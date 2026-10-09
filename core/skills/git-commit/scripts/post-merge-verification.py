#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], text=True, encoding="utf-8", capture_output=True, check=check)


def is_commit(repo: Path, value: str) -> bool:
    return git(repo, "cat-file", "-e", f"{value}^{{commit}}", check=False).returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--fork", required=True)
    parser.add_argument("--baseline-before", required=True)
    parser.add_argument("--baseline-after", required=True)
    parser.add_argument("--fork-source", default="missing")
    parser.add_argument("--integration-mode", required=True)
    parser.add_argument("--manual-resolution", action="store_true")
    args = parser.parse_args(argv)
    repo = Path(args.repo)
    reason = ""
    if not ((repo / ".git").is_dir() or (repo / ".git").is_file()):
        reason = "repository is unavailable"
    elif args.fork_source != "persisted":
        reason = f"task fork provenance is not persisted: {args.fork_source}"
    elif not is_commit(repo, args.fork):
        reason = "task fork SHA is missing or invalid"
    elif not is_commit(repo, args.baseline_before):
        reason = "pre-merge baseline SHA is missing or invalid"
    elif not is_commit(repo, args.baseline_after):
        reason = "post-merge baseline SHA is missing or invalid"
    elif git(repo, "merge-base", "--is-ancestor", args.fork, args.baseline_before, check=False).returncode != 0:
        reason = "task fork is not an ancestor of the pre-merge baseline"
    elif git(repo, "merge-base", "--is-ancestor", args.baseline_before, args.baseline_after, check=False).returncode != 0:
        reason = "pre-merge baseline is not an ancestor of the post-merge baseline"
    elif args.manual_resolution:
        reason = "merge required manual conflict resolution"
    elif args.integration_mode != "managed-no-ff":
        reason = f"integration mode is not managed-no-ff: {args.integration_mode}"
    if reason:
        print(f"RUN_TARGETED\nreason={reason}")
        return 0
    merges = git(repo, "rev-list", "--first-parent", "--merges", f"{args.fork}..{args.baseline_before}").stdout.strip()
    changed = " ".join(git(repo, "diff", "--name-only", args.baseline_before, args.baseline_after).stdout.splitlines())
    if merges:
        print(f"RUN_TARGETED\nreason=other first-parent merge(s) existed before this task merge\nmerges={' '.join(merges.splitlines())}\nchanged_files={changed}")
    else:
        print(f"SKIP_DUPLICATE\nreason=no first-parent merge existed between task fork and pre-merge baseline\nfork={args.fork}\nbaseline_before={args.baseline_before}\nbaseline_after={args.baseline_after}\nchanged_files={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
