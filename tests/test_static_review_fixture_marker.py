import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "static_review_check.py"
BAD_SQL = "update t_user set name = 'x';\n"


def run(*paths: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, paths)], text=True, capture_output=True)


def test_unmarked_bad_sample_is_blocked(tmp_path):
    sample = tmp_path / "bad.sql"
    sample.write_text(BAD_SQL)
    result = run(sample)
    assert result.returncode == 2
    assert "no where clause" in result.stdout


def test_marked_fixture_dir_is_skipped_for_files_and_dirs(tmp_path):
    fixtures = tmp_path / "fixtures"
    (fixtures / "nested").mkdir(parents=True)
    (fixtures / ".static-review-fixture").write_text("")
    sample = fixtures / "nested" / "bad.sql"
    sample.write_text(BAD_SQL)
    for target in (sample, tmp_path):
        result = run(target)
        assert result.returncode == 0
        assert "Scanned files: 0" in result.stdout
