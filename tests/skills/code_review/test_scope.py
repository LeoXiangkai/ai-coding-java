import atexit
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


# scope.py appends every gate decision to the review log; keep test runs out of the
# repo's core/aicj (default derivation points there) by pinning a throwaway dir.
_MODULE_LOG_DIR = tempfile.mkdtemp(prefix="aicj-scope-test-")
os.environ["AICJ_REVIEW_LOG_DIR"] = _MODULE_LOG_DIR
atexit.register(shutil.rmtree, _MODULE_LOG_DIR, ignore_errors=True)

SKILL_DIR = Path(__file__).resolve().parents[3] / "core" / "skills" / "code-review"
SCOPE_SCRIPT = SKILL_DIR / "scripts" / "scope.py"
REVIEW_LOG_DIR_ENV = "AICJ_REVIEW_LOG_DIR"


def run(*args: str, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


class GitRepository:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True)
        self.git("init", "-q")
        self.git("config", "user.email", "review-scope@example.test")
        self.git("config", "user.name", "Review Scope Test")
        self.write("README.md", "baseline\n")
        self.git("add", "README.md")
        self.git("commit", "-qm", "baseline")
        self.base_oid = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("switch", "-qc", "feature/review-scope")
        self.git("config", "branch.feature/review-scope.baseline", "master")
        self.git("config", "branch.feature/review-scope.fork-oid", self.base_oid)

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        result = run("git", *args, cwd=self.root)
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return result

    def write(self, relative_path: str, content: str) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def scope(self, effort: str = "medium") -> dict:
        result = run(
            "python3",
            str(SCOPE_SCRIPT),
            "--target",
            str(self.root),
            "--effort",
            effort,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)


