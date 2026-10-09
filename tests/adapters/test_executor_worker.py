from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from adapter_helpers import WORKER, fake_command, run_script


def git(*args, cwd):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.test",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.test"}
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=env)


@pytest.fixture()
def repo(tmp_path):
    main = tmp_path / "main"
    main.mkdir()
    git("init", "-q", "-b", "main", cwd=main)
    (main / "a.txt").write_text("a\n", encoding="utf-8")
    git("add", "a.txt", cwd=main)
    git("commit", "-q", "-m", "init", cwd=main)
    wt = tmp_path / "wt"
    git("worktree", "add", "-q", "-b", "feature/x", str(wt), cwd=main)
    return main, wt


def git_only_path(tmp_path):
    """PATH that has git but no engine CLI."""
    import shutil
    d = tmp_path / "git-only-bin"
    d.mkdir(exist_ok=True)
    if os.name == "nt":
        real_git = shutil.which("git")
        assert real_git
        return Path(real_git).parent
    else:
        link = d / "git"
        if not link.exists():
            link.symlink_to(shutil.which("git"))
    return d


def worker(*args, claude, env_extra=None, path=None):
    return run_script(WORKER, *args, claude=claude, env_extra=env_extra, path=path)


def dry(repo, claude, *extra, env_extra=None):
    _, wt = repo
    result = worker("--cd", str(wt), "--dry-run", *extra, "do it", claude=claude, env_extra=env_extra)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_main_worktree_rejected(repo, tmp_path):
    main, _ = repo
    result = worker("--cd", str(main), "--tier", "high", "--dry-run", "x", claude=tmp_path)
    assert result.returncode == 2


