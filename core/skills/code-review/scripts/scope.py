#!/usr/bin/env python3
"""Resolve one repository/branch review boundary and its reviewer budget."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


LOW_IMPACT_MAX_FILES = 8
LOW_IMPACT_MAX_CHANGED_LINES = 300
DUAL_REVIEW_MIN_FILES = 31
DUAL_REVIEW_MIN_CHANGED_LINES = 1501
MAX_REVIEWERS = 2

LOG_DIR_ENV = "AICJ_REVIEW_LOG_DIR"
CLAUDE_DIR_ENV = "AICJ_CLAUDE_DIR"
GATE_LOG_FILE = "code-review-gates.jsonl"


def claude_dir() -> Path:
    """AICJ_CLAUDE_DIR wins; otherwise derive from this script's install location.

    Installed layout: <claude>/skills/code-review/scripts/scope.py -> parents[3] is <claude>.
    """
    env = os.environ.get(CLAUDE_DIR_ENV)
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parents[3]


def review_log_dir() -> Path:
    env = os.environ.get(LOG_DIR_ENV)
    if env:
        return Path(env).expanduser().resolve()
    return (claude_dir() / "aicj" / "review-logs").resolve()


def iso8601() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def append_gate_log(record: dict) -> None:
    """Append a JSONL record; failures are swallowed and must not affect stdout/exit code."""
    log_dir = review_log_dir()
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / GATE_LOG_FILE
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

RISK_PATTERNS = {
    "api-contract": {
        "path": re.compile(r"(^|/)(api|controller|dto|vo|schema|schemas|openapi|graphql|proto)(/|$)", re.I),
        "content": re.compile(r"\b(interface|request|response|endpoint|route|controller|openapi|protobuf)\b", re.I),
    },
    "database-migration": {
        "path": re.compile(r"(?:\.sql$|(^|/)(migration|migrations|liquibase|flyway|db/changelog)(/|$))", re.I),
        "content": re.compile(r"\b(ALTER\s+TABLE|CREATE\s+TABLE|DROP\s+TABLE|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b", re.I),
    },
    "authorization-security": {
        "path": re.compile(r"(^|/|[-_.])(auth|authorization|permission|security|role|acl|credential|crypto|pii|token)(/|[-_.]|$)", re.I),
        "content": re.compile(r"\b(authori[sz]e[sd]?|permission|credential|password|access[_ -]?token|encrypt(?:ion|ed)?|pii)\b", re.I),
    },
    "concurrency-transaction": {
        "path": re.compile(r"(^|/|[-_.])(transaction|concurren|lock|async|executor|thread)(/|[-_.]|$)", re.I),
        "content": re.compile(r"\b(Transactional|transaction|synchronized|mutex|semaphore|afterCommit|Async|ExecutorService|ThreadLocal)\b"),
    },
    "cross-process": {
        "path": re.compile(r"(^|/|[-_.])(mq|kafka|rabbit|dubbo|rpc|consumer|producer|scheduler|webhook)(/|[-_.]|$)", re.I),
        "content": re.compile(r"\b(Kafka|RabbitMQ|Dubbo|RPC|message\s+queue|webhook|scheduled|third[- ]party)\b", re.I),
    },
}


class ScopeError(RuntimeError):
    pass


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise ScopeError(message or f"git {' '.join(args)} failed")
    return result


def text_output(repo: Path, *args: str, check: bool = True) -> str:
    return git(repo, *args, check=check).stdout.decode("utf-8", errors="replace").strip()


def resolve_repo_root(target: Path) -> Path:
    candidate = target.expanduser().resolve()
    if candidate.is_file():
        candidate = candidate.parent
    if not candidate.exists():
        raise ScopeError(f"target does not exist: {candidate}")
    root = text_output(candidate, "rev-parse", "--show-toplevel")
    return Path(root).resolve()


def git_common_dir(repo: Path) -> Path:
    raw = text_output(repo, "rev-parse", "--git-common-dir")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = repo / candidate
    return candidate.resolve()


def resolve_branch(repo: Path) -> str:
    branch = text_output(repo, "branch", "--show-current")
    if not branch:
        raise ScopeError("code-review requires a named current development branch")
    return branch


def resolve_base(repo: Path, branch: str) -> tuple[str, str, str | None]:
    fork_key = f"branch.{branch}.fork-oid"
    fork_oid = text_output(repo, "config", "--get", fork_key, check=False)
    if fork_oid:
        return text_output(repo, "rev-parse", f"{fork_oid}^{{commit}}"), "fork-oid", None

    baseline_key = f"branch.{branch}.baseline"
    baseline = text_output(repo, "config", "--get", baseline_key, check=False)
    if baseline:
        return text_output(repo, "rev-parse", f"{baseline}^{{commit}}"), "baseline", baseline

    upstream = text_output(repo, "rev-parse", "--abbrev-ref", "@{upstream}", check=False)
    if upstream:
        merge_base = text_output(repo, "merge-base", "HEAD", upstream)
        return merge_base, "upstream-merge-base", upstream

    raise ScopeError(
        "missing immutable branch.<branch>.fork-oid and branch baseline; "
        "record worktree baseline metadata before review"
    )


def nul_paths(raw: bytes) -> list[str]:
    return [part.decode("utf-8", errors="surrogateescape") for part in raw.split(b"\0") if part]


def file_blobs_worktree(repo: Path, files: list[str]) -> dict[str, str | None]:
    blobs: dict[str, str | None] = {}
    if not files:
        return blobs
    existing = [f for f in files if (repo / f).is_file()]
    if not existing:
        for relative_path in files:
            blobs[relative_path] = None
        return blobs
    result = git(repo, "hash-object", "--", *existing, check=False)
    hashes = [h.strip() for h in result.stdout.decode("utf-8", errors="replace").splitlines() if h.strip()]
    if len(hashes) != len(existing):
        raise ScopeError(
            f"git hash-object returned {len(hashes)} hashes for {len(existing)} files"
        )
    for relative_path, blob in zip(existing, hashes):
        blobs[relative_path] = blob
    for relative_path in files:
        if relative_path not in blobs:
            blobs[relative_path] = None
    return blobs


def changed_files(repo: Path, base_oid: str, head: str | None = None) -> tuple[list[str], set[str]]:
    head_expr = head if head is not None else "--"
    tracked = set(nul_paths(git(repo, "diff", "--name-only", "-z", base_oid, head_expr).stdout))
    untracked: set[str] = set()
    if head is None:
        untracked = set(nul_paths(git(repo, "ls-files", "--others", "--exclude-standard", "-z").stdout))
    return sorted(tracked | untracked), untracked


def validate_file_boundary(repo: Path, files: list[str]) -> None:
    for relative_path in files:
        path = repo / relative_path
        if not path.is_symlink():
            continue
        resolved = path.resolve(strict=False)
        if not resolved.is_relative_to(repo):
            raise ScopeError(
                f"changed path resolves outside repository: {relative_path} -> {resolved}"
            )


def changed_line_count(
    repo: Path,
    base_oid: str,
    untracked: set[str],
    head: str | None = None,
    paths: list[str] | None = None,
) -> int:
    head_expr = head if head is not None else "--"
    total = 0
    cmd = ["diff", "--numstat", base_oid, head_expr]
    if paths:
        cmd.append("--")
        cmd.extend(paths)
    numstat = text_output(repo, *cmd)
    for row in numstat.splitlines():
        columns = row.split("\t", 2)
        if len(columns) < 2:
            continue
        for value in columns[:2]:
            if value.isdigit():
                total += int(value)

    if head is None:
        for relative_path in untracked:
            if paths and relative_path not in paths:
                continue
            path = repo / relative_path
            if not path.is_file():
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if b"\0" not in data:
                total += len(data.splitlines())
    return total


def changed_content(
    repo: Path,
    base_oid: str,
    relative_path: str,
    untracked: set[str],
    head: str | None = None,
) -> str:
    head_expr = head if head is not None else "--"
    if head is None and relative_path in untracked:
        path = repo / relative_path
        if not path.is_file():
            return ""
        try:
            return path.read_text(encoding="utf-8", errors="ignore")[:1_000_000]
        except OSError:
            return ""

    patch = text_output(
        repo,
        "diff",
        "--unified=0",
        "--no-ext-diff",
        base_oid,
        head_expr,
        "--",
        relative_path,
    )
    changed_lines = [
        line[1:]
        for line in patch.splitlines()
        if (line.startswith("+") and not line.startswith("+++"))
        or (line.startswith("-") and not line.startswith("---"))
    ]
    return "\n".join(changed_lines)[:1_000_000]


def detect_risks(
    repo: Path,
    base_oid: str,
    files: list[str],
    untracked: set[str],
    head: str | None = None,
) -> tuple[list[str], dict[str, list[str]]]:
    details: dict[str, list[str]] = {}
    for relative_path in files:
        content = changed_content(repo, base_oid, relative_path, untracked, head=head)
        for risk, patterns in RISK_PATTERNS.items():
            if patterns["path"].search(relative_path) or patterns["content"].search(content):
                details.setdefault(risk, []).append(relative_path)
    return sorted(details), {risk: sorted(paths) for risk, paths in sorted(details.items())}


def _to_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return 0


def review_budget(file_count: int, changed_lines: int, risks: list[str]) -> tuple[str, int]:
    low_impact = (
        file_count <= LOW_IMPACT_MAX_FILES
        and changed_lines <= LOW_IMPACT_MAX_CHANGED_LINES
        and not risks
    )
    if low_impact:
        return "skip", 0

    large_change = (
        file_count >= DUAL_REVIEW_MIN_FILES
        or changed_lines >= DUAL_REVIEW_MIN_CHANGED_LINES
    )
    if large_change and len(risks) >= 2:
        return "dual-candidate", MAX_REVIEWERS

    return "single", 1


def build_scope(target: Path, effort: str, paths: list[str] | None = None) -> dict[str, object]:
    repo = resolve_repo_root(target)
    branch = resolve_branch(repo)
    base_oid, base_source, baseline = resolve_base(repo, branch)
    all_files, all_untracked = changed_files(repo, base_oid)
    if paths is not None:
        path_set = set(paths)
        files = sorted(set(all_files) & path_set)
        untracked = {f for f in all_untracked if f in path_set}
    else:
        files, untracked = all_files, all_untracked
    validate_file_boundary(repo, files)
    changed_lines = changed_line_count(repo, base_oid, untracked, paths=paths)
    risks, risk_details = detect_risks(repo, base_oid, files, untracked)
    gate, max_reviewers = review_budget(len(files), changed_lines, risks)
    identity = f"{repo}\0{branch}\0{base_oid}".encode()

    return {
        "repo_root": str(repo),
        "branch": branch,
        "base_oid": base_oid,
        "base_source": base_source,
        "baseline": baseline,
        "coordination_key": hashlib.sha256(identity).hexdigest()[:20],
        "files": files,
        "file_count": len(files),
        "changed_lines": changed_lines,
        "risk_signals": risks,
        "risk_details": risk_details,
        "review_gate": gate,
        "max_reviewers": min(max_reviewers, MAX_REVIEWERS),
        "requested_effort": effort,
        "common_dir": str(git_common_dir(repo)),
        "head_oid": text_output(repo, "rev-parse", "HEAD"),
    }


def outcome_record(
    repo_root: Path,
    branch: str,
    base_oid: str,
    reviewers: int,
    findings: int,
    confirmed: int,
    common_dir: Path | str | None = None,
    head_oid: str | None = None,
    review_gate: str | None = None,
    reviewed_blobs: dict[str, str | None] | None = None,
) -> dict:
    record = {
        "ts": iso8601(),
        "kind": "outcome",
        "repo_root": str(repo_root),
        "branch": branch,
        "base_oid": base_oid,
        "reviewers": reviewers,
        "findings": findings,
        "confirmed": confirmed,
    }
    if common_dir is not None:
        record["common_dir"] = str(common_dir)
    if head_oid is not None:
        record["head_oid"] = head_oid
    if review_gate is not None:
        record["review_gate"] = review_gate
    if reviewed_blobs is not None:
        record["reviewed_blobs"] = reviewed_blobs
    return record


def append_outcome(args: argparse.Namespace) -> int:
    target = Path(args.target)
    repo = resolve_repo_root(target)
    branch = resolve_branch(repo)
    base_oid, _base_source, _baseline = resolve_base(repo, branch)
    scope = build_scope(target, args.effort)
    record = outcome_record(
        repo,
        branch,
        base_oid,
        _to_int(args.reviewers),
        _to_int(args.findings),
        _to_int(args.confirmed),
        common_dir=git_common_dir(repo),
        head_oid=text_output(repo, "rev-parse", "HEAD"),
        review_gate=scope["review_gate"],
        reviewed_blobs=file_blobs_worktree(repo, scope["files"]),
    )
    append_gate_log(record)
    print("recorded")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=".", help="Path inside the one repository to review")
    parser.add_argument(
        "--effort",
        default="medium",
        choices=("low", "medium", "high", "xhigh", "max"),
        help="Depth within the fixed reviewer budget",
    )
    parser.add_argument("--outcome", action="store_true", help="Record review outcome")
    parser.add_argument("--reviewers", type=int, default=0)
    parser.add_argument("--findings", type=int, default=0)
    parser.add_argument("--confirmed", type=int, default=0)
    args = parser.parse_args()

    if args.outcome:
        return append_outcome(args)

    try:
        result = build_scope(Path(args.target), args.effort)
    except ScopeError as error:
        parser.exit(2, f"scope error: {error}\n")

    gate_record = {
        "ts": iso8601(),
        "kind": "gate",
        "repo_root": result["repo_root"],
        "branch": result["branch"],
        "base_oid": result["base_oid"],
        "files": result["files"],
        "lines": result["changed_lines"],
        "review_gate": result["review_gate"],
    }
    # Preserve risk signal fields from result using their existing keys
    for key in ("risk_signals", "risk_details", "max_reviewers", "requested_effort"):
        if key in result:
            gate_record[key] = result[key]
    append_gate_log(gate_record)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
