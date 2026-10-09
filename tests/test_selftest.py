from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from conftest import AICJ, REPO


def run_aicj(*args: str, home: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    process_env = dict(os.environ)
    process_env.update(env or {})
    return subprocess.run(
        [sys.executable, str(AICJ), *args, "--home", str(home), "--source", str(REPO)],
        cwd=REPO,
        env=process_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def install(home: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    result = run_aicj("install", *extra, home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def test_selftest_runs_real_hooks_and_reports_push_modes(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    install(home)

    result = run_aicj("selftest", home=home)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS  4a push-review-gate warn" in result.stdout
    assert "PASS  4b push-review-gate block" in result.stdout
    assert "PASS  4c push-review-gate non-push" in result.stdout
    assert "SKIP  claude-code" in result.stdout
    assert "summary" in result.stdout


def test_selftest_fails_when_registered_hook_script_is_deleted(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    install(home)
    hook = home / ".claude/hooks/aicj/push-review-gate.py"
    hook.unlink()

    result = run_aicj("selftest", home=home)

    assert result.returncode == 1
    assert "FAIL  doctor" in result.stdout
    assert "push-review-gate.py" in result.stdout


def _path_without_claude(directory: Path) -> str:
    git = shutil.which("git")
    assert git
    return os.pathsep.join((str(directory), str(Path(sys.executable).parent), str(Path(git).parent)))


def _fake_claude(directory: Path, body: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "claude"
    path.write_text(f"#!{sys.executable}\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


def test_selftest_with_fake_claude_executes_registered_hook(tmp_path: Path) -> None:
    home = tmp_path / "home"
    fake_bin = tmp_path / "bin"
    home.mkdir()
    install(home)
    _fake_claude(
        fake_bin,
        """
import json, os, subprocess, sys
settings = json.load(open(os.path.join(os.environ['CLAUDE_CONFIG_DIR'], 'settings.json'), encoding='utf-8'))
hook = settings['hooks']['PreToolUse'][0]['hooks'][0]
payload = {'session_id': 'fake-claude', 'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'tool_input': {'command': 'git push origin main'}, 'cwd': os.getcwd()}
result = subprocess.run([hook['command'], *hook.get('args', [])], input=json.dumps(payload), text=True, capture_output=True, env=os.environ.copy())
print(result.stdout)
print(result.stderr, file=sys.stderr)
raise SystemExit(0)
""",
    )

    result = run_aicj("selftest", "--with-claude", home=home, env={"PATH": _path_without_claude(fake_bin)})

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS  claude-code" in result.stdout


def test_selftest_with_fake_claude_auth_failure_is_skip(tmp_path: Path) -> None:
    home = tmp_path / "home"
    fake_bin = tmp_path / "bin"
    home.mkdir()
    install(home)
    _fake_claude(fake_bin, "import sys; print('403 authentication required', file=sys.stderr); raise SystemExit(1)")

    result = run_aicj("selftest", "--with-claude", home=home, env={"PATH": _path_without_claude(fake_bin)})

    assert result.returncode == 0, result.stdout + result.stderr
    assert "SKIP  claude-code" in result.stdout
    assert "403" in result.stdout


def test_selftest_with_claude_missing_is_skip(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    install(home)
    env = {"PATH": _path_without_claude(tmp_path / "no-claude")}

    result = run_aicj("selftest", "--with-claude", home=home, env=env)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "SKIP  claude-code  未找到 claude 命令" in result.stdout


def test_cc_mode_marks_worker_checks_na_and_writes_config(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    install(home)
    result = run_aicj("selftest", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS  模式  cc" in result.stdout
    assert "N/A   worker dry-run  cc 模式，未安装 executor 适配" in result.stdout
    assert "N/A=5" in result.stdout
    assert json.loads((home / ".claude/aicj/config.json").read_text(encoding="utf-8"))["executor_mode"] == "cc"


def test_worker_mode_selftest_checks_worker_contract(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    install(home, "--adapters", "executor")
    result = run_aicj("selftest", home=home)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS  模式  worker" in result.stdout
    assert "PASS  worker dry-run" in result.stdout
    assert "PASS  worker 主工作区校验" in result.stdout
    assert "PASS  block-handoff-poll" in result.stdout
    assert "FAIL  " not in result.stdout


def test_worker_with_fake_claude_creates_file(tmp_path: Path) -> None:
    home = tmp_path / "home"
    fake_bin = tmp_path / "bin"
    home.mkdir()
    install(home, "--adapters", "executor")
    _fake_claude(fake_bin, "from pathlib import Path; Path('selftest-worker.txt').write_text('ok', encoding='utf-8')")
    result = run_aicj("selftest", "--with-claude", home=home, env={"PATH": _path_without_claude(fake_bin)})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS  aicj-worker claude" in result.stdout


def test_worker_with_fake_claude_auth_failure_is_skip(tmp_path: Path) -> None:
    home = tmp_path / "home"
    fake_bin = tmp_path / "bin"
    home.mkdir()
    install(home, "--adapters", "executor")
    _fake_claude(fake_bin, "import sys; print('403 authentication required', file=sys.stderr); raise SystemExit(1)")
    result = run_aicj("selftest", "--with-claude", home=home, env={"PATH": _path_without_claude(fake_bin)})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SKIP  aicj-worker claude" in result.stdout and "403" in result.stdout


def test_install_is_idempotent_and_mode_switch_updates_config(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    install(home)
    cc_config = (home / ".claude/aicj/config.json").read_text(encoding="utf-8")
    second = install(home)
    assert all(word not in second.stdout for word in ("created", "replaced", "conflict"))
    assert (home / ".claude/aicj/config.json").read_text(encoding="utf-8") == cc_config
    install(home, "--adapters", "executor")
    assert json.loads((home / ".claude/aicj/config.json").read_text(encoding="utf-8"))["executor_mode"] == "worker"
    install(home)
    cc = run_aicj("selftest", home=home)
    assert cc.returncode == 0, cc.stdout + cc.stderr
    assert "PASS  模式  cc" in cc.stdout and "N/A   worker dry-run" in cc.stdout
    install(home, "--adapters", "executor")
    worker_result = run_aicj("selftest", home=home)
    assert worker_result.returncode == 0, worker_result.stdout + worker_result.stderr
    assert "PASS  模式  worker" in worker_result.stdout and "PASS  worker dry-run" in worker_result.stdout


def test_executor_rules_document_both_modes() -> None:
    text = (REPO / "core/rules/executor-handoff.md").read_text(encoding="utf-8")
    assert "cc 模式" in text and "worker 模式" in text
    assert "失败降级子代理" in text


def test_windows_script_has_bom_and_frozen_parameters() -> None:
    script = REPO / "scripts/windows/install.ps1"
    data = script.read_bytes()
    text = data.decode("utf-8-sig")
    assert data.startswith(b"\xef\xbb\xbf")
    for parameter in ("-NoPrereqs", "-NoClaude", "-HomeDir", "-Mode", "ValidateSet(\"cc\", \"worker\")"):
        assert parameter in text


def test_cpa_script_is_bom_safe_and_does_not_default_login() -> None:
    script = REPO / "scripts/windows/install-cpa.ps1"
    data = script.read_bytes()
    text = data.decode("utf-8-sig")
    assert data.startswith(b"\xef\xbb\xbf")
    for parameter in ("$InstallDir", "$Version", "$Port", "$Login", "$NoAutostart", "$Uninstall", "$Purge"):
        assert parameter in text
    assert "Get-FileHash" in text and "SHA256" in text
    assert 'host: "127.0.0.1"' in text
    assert "if ($Login.Count -gt 0)" in text
