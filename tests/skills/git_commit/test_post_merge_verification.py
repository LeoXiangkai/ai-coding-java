from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[3] / "core" / "skills" / "git-commit" / "scripts" / "post-merge-verification.py"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def new_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    (repo / "state").write_text("base\n", encoding="utf-8")
    git(repo, "add", "state")
    git(repo, "commit", "-qm", "base")
    return repo


def commit_file(repo: Path, name: str, content: str) -> None:
    (repo / name).write_text(content + "\n", encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-qm", name)


def decision(repo: Path, fork: str, before: str, after: str, *extra: str) -> list[str]:
    result = subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--repo", str(repo),
            "--fork", fork,
            "--baseline-before", before,
            "--baseline-after", after,
            "--fork-source", "persisted",
            "--integration-mode", "managed-no-ff",
            *extra,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def test_skips_when_only_current_task_was_merged(tmp_path: Path) -> None:
    repo = new_repo(tmp_path)
    fork = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "-q", "-c", "task", fork)
    commit_file(repo, "task.txt", "task")
    git(repo, "switch", "-q", "-C", "baseline", fork)
    before = git(repo, "rev-parse", "HEAD")
    git(repo, "merge", "--no-ff", "-qm", "current task", "task")
    after = git(repo, "rev-parse", "HEAD")

    output = decision(repo, fork, before, after)

    assert output[0] == "SKIP_DUPLICATE"
    assert any(line.strip() == "changed_files=task.txt" for line in output)


def test_runs_targeted_when_another_task_was_merged_first(tmp_path: Path) -> None:
    repo = new_repo(tmp_path)
    fork = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "-q", "-c", "task", fork)
    commit_file(repo, "task.txt", "task")
    git(repo, "switch", "-q", "-C", "baseline", fork)
    git(repo, "switch", "-q", "-c", "other", fork)
    commit_file(repo, "other.txt", "other")
    git(repo, "switch", "-q", "baseline")
    git(repo, "merge", "--no-ff", "-qm", "other task", "other")
    before = git(repo, "rev-parse", "HEAD")
    git(repo, "merge", "--no-ff", "-qm", "current task", "task")
    after = git(repo, "rev-parse", "HEAD")

    output = decision(repo, fork, before, after)

    assert output[0] == "RUN_TARGETED"
    assert any(line.startswith("reason=other first-parent merge") for line in output)


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        (("--manual-resolution",), "reason=merge required manual conflict resolution"),
        ((), "reason=task fork provenance is not persisted: fallback"),
    ],
)
def test_runs_targeted_for_conflict_or_unknown_source(
    tmp_path: Path, extra: tuple[str, ...], expected: str
) -> None:
    repo = new_repo(tmp_path)
    fork = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "-q", "-c", "task", fork)
    commit_file(repo, "task.txt", "task")
    git(repo, "switch", "-q", "-C", "baseline", fork)
    before = git(repo, "rev-parse", "HEAD")
    git(repo, "merge", "--no-ff", "-qm", "current task", "task")
    after = git(repo, "rev-parse", "HEAD")

    if expected.endswith("fallback"):
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), "--repo", str(repo), "--fork", fork,
                "--baseline-before", before, "--baseline-after", after,
                "--fork-source", "fallback", "--integration-mode", "managed-no-ff",
            ], check=True, capture_output=True, text=True,
        )
        output = result.stdout.splitlines()
    else:
        output = decision(repo, fork, before, after, *extra)

    assert output[0] == "RUN_TARGETED"
    assert expected in output