class ScopeTests(unittest.TestCase):
    def test_target_repository_never_includes_sibling_repository_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            frontend = GitRepository(parent / "preschool-frontend")
            backend = GitRepository(parent / "preschool-service")
            frontend.write("apps/admin/src/main.ts", "export const changed = true;\n")
            backend.write("src/main/java/ConfigController.java", "class Changed {}\n")

            result = frontend.scope(effort="high")

            self.assertEqual(Path(result["repo_root"]), frontend.root.resolve())
            self.assertEqual(result["branch"], "feature/review-scope")
            self.assertEqual(result["base_oid"], frontend.base_oid)
            self.assertEqual(result["files"], ["apps/admin/src/main.ts"])
            self.assertNotIn(str(backend.root), json.dumps(result))

    def test_out_of_repository_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            repo = GitRepository(parent / "repo")
            sibling = parent / "sibling-secret.txt"
            sibling.write_text("permission password credential\n", encoding="utf-8")
            link = repo.root / "src" / "linked-secret.txt"
            link.parent.mkdir(parents=True)
            link.symlink_to(sibling)

            result = run(
                "python3",
                str(SCOPE_SCRIPT),
                "--target",
                str(repo.root),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("resolves outside repository", result.stderr)

    def test_out_of_repository_symlink_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            repo = GitRepository(parent / "repo")
            sibling = parent / "sibling"
            sibling.mkdir()
            (sibling / "changed.ts").write_text(
                "export const permission = 'outside';\n", encoding="utf-8"
            )
            (repo.root / "src").mkdir()
            (repo.root / "src" / "link-dir").symlink_to(sibling, target_is_directory=True)

            result = run(
                "python3",
                str(SCOPE_SCRIPT),
                "--target",
                str(repo.root),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("resolves outside repository", result.stderr)

    def test_small_or_medium_low_impact_diff_skips_independent_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = GitRepository(Path(tmp) / "repo")
            for index in range(6):
                repo.write(
                    f"src/component-{index}.ts",
                    "\n".join(f"export const value{line} = {line};" for line in range(30)) + "\n",
                )

            result = repo.scope(effort="max")

            self.assertEqual(result["file_count"], 6)
            self.assertLessEqual(result["changed_lines"], 300)
            self.assertEqual(result["risk_signals"], [])
            self.assertEqual(result["review_gate"], "skip")
            self.assertEqual(result["max_reviewers"], 0)

    def test_contract_and_dml_diff_uses_exactly_one_reviewer_even_at_high_effort(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = GitRepository(Path(tmp) / "repo")
            repo.write(
                "apps/admin/src/api/config.ts",
                "export interface Config { defaultAdminHome?: string }\n",
            )
            repo.write(
                "docs/sql/V20260915__admin_default_home.sql",
                "INSERT INTO sys_dic(param_type, param_name) VALUES ('admin', 'defaultHome');\n",
            )

            result = repo.scope(effort="high")

            self.assertEqual(
                set(result["risk_signals"]),
                {"api-contract", "database-migration"},
            )
            self.assertEqual(result["review_gate"], "single")
            self.assertEqual(result["max_reviewers"], 1)

    def test_unchanged_risky_words_do_not_raise_diff_risk(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = GitRepository(Path(tmp) / "repo")
            repo.write(
                "src/config.ts",
                "export const permission = 'existing';\nexport const label = 'before';\n",
            )
            repo.git("add", "src/config.ts")
            repo.git("commit", "-qm", "add existing risky vocabulary")
            repo.base_oid = repo.git("rev-parse", "HEAD").stdout.strip()
            repo.git("config", "branch.feature/review-scope.fork-oid", repo.base_oid)
            repo.write(
                "src/config.ts",
                "export const permission = 'existing';\nexport const label = 'after';\n",
            )

            result = repo.scope()

            self.assertEqual(result["risk_signals"], [])
            self.assertEqual(result["review_gate"], "skip")

    def test_only_large_multi_domain_diff_can_become_dual_review_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = GitRepository(Path(tmp) / "repo")
            for index in range(31):
                directory = "auth" if index < 16 else "migration"
                suffix = ".java" if directory == "auth" else ".sql"
                content = (
                    "public class PermissionPolicy { boolean authorized; }\n"
                    if directory == "auth"
                    else "ALTER TABLE account ADD audit_flag NUMBER(1);\n"
                )
                repo.write(f"src/{directory}/change-{index}{suffix}", content)

            result = repo.scope(effort="low")

            self.assertGreater(result["file_count"], 30)
            self.assertIn("authorization-security", result["risk_signals"])
            self.assertIn("database-migration", result["risk_signals"])
            self.assertEqual(result["review_gate"], "dual-candidate")
            self.assertEqual(result["max_reviewers"], 2)

    def test_default_log_dir_derives_from_script_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            repo = GitRepository(parent / "repo")
            repo.write("src/change.ts", "export const changed = true;\n")
            env = {k: v for k, v in os.environ.items() if k != "AICJ_REVIEW_LOG_DIR"}

            # default: derived from the script location -> <claude>/aicj/review-logs
            result = run(
                "python3",
                str(SCOPE_SCRIPT),
                "--target",
                str(repo.root),
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            default_log = SKILL_DIR.parents[1] / "aicj" / "review-logs" / "code-review-gates.jsonl"
            try:
                self.assertTrue(default_log.exists(), default_log)
            finally:
                if default_log.exists():
                    default_log.unlink()
                for directory in (default_log.parent, default_log.parent.parent):
                    try:
                        directory.rmdir()
                    except OSError:
                        pass

    def test_review_log_dir_env_writes_to_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            env_dir = parent / "custom-logs"
            repo = GitRepository(parent / "repo")
            repo.write("src/change2.ts", "export const changed2 = true;\n")
            result = run(
                "python3",
                str(SCOPE_SCRIPT),
                "--target",
                str(repo.root),
                env={**os.environ, "AICJ_REVIEW_LOG_DIR": str(env_dir)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((env_dir / "code-review-gates.jsonl").exists())

    def test_coordination_key_is_stable_per_repository_branch_and_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            first = GitRepository(parent / "first")
            second = GitRepository(parent / "second")
            first.write("src/change.ts", "export const changed = true;\n")
            second.write("src/change.ts", "export const changed = true;\n")

            first_result = first.scope()
            repeated_result = first.scope()
            second_result = second.scope()

            self.assertEqual(first_result["coordination_key"], repeated_result["coordination_key"])
            self.assertNotEqual(first_result["coordination_key"], second_result["coordination_key"])

    def test_outcome_record_includes_common_dir_head_oid_review_gate_and_blobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_log = Path(tmp) / "review-logs"
            env_log.mkdir()
            repo = GitRepository(Path(tmp) / "repo")
            repo.write("src/change.ts", "export const changed = true;\n")

            result = subprocess.run(
                [
                    "python3",
                    str(SCOPE_SCRIPT),
                    "--target",
                    str(repo.root),
                    "--outcome",
                    "--reviewers",
                    "1",
                    "--findings",
                    "0",
                    "--confirmed",
                    "0",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, REVIEW_LOG_DIR_ENV: str(env_log)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = (env_log / "code-review-gates.jsonl").read_text(encoding="utf-8").splitlines()
            record = json.loads(lines[-1])
            self.assertEqual(record["kind"], "outcome")
            self.assertIn("common_dir", record)
            self.assertTrue(Path(record["common_dir"]).is_dir())
            self.assertIn("head_oid", record)
            self.assertEqual(record["head_oid"], repo.git("rev-parse", "HEAD").stdout.strip())
            self.assertIn("review_gate", record)
            self.assertIn("reviewed_blobs", record)
            self.assertEqual(
                record["reviewed_blobs"],
                {"src/change.ts": repo.git("hash-object", "src/change.ts").stdout.strip()},
            )

    def test_outcome_blobs_match_hash_object_per_file_including_deletion_and_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_log = Path(tmp) / "review-logs"
            env_log.mkdir()
            repo = GitRepository(Path(tmp) / "repo")
            # Baseline files that will later be deleted/modified
            repo.write("path/with spaces/file a.txt", "space content\n")
            repo.write("to-delete.txt", "will be removed\n")
            repo.write("normal.txt", "normal v1\n")
            repo.git("add", "path/with spaces/file a.txt", "to-delete.txt", "normal.txt")
            repo.git("commit", "-qm", "baseline extras")
            repo.base_oid = repo.git("rev-parse", "HEAD").stdout.strip()
            repo.git("config", "branch.feature/review-scope.fork-oid", repo.base_oid)

            # Worktree changes: modify, delete, add
            repo.write("path/with spaces/file a.txt", "space content changed\n")
            (repo.root / "to-delete.txt").unlink()
            repo.write("normal.txt", "normal v2\n")
            repo.write("added.txt", "new file\n")

            result = subprocess.run(
                [
                    "python3",
                    str(SCOPE_SCRIPT),
                    "--target",
                    str(repo.root),
                    "--outcome",
                    "--reviewers",
                    "1",
                    "--findings",
                    "0",
                    "--confirmed",
                    "0",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, REVIEW_LOG_DIR_ENV: str(env_log)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = (env_log / "code-review-gates.jsonl").read_text(encoding="utf-8").splitlines()
            record = json.loads(lines[-1])
            reviewed_blobs = record.get("reviewed_blobs", {})
            self.assertIn("path/with spaces/file a.txt", reviewed_blobs)
            self.assertIn("to-delete.txt", reviewed_blobs)
            self.assertIn("normal.txt", reviewed_blobs)
            self.assertIn("added.txt", reviewed_blobs)
            self.assertIsNone(reviewed_blobs["to-delete.txt"])
            for rel_path, blob in reviewed_blobs.items():
                if blob is None:
                    continue
                expected = repo.git("hash-object", rel_path).stdout.strip()
                self.assertEqual(blob, expected, rel_path)


if __name__ == "__main__":
    unittest.main()
