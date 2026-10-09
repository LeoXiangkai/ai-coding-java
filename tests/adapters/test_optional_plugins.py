from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from adapter_helpers import REPO, fake_command, run_script
from conftest import files_under, run_aicj

JEV = REPO / "adapters/optional-plugins/jev"
VERIFY = REPO / "adapters/optional-plugins/verify-probe"


def run_jev(*args: str, claude: Path, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("AICJ_")}
    env["AICJ_CLAUDE_DIR"] = str(claude)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(JEV / "bin/jev-consumer"), *args], capture_output=True, text=True, encoding="utf-8", env=env)


def with_path(tmp_path: Path, *commands: str) -> str:
    directory = tmp_path / "bin"
    directory.mkdir(exist_ok=True)
    for name in commands:
        fake_command(directory, name, "import sys\nsys.exit(0)\n")
    return str(directory)


def test_doctor_skips_plugin_requirements_without_making_files_missing(home, monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", with_path(tmp_path, "git"))
    result = run_aicj("install", "--adapters", "jev,verify-probe", home=home, source=None)
    assert result.returncode == 0, result.stdout + result.stderr
    doctor = run_aicj("doctor", home=home, source=None)
    assert doctor.returncode == 0, doctor.stdout + doctor.stderr
    assert "SKIPPED  plugin jev" in doctor.stdout
    assert "SKIPPED  plugin verify-probe" not in doctor.stdout
    assert "MISSING  plugin" not in doctor.stdout
    assert "command node" in doctor.stdout and "装好后即可用" in doctor.stdout


def test_doctor_passes_plugin_requirements_when_command_and_skill_exist(home, tmp_path, monkeypatch):
    claude = home / ".claude"
    skill = claude / "skills/jev-assist/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("third-party probe\n", encoding="utf-8")
    monkeypatch.setenv("PATH", with_path(tmp_path, "git", "node"))
    assert run_aicj("install", "--adapters", "jev,verify-probe", home=home, source=None).returncode == 0
    doctor = run_aicj("doctor", home=home, source=None)
    assert doctor.returncode == 0, doctor.stdout + doctor.stderr
    assert "PASS     plugin jev" in doctor.stdout
    assert "PASS     plugin verify-probe" in doctor.stdout


def test_jev_consumer_rejects_non_git_and_blank_arguments(tmp_path):
    claude = tmp_path / ".claude"
    assert run_jev("data", "x", str(tmp_path), claude=claude).returncode == 2
    result = run_jev(" ", "x", str(tmp_path), claude=claude)
    assert result.returncode == 2 and "non-blank" in result.stderr


def test_jev_consumer_lists_small_pool_without_node(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "one.txt").write_text("needle\n", encoding="utf-8")
    subprocess.run(["git", "add", "one.txt"], cwd=repo, check=True)
    marker = tmp_path / "node-called"
    fake_node = fake_command(tmp_path, "node", f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
    env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}"}
    result = run_jev("data", "needle", str(repo), claude=tmp_path / ".claude", env_extra=env)
    assert result.returncode == 0 and "one.txt" in result.stdout
    assert "no semantic call made" in result.stderr and not marker.exists()


def test_jev_consumer_reports_missing_scanner_for_large_pool(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    for number in range(16):
        path = repo / f"file-{number}.txt"
        path.write_text("needle\n", encoding="utf-8")
        subprocess.run(["git", "add", path.name], cwd=repo, check=True)
    claude = tmp_path / ".claude"
    template = claude / "aicj/jev/consumer-template.json"
    template.parent.mkdir(parents=True)
    template.write_text("{}\n", encoding="utf-8")
    result = run_jev("data", "needle", str(repo), claude=claude)
    assert result.returncode == 2 and "consumer_scan.mjs missing" in result.stderr


def test_jev_consumer_bash3_empty_extra_array(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    for number in range(16):
        path = repo / f"file-{number}.txt"
        path.write_text("needle\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", path.name], check=True)
    claude = tmp_path / ".claude"
    (claude / "aicj/jev").mkdir(parents=True)
    (claude / "aicj/jev/consumer-template.json").write_text("{}\n", encoding="utf-8")
    scan = claude / "skills/jev-assist/scripts/consumer_scan.mjs"
    scan.parent.mkdir(parents=True)
    scan.write_text("process.exit(0)\n", encoding="utf-8")
    scan.chmod(0o755)
    env = {"PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}", "AICJ_CLAUDE_DIR": str(claude)}
    result = subprocess.run([sys.executable, str(JEV / "bin/jev-consumer"), "data", "needle", str(repo)], env=env, capture_output=True, text=True, encoding="utf-8")
    assert "unbound variable" not in result.stderr


def _large_jev_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "large-repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    for number in range(16):
        path = repo / f"candidate-{number}.txt"
        path.write_text("needle\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", path.name], check=True)
    return repo


def test_jev_consumer_default_layout_and_env_file(tmp_path):
    repo = _large_jev_repo(tmp_path)
    claude = tmp_path / "claude"
    script = claude / "bin/jev-consumer"
    script.parent.mkdir(parents=True)
    script.write_bytes((JEV / "bin/jev-consumer").read_bytes())
    script.chmod(0o755)
    (claude / "aicj/jev").mkdir(parents=True)
    (claude / "aicj/jev/consumer-template.json").write_text("{}\n", encoding="utf-8")
    scan = claude / "skills/jev-assist/scripts/consumer_scan.mjs"
    scan.parent.mkdir(parents=True)
    scan.write_text("process.stdout.write(process.env.JEV_TEST_VALUE || '')\n", encoding="utf-8")
    scan.chmod(0o755)
    node_dir = tmp_path / "node-bin"
    node = fake_command(node_dir, "node", "import os; print(os.environ.get('JEV_TEST_VALUE', ''))\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("AICJ_")}
    env["PATH"] = str(node_dir) + os.pathsep + os.environ["PATH"]
    env["JEV_ENV_FILE"] = str(tmp_path / "jev.env")
    (tmp_path / "jev.env").write_text("# comment\nexport JEV_TEST_VALUE='from-file'\n", encoding="utf-8")
    result = subprocess.run([sys.executable, str(script), "data", "needle", str(repo)], env=env, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0
    assert "from-file" in result.stdout


@pytest.mark.parametrize("content, expected", [(None, "JEV_ENV_FILE not found"), ("BAD LINE\n", "failed to load JEV_ENV_FILE")])
def test_jev_consumer_rejects_missing_or_invalid_env_file(tmp_path, content, expected):
    repo = _large_jev_repo(tmp_path)
    claude = tmp_path / ".claude"
    (claude / "aicj/jev").mkdir(parents=True)
    (claude / "aicj/jev/consumer-template.json").write_text("{}\n", encoding="utf-8")
    scan = claude / "skills/jev-assist/scripts/consumer_scan.mjs"
    scan.parent.mkdir(parents=True)
    scan.write_text("", encoding="utf-8")
    env_file = tmp_path / "jev.env"
    if content is not None:
        env_file.write_text(content, encoding="utf-8")
    result = run_jev("data", "needle", str(repo), claude=claude, env_extra={"JEV_ENV_FILE": str(env_file)})
    assert result.returncode == 2 and expected in result.stderr


def test_verify_probe_requires_profile_and_ignores_sample(tmp_path):
    claude = tmp_path / ".claude"
    profile_dir = claude / "aicj/verify-profiles"
    profile_dir.mkdir(parents=True)
    (profile_dir / "example.json.sample").write_text("{}\n", encoding="utf-8")
    result = run_script(VERIFY / "bin/verify-probe", "missing", claude=claude)
    assert result.returncode == 2 and "profile" in result.stderr
    result = run_script(VERIFY / "bin/verify-probe", "--from-cwd", claude=claude)
    assert result.returncode == 2 and "未找到匹配" in result.stderr


def test_verify_probe_json_reports_probe_statuses(tmp_path):
    claude = tmp_path / ".claude"
    profile_dir = claude / "aicj/verify-profiles"
    profile_dir.mkdir(parents=True)
    profile = {
        "backend": {"root": str(tmp_path), "compile": {"probe_cmd": ["true"]}, "unit": {"probe_cmd": ["false"]}},
        "frontend": {"root": str(tmp_path), "unit": {"probe_cmd": ["true"]}},
        "e2e": {"root": str(tmp_path), "probe_cmd": ["true"]},
    }
    (profile_dir / "sample.json").write_text(json.dumps(profile), encoding="utf-8")
    result = run_script(VERIFY / "bin/verify-probe", "sample", "--json", claude=claude)
    payload = json.loads(result.stdout)
    statuses = {row["layer"]: row["status"] for row in payload["layers"]}
    assert result.returncode == 1 and statuses["backend-compile"] == "RUNNABLE"
    assert statuses["backend-unit"] == "BLOCKED" and payload["overall"] == "BLOCKED"


def test_optional_plugins_install_and_uninstall_round_trip(home):
    install = run_aicj("install", "--adapters", "jev,verify-probe", home=home, source=None)
    assert install.returncode == 0, install.stdout + install.stderr
    assert (home / ".claude/bin/jev-consumer").is_file()
    assert (home / ".claude/bin/verify-probe").is_file()
    assert (home / ".claude/aicj/verify-profiles/example.json.sample").is_file()
    assert run_aicj("uninstall", home=home, source=None).returncode == 0
    assert files_under(home) == []


PLUGIN_FORBIDDEN = re.compile(
    r"/Users/|~/\.claude|/home/\w+|opus|sonnet|haiku|gpt-|claude-\d|\bCPA\b|127\.0\.0\.1|worker-cc", re.I
)


def test_no_forbidden_terms_in_optional_plugins():
    hits = []
    for path in sorted((REPO / "adapters/optional-plugins").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            for match in PLUGIN_FORBIDDEN.finditer(path.read_text(encoding="utf-8")):
                hits.append(f"{path.relative_to(REPO)}: {match.group(0)}")
    assert hits == []
