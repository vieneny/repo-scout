import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/repo-scout/scripts"))
from scout.profile import build_profile, detect_stack


class ProfileTests(unittest.TestCase):
    def test_local_retains_only_technology_names_and_relative_paths(self):
        with tempfile.TemporaryDirectory(prefix="scout-private-") as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"name": "private-package", "description": "secret description", "dependencies": {"react": "^19", "@company/private-token": "secret-value"}}), encoding="utf-8")
            (root / ".env").write_text("TOKEN=very-secret", encoding="utf-8")
            (root / "private").mkdir()
            (root / "private/pyproject.toml").write_text('dependencies=["langchain"]', encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules/requirements.txt").write_text("django", encoding="utf-8")
            profile = build_profile("local", root)
            encoded = json.dumps(profile)
            self.assertIn("React", profile["stack"])
            self.assertNotIn("Django", profile["stack"])
            self.assertNotIn("LangChain", profile["stack"])
            for forbidden in (str(root), "secret-value", "very-secret", "private-package", "secret description"):
                self.assertNotIn(forbidden, encoded)
            self.assertEqual(profile["observations"][0]["path"], "package.json")
            self.assertNotIn(root.name, " ".join(profile["queries"]))

    def test_symlink_manifest_is_not_followed(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            outside = Path(external) / "requirements.txt"
            outside.write_text("langchain", encoding="utf-8")
            try:
                (root / "requirements.txt").symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("Symlink creation unavailable")
            self.assertNotIn("LangChain", build_profile("local", root)["stack"])

    def test_idea_extracts_technologies_and_capabilities(self):
        profile = build_profile("idea", "Learn LangChain RAG agents with FastAPI", capabilities=["rag"], audience="individual")
        self.assertIn("LangChain", profile["stack"])
        self.assertIn("FastAPI", profile["stack"])
        self.assertIn("rag", profile["capabilities"])
        self.assertTrue(profile["queries"])

    def test_supplied_language_does_not_drop_named_framework_anchor(self):
        profile = build_profile("idea", "学习 LangChain，构建个人 RAG 助手", stack=["Python"], capabilities=["RAG"])
        self.assertEqual(profile["stack"], ["Python", "LangChain"])
        self.assertEqual(profile["capabilities"], ["RAG"])
        self.assertTrue(all("LangChain" in query for query in profile["queries"]))
        self.assertIn("RAG", profile["queries"][0])

    def test_manifest_detection_ignores_arbitrary_description_mentions(self):
        stack = detect_stack({"package.json": json.dumps({"description": "Not a React project", "dependencies": {"vue": "3"}}), "pyproject.toml": '[project]\ndependencies=["langgraph>=1", "psycopg[binary]"]'})
        self.assertIn("Vue", stack)
        self.assertNotIn("React", stack)
        self.assertIn("LangGraph", stack)
        self.assertIn("PostgreSQL", stack)

    def test_invalid_inputs_are_explicit(self):
        with self.assertRaises(ValueError):
            build_profile("local", "/a/path/that/does/not/exist")
        with self.assertRaises(ValueError):
            build_profile("idea", "")
        with self.assertRaises(ValueError):
            build_profile("idea", "chat", audience="everyone")


if __name__ == "__main__":
    unittest.main()
