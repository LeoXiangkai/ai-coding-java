from __future__ import annotations

from pathlib import Path

from conftest import run_sanitize


def make_tree(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def test_clean_tree_passes(tmp_path: Path) -> None:
    make_tree(tmp_path, {"core/rules/ok.md": "# nothing personal\n"})
    result = run_sanitize(tmp_path)
    assert result.returncode == 0, result.stdout
    assert "Summary: 0 sanitize issue(s)" in result.stdout


def test_builtin_patterns_each_fail(tmp_path: Path) -> None:
    cases = {
        "core/a.md": "path is /Users/alice/project/x\n",
        "core/b.md": "service at 127.0.0.1:8317\n",
        "core/c.md": "run worker-cc --model opus\n",
        "core/d.md": "key sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ012345\n",
        "core/e.md": "token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456\n",
        "core/f.md": "aws AKIAIOSFODNN7EXAMPLE1\n",
        "core/g.md": "export API_TOKEN=super-secret-value\n",
        "core/h.md": "-----BEGIN RSA PRIVATE KEY-----\n",
    }
    make_tree(tmp_path, cases)
    result = run_sanitize(tmp_path)
    assert result.returncode == 1
    for name in (
        "personal-abs-path",
        "loopback-port",
        "private-executor",
        "secret-key-sk",
        "secret-key-ghp",
        "secret-key-akia",
        "secret-token-assign",
        "secret-private-key",
    ):
        assert name in result.stdout, name


def test_home_paths_also_caught(tmp_path: Path) -> None:
    make_tree(tmp_path, {"packs/p/rule.md": "see /home/bob/data\n"})
    result = run_sanitize(tmp_path)
    assert result.returncode == 1
    assert "personal-abs-path" in result.stdout


def test_extra_patterns_from_env_file(tmp_path: Path) -> None:
    make_tree(tmp_path, {"core/rule.md": "mentions personname-example by name\n"})
    extra = tmp_path / "extra.txt"
    extra.write_text("# personal names\npersonname-example\n", encoding="utf-8")

    result = run_sanitize(tmp_path, extra=extra)
    assert result.returncode == 1
    assert "extra:2" in result.stdout

    result = run_sanitize(tmp_path)
    assert result.returncode == 0, result.stdout


def test_executor_examples_whitelist(tmp_path: Path) -> None:
    files = {
        "adapters/executor/examples/run.md": "calls worker-cc --model sonnet\n",
        "core/rule.md": "calls worker-cc --model sonnet\n",
    }
    make_tree(tmp_path, files)
    result = run_sanitize(tmp_path)
    assert result.returncode == 1
    lines = [line for line in result.stdout.splitlines() if line.startswith("FAIL")]
    assert len(lines) == 1
    assert "core/rule.md" in lines[0]
    assert "adapters/executor/examples/" not in lines[0]


def test_repo_tree_itself_is_clean() -> None:
    from conftest import REPO

    result = run_sanitize(REPO)
    assert result.returncode == 0, result.stdout
