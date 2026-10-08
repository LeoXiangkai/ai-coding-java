import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[3] / "core" / "skills" / "code-review"
SKILL = SKILL_DIR / "SKILL.md"
SCOPE_SCRIPT = SKILL_DIR / "scripts" / "scope.py"


class SkillContractTests(unittest.TestCase):
    def test_skill_encodes_repository_branch_boundary_and_reviewer_cap(self):
        text = SKILL.read_text(encoding="utf-8")

        required_phrases = [
            "repository root + current branch",
            "Never read sibling repositories",
            "effort does not increase reviewer count",
            "at most two reviewer agents",
            "fresh scoped reviewer agent",
            "default mid-tier model",
            "must not call Agent, Skill, or /code-review",
            "same repository root + branch",
        ]
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertNotIn("subagent_type: fork", text)
        self.assertNotIn("sonnet", text)

    def test_scope_script_has_hard_reviewer_cap(self):
        text = SCOPE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("MAX_REVIEWERS = 2", text)
        self.assertNotIn("effort_to_reviewers", text)

    def test_paths_derive_from_environment_or_script_location(self):
        text = SCOPE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("AICJ_CLAUDE_DIR", text)
        self.assertIn("AICJ_REVIEW_LOG_DIR", text)
        self.assertNotIn("CLAUDE_EVAL_LOG_DIR", text)
        self.assertNotIn('Path.home() / ".claude"', text)

    def test_skill_has_no_personal_model_or_executor_names(self):
        for path in (SKILL, SCOPE_SCRIPT):
            text = path.read_text(encoding="utf-8")
            for banned in ("sonnet", "opus", "haiku", "worker-cc"):
                self.assertNotIn(banned, text, f"{path.name} mentions {banned}")


if __name__ == "__main__":
    unittest.main()
