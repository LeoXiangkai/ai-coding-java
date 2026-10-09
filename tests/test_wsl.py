from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import AICJ, REPO
from adapters.adapter_helpers import fake_command
from installer.lib import wsl


@pytest.mark.skipif(os.name == "nt", reason="WSL detection is disabled on native Windows")
def test_is_wsl_uses_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WSL_DISTRO_NAME", " Ubuntu ")
    assert wsl.is_wsl()


@pytest.mark.skipif(os.name == "nt", reason="WSL detection is disabled on native Windows")
def test_is_wsl_uses_kernel_release(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.setattr(Path, "read_text", lambda self, **kwargs: "5.15.90-MICROSOFT-standard")
    assert wsl.is_wsl()


def test_is_wsl_false_when_no_markers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.setattr(Path, "read_text", lambda self, **kwargs: "5.15.90-generic")
    assert not wsl.is_wsl()


def test_windows_mount_and_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("AICJ_WSL_MOUNT_ROOT", raising=False)
    assert wsl.windows_mount("/mnt/c/Users/x")
    assert wsl.windows_mount("/mnt/c")
    assert not wsl.windows_mount("/mnt/data/x")
    assert not wsl.windows_mount("/home/x")

    root = tmp_path / "automount"
    monkeypatch.setenv("AICJ_WSL_MOUNT_ROOT", str(root))
    assert wsl.windows_mount(root / "D" / "work")
    assert not wsl.windows_mount(root / "data" / "work")


def test_windows_mount_reads_wsl_conf_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    conf = tmp_path / "wsl.conf"
    monkeypatch.delenv("AICJ_WSL_MOUNT_ROOT", raising=False)
    monkeypatch.setattr(wsl, "WSL_CONF", conf)
    conf.write_text("[automount]\nroot = /\n", encoding="utf-8")
    assert wsl.windows_mount("/c/Users/x")
    assert not wsl.windows_mount("/home/x")
    conf.write_text('[automount]\nroot = "/win/"\n', encoding="utf-8")
    assert wsl.windows_mount("/win/d/x")


def _fake_wsl_commands(tmp_path: Path, record: Path, mount: Path, exit_code: int = 17, probe: str = "True") -> Path:
    commands = tmp_path / "commands"
    fake_command(
        commands,
        "wslpath",
        f"""
import sys
path = sys.argv[-1]
mount = {str(mount)!r}
if path.startswith(mount + '/C') or path == mount + '/C':
    print('C:' + path[len(mount) + 2 :].replace('/', chr(92)))
else:
    print(chr(92) * 2 + 'wsl.localhost' + chr(92) + 'Ubuntu' + path)
""",
    )
    fake_command(
        commands,
        "py.exe",
        f"""
import os, sys
if '-c' in sys.argv:
    print({probe!r})
else:
    open({str(record)!r}, 'w', encoding='utf-8').write(os.environ.get('AICJ_WSL_HANDOFF', '') + '\\n' + '\\n'.join(sys.argv[1:]))
    raise SystemExit({exit_code})
""",
    )
    return commands


def _run_handoff(tmp_path: Path, *extra: str, home: Path | None, source: Path | None = None, command: str = "install", env_extra: dict[str, str] | None = None):
    record = tmp_path / "handoff.txt"
    mount = tmp_path / "mnt"
    commands = _fake_wsl_commands(tmp_path, record, mount)
    env = {k: v for k, v in os.environ.items() if not k.startswith("AICJ_")}
    env.update({"WSL_DISTRO_NAME": "Ubuntu", "AICJ_WSL_MOUNT_ROOT": str(tmp_path / "mnt")})
    git = shutil.which("git")
    assert git is not None
    env["PATH"] = os.pathsep.join((str(commands), str(Path(git).parent)))
    if env_extra:
        env.update(env_extra)
    args = [sys.executable, str(AICJ), command]
    if home is not None:
        args += ["--home", str(home)]
    if source is not None:
        args += ["--source", str(source)]
    args += list(extra)
    return subprocess.run(args, cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", env=env), record


@pytest.mark.skipif(os.name == "nt", reason="uses POSIX fake wslpath and py.exe commands")
def test_handoff_converts_paths_preserves_arguments_and_status(tmp_path: Path) -> None:
    mount = tmp_path / "mnt"
    home = mount / "C" / "Users" / "x" / "aicj"
    source = mount / "C" / "repo"
    project = mount / "C" / "project"
    result, record = _run_handoff(tmp_path, "--dry-run", "--packs", "java,vue", "--project", str(project), home=home, source=source)
    assert result.returncode == 17
    lines = record.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "1"
    assert lines[1:] == ["-3", r"\\wsl.localhost\Ubuntu" + str(AICJ), "install", "--home", r"C:\Users\x\aicj", "--source", r"C:\repo", "--dry-run", "--packs", "java,vue", "--project", r"C:\project"]
    assert "已转交 Windows Python" in result.stderr


@pytest.mark.skipif(os.name == "nt", reason="uses POSIX fake wslpath and py.exe commands")
def test_non_windows_home_does_not_handoff(tmp_path: Path) -> None:
    source = tmp_path / "source"
    shutil.copytree(REPO / "tests/fixtures/fake-component", source)
    result, record = _run_handoff(tmp_path, "--dry-run", home=tmp_path / "home", source=source)
    assert result.returncode == 0
    assert not record.exists()
    assert "已转交" not in result.stderr


@pytest.mark.skipif(os.name == "nt", reason="uses POSIX fake wslpath and py.exe commands")
def test_handoff_guard_prevents_recursion(tmp_path: Path) -> None:
    result, record = _run_handoff(tmp_path, "--dry-run", home=tmp_path / "mnt" / "C" / "home", env_extra={"AICJ_WSL_HANDOFF": "1"})
    assert result.returncode == 0
    assert not record.exists()
    assert "已转交" not in result.stderr


@pytest.mark.skipif(os.name == "nt", reason="uses POSIX fake wslpath and py.exe commands")
@pytest.mark.parametrize("command", ["uninstall", "doctor"])
def test_handoff_converts_equals_paths_and_commands(tmp_path: Path, command: str) -> None:
    mount = tmp_path / "mnt"
    home = mount / "C" / "Users" / "x" / "aicj"
    extra = ("--home=" + str(home),) if command == "doctor" else ("--home=" + str(home), "--source=" + str(mount / "C" / "repo"))
    result, record = _run_handoff(tmp_path, *extra, home=None, command=command)
    assert result.returncode == 17
    lines = record.read_text(encoding="utf-8").splitlines()
    assert lines[3] == command
    assert any(r"C:\Users\x\aicj" in line for line in lines)


@pytest.mark.skipif(os.name == "nt", reason="uses POSIX fake wslpath and py.exe commands")
def test_handoff_drops_link_and_adds_home_from_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mount = tmp_path / "mnt"
    home = mount / "C" / "Users" / "x" / "aicj"
    monkeypatch.setenv("HOME", str(home))
    result, record = _run_handoff(tmp_path, "--link", "--dry-run", home=None)
    assert result.returncode == 17
    lines = record.read_text(encoding="utf-8").splitlines()
    assert "--link" not in lines[3:]
    assert lines[4:] == ["--dry-run", "--home", r"C:\Users\x\aicj"]
    assert "不支持 --link" in result.stderr


@pytest.mark.skipif(os.name == "nt", reason="uses POSIX fake wslpath and py.exe commands")
def test_handoff_converts_relative_home(tmp_path: Path) -> None:
    mount = tmp_path / "mnt"
    cwd = mount / "C" / "work"
    cwd.mkdir(parents=True)
    record = tmp_path / "handoff.txt"
    commands = _fake_wsl_commands(tmp_path, record, mount)
    env = {k: v for k, v in os.environ.items() if not k.startswith("AICJ_")}
    env.update({"WSL_DISTRO_NAME": "Ubuntu", "AICJ_WSL_MOUNT_ROOT": str(mount), "PATH": os.pathsep.join((str(commands), str(Path(shutil.which("git")).parent)))})
    result = subprocess.run([sys.executable, str(AICJ), "install", "--home", "../home", "--dry-run"], cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=env)
    assert result.returncode == 17
    assert r"C:\home" in record.read_text(encoding="utf-8")


def test_python_exe_fallback_and_missing_python(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(wsl.shutil, "which", lambda name: "/python.exe" if name == "python.exe" else None)
    monkeypatch.setattr(wsl.subprocess, "run", lambda command, **kwargs: (calls.append(command) or type("Result", (), {"returncode": 0, "stdout": "True\n", "stderr": ""})()))
    assert wsl.find_windows_python() == ("/python.exe", [])
    assert calls == [["/python.exe", "-c", "import sys;print(sys.version_info[:2] >= (3, 9))"]]
    monkeypatch.setattr(wsl.shutil, "which", lambda name: None)
    assert "python.org" in str(wsl.windows_python_missing_error())


def test_python_probe_must_report_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wsl.shutil, "which", lambda name: "/py.exe")
    monkeypatch.setattr(wsl.subprocess, "run", lambda command, **kwargs: type("Result", (), {"returncode": 0, "stdout": "False\n", "stderr": ""})())
    assert wsl.find_windows_python() is None


@pytest.mark.skipif(os.name == "nt", reason="native Windows is not a WSL handoff environment")
def test_both_windows_python_missing_returns_actionable_error(tmp_path: Path) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("AICJ_")}
    env.update({"WSL_DISTRO_NAME": "Ubuntu", "AICJ_WSL_MOUNT_ROOT": str(tmp_path / "mnt"), "PATH": str(tmp_path / "empty")})
    result = subprocess.run(
        [sys.executable, str(AICJ), "install", "--home", str(tmp_path / "mnt" / "C" / "home"), "--dry-run"],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert result.returncode == 2
    assert "python.org" in result.stderr
    assert "winget install Python.Python.3.12" in result.stderr
    assert "py -3 installer/aicj.py" in result.stderr


@pytest.mark.skipif(os.name == "nt", reason="uses POSIX fake wslpath and py.exe commands")
def test_source_on_windows_mount_warns_and_install_continues(tmp_path: Path) -> None:
    source = tmp_path / "mnt" / "C" / "source"
    shutil.copytree(REPO / "tests/fixtures/fake-component", source)
    result, _record = _run_handoff(tmp_path, "--dry-run", home=tmp_path / "home", source=source)
    assert result.returncode == 0
    assert "仓库位于 Windows 盘" in result.stderr