def test_non_git_directory_rejected(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert worker("--cd", str(plain), "--tier", "high", "--dry-run", "x", claude=tmp_path).returncode == 2


def test_missing_directory_and_blank_prompt_rejected(repo, tmp_path):
    _, wt = repo
    assert worker("--cd", str(tmp_path / "nope"), "--tier", "high", "--dry-run", "x", claude=tmp_path).returncode == 2
    assert worker("--cd", str(wt), "--tier", "high", "--dry-run", "   ", claude=tmp_path).returncode == 2


def test_missing_tier_is_usage_error(repo, tmp_path):
    _, wt = repo
    assert worker("--cd", str(wt), "--dry-run", "x", claude=tmp_path).returncode == 2


def test_claude_engine_argv(repo, tmp_path):
    argv = dry(repo, tmp_path, "--tier", "mid")
    assert argv[:2] == ["claude", "-p"]
    assert argv[argv.index("--disallowedTools") + 1] == "Agent"
    assert argv[argv.index("--") + 1] == "do it"
    assert "--model" not in argv
    assert argv[-1] == "do it"


def test_codex_engine_argv(repo, tmp_path):
    _, wt = repo
    argv = dry(repo, tmp_path, "--tier", "low", "--engine", "codex")
    assert argv[:2] == ["codex", "exec"]
    assert argv[argv.index("--cd") + 1] == str(wt.resolve())
    assert "-m" not in argv
    assert argv[-1].startswith("do it")
    assert "不得再派子代理" in argv[-1] and "commit/push" in argv[-1]
    assert argv[argv.index("-s") + 1] == "danger-full-access"
    assert 'model_reasoning_effort="low"' in argv
    high = dry(repo, tmp_path, "--tier", "high", "--engine", "codex", env_extra={"AICJ_EXECUTOR_CODEX_SANDBOX": "workspace-write"})
    assert high[high.index("-s") + 1] == "workspace-write"
    assert 'model_reasoning_effort="high"' in high


def test_engine_from_environment_and_flag_precedence(repo, tmp_path):
    assert dry(repo, tmp_path, "--tier", "low", env_extra={"AICJ_EXECUTOR_ENGINE": " Codex "})[0] == "codex"
    assert dry(repo, tmp_path, "--tier", "low", "--engine", "claude", env_extra={"AICJ_EXECUTOR_ENGINE": "codex"})[0] == "claude"


def test_unknown_engine_from_environment_rejected(repo, tmp_path):
    _, wt = repo
    result = worker("--cd", str(wt), "--tier", "low", "--dry-run", "x", claude=tmp_path,
                    env_extra={"AICJ_EXECUTOR_ENGINE": "bogus"})
    assert result.returncode == 2


def test_tier_model_passed_only_for_its_tier(repo, tmp_path):
    env = {"AICJ_EXECUTOR_MODEL_HIGH": "model-h", "AICJ_EXECUTOR_MODEL_LOW": "model-l"}
    high = dry(repo, tmp_path, "--tier", "high", env_extra=env)
    assert high[high.index("--model") + 1] == "model-h"
    assert "--model" not in dry(repo, tmp_path, "--tier", "mid", env_extra=env)
    codex = dry(repo, tmp_path, "--tier", "low", "--engine", "codex", env_extra=env)
    assert codex[codex.index("-m") + 1] == "model-l"


def test_blank_model_variable_is_ignored(repo, tmp_path):
    assert "--model" not in dry(repo, tmp_path, "--tier", "high", env_extra={"AICJ_EXECUTOR_MODEL_HIGH": "  "})


def test_engine_cli_missing_returns_127(repo, tmp_path):
    _, wt = repo
    empty = git_only_path(tmp_path)
    for engine in ("claude", "codex"):
        result = worker("--cd", str(wt), "--tier", "high", "--engine", engine, "x", claude=tmp_path, path=str(empty))
        assert result.returncode == 127
        assert "降级" in result.stderr


def test_engine_nonzero_exit_is_propagated(repo, tmp_path):
    _, wt = repo
    fake = tmp_path / "fake-bin"
    fake_command(fake, "claude", "import sys\nsys.exit(7)\n")
    path = os.pathsep.join([str(fake), str(git_only_path(tmp_path))])
    result = worker("--cd", str(wt), "--tier", "high", "x", claude=tmp_path, path=path)
    assert result.returncode == 7


@pytest.mark.parametrize("value", ["wat", "0", "-1", "nan", "inf"])
def test_invalid_timeout_reports_error_without_limiting_execution(repo, tmp_path, value):
    fake = tmp_path / "fake-bin"
    fake_command(fake, "claude", "import time; time.sleep(0.1); print('completed')\n")
    path = os.pathsep.join([str(fake), str(git_only_path(tmp_path))])
    result = worker("--cd", str(repo[1]), "--tier", "high", "x", claude=tmp_path, path=path, env_extra={"AICJ_EXECUTOR_TIMEOUT": value})
    assert result.returncode == 0, result.stderr
    assert result.stdout == "completed\n"
    assert "AICJ_EXECUTOR_TIMEOUT" in result.stderr
    control = worker("--cd", str(repo[1]), "--tier", "high", "x", claude=tmp_path, path=path, env_extra={"AICJ_EXECUTOR_TIMEOUT": "0.01"})
    assert control.returncode == 124
    assert control.stdout == ""


def test_timeout_returns_124(repo, tmp_path):
    fake = tmp_path / "fake-bin"
    fake_command(fake, "claude", "import time; time.sleep(0.1); print('completed')\n")
    path = os.pathsep.join([str(fake), str(git_only_path(tmp_path))])
    result = worker("--cd", str(repo[1]), "--tier", "high", "x", claude=tmp_path, path=path, env_extra={"AICJ_EXECUTOR_TIMEOUT": "0.01"})
    assert result.returncode == 124
    assert "超时" in result.stderr
    assert result.stdout == ""
    control = worker("--cd", str(repo[1]), "--tier", "high", "x", claude=tmp_path, path=path, env_extra={"AICJ_EXECUTOR_TIMEOUT": ""})
    assert (control.returncode, control.stdout, control.stderr) == (0, "completed\n", "")
