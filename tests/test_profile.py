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

    def test_chinese_java_graduation_idea_keeps_both_domain_and_language(self):
        profile = build_profile("idea", "学习Java的毕设设计项目", capabilities=["database", "后台管理"])
        self.assertIn("Java / JVM", profile["stack"])
        self.assertIn("graduation-project", profile["capabilities"])
        self.assertTrue(all("Java" in query for query in profile["queries"]))
        self.assertTrue(all("graduation-project" in query or "毕业设计" in query for query in profile["queries"]))
        self.assertIn("database", " ".join(profile["queries"]))
        self.assertIn("后台管理", " ".join(profile["queries"]))
        self.assertNotIn("/", " ".join(profile["queries"]))
        self.assertNotIn("JVM", " ".join(profile["queries"]))

    def test_ascii_identifier_boundaries_do_not_turn_javascript_or_names_into_java(self):
        for idea in ["学习JavaScript的毕设", "JavaHelper for students", "MyJava tools", "java_helper utilities"]:
            with self.subTest(idea=idea):
                self.assertNotIn("Java / JVM", build_profile("idea", idea)["stack"])
        self.assertIn("JavaScript", build_profile("idea", "学习JavaScript的毕设")["stack"])
        self.assertIn("Java / JVM", build_profile("idea", "Java-based capstone")["stack"])

    def test_chinese_and_english_image_creation_goals_have_specific_capabilities(self):
        for idea in ["使用ComfyUI和Diffusers做AI创作，文生图", "AI creation and image-generation with ComfyUI Diffusers PyTorch Transformers"]:
            with self.subTest(idea=idea):
                profile = build_profile("idea", idea)
                self.assertIn("ComfyUI", profile["stack"])
                self.assertIn("Diffusers", profile["stack"])
                self.assertIn("image-generation", profile["capabilities"])
                self.assertIn("ai-creation", profile["capabilities"])
                self.assertNotIn("video-generation", profile["capabilities"])
                self.assertTrue(all("image-generation" in query for query in profile["queries"]))
        english = build_profile("idea", "image-generation with PyTorch Transformers")
        self.assertIn("PyTorch", english["stack"])
        self.assertIn("Transformers", english["stack"])

    def test_video_and_audio_queries_keep_video_domain_instead_of_image(self):
        for idea in ["用FFmpeg做视频剪辑、音频配音，并尝试文生视频", "video generation with FFmpeg Blender, video editing and audio"]:
            with self.subTest(idea=idea):
                profile = build_profile("idea", idea)
                self.assertIn("FFmpeg", profile["stack"])
                self.assertTrue({"video-generation", "video-editing", "audio"}.issubset(profile["capabilities"]))
                self.assertNotIn("image-generation", profile["capabilities"])
                self.assertTrue(all("video-generation" in query for query in profile["queries"]))

    def test_creative_tools_require_dependencies_or_tool_declarations_in_manifests(self):
        stack = detect_stack({
            "requirements.txt": "torch>=2\ndiffusers\ntransformers\nffmpeg-python\nbpy\ncomfyui\n",
            "pyproject.toml": '[project]\nname="creative"\ndependencies=["diffusers>=0.30", "torch>=2"]\n',
        })
        self.assertTrue({"ComfyUI", "Diffusers", "PyTorch", "Transformers", "FFmpeg", "Blender"}.issubset(stack))
        descriptions = detect_stack({
            "package.json": json.dumps({"description": "ComfyUI Diffusers PyTorch Transformers FFmpeg Blender", "dependencies": {"vue": "3"}}),
            "pyproject.toml": '[project]\ndescription="ComfyUI Diffusers PyTorch Transformers FFmpeg Blender"\ndependencies=["fastapi"]\n',
            "requirements.txt": "# torch diffusers transformers ffmpeg-python bpy comfyui\nfastapi\n",
            "Dockerfile": 'FROM python:3\nRUN echo "Blender and FFmpeg are not installed"\n',
        })
        self.assertFalse({"ComfyUI", "Diffusers", "PyTorch", "Transformers", "FFmpeg", "Blender"} & set(descriptions))
        self.assertIn("FFmpeg", detect_stack({"Dockerfile": "FROM python:3\nRUN apt-get install ffmpeg && echo Blender\n"}))
        self.assertNotIn("Blender", detect_stack({"Dockerfile": "FROM python:3\nRUN apt-get install ffmpeg && echo Blender\n"}))
        self.assertNotIn("PyTorch", detect_stack({"Dockerfile": 'FROM python:3\nRUN echo "pip install torch"\n'}))
        self.assertTrue({"Diffusers", "PyTorch"}.issubset(detect_stack({"pyproject.toml": '[project]\ndependencies=["diffusers[torch]>=0.30", "torch>=2"]\n'})))
        self.assertIn("Blender", detect_stack({"setup.py": 'from setuptools import setup\nsetup(install_requires=["bpy>=4"])\n'}))
        self.assertIn("Transformers", detect_stack({"setup.cfg": "[options]\ninstall_requires =\n transformers>=4\n"}))
        self.assertIn("FFmpeg", detect_stack({"compose.yml": "services:\n media:\n  image: ffmpeg:latest\n"}))

    def test_constraints_are_explicit_deduplicated_and_not_sent_as_search_terms(self):
        profile = build_profile("idea", "用ComfyUI在8GB显存电脑上文生图")
        self.assertEqual(profile["constraints"], [])
        explicit = build_profile("idea", "Java capstone", constraints=[" CPU only ", "MIT license", "cpu ONLY"])
        self.assertEqual(explicit["constraints"], ["CPU only", "MIT license"])
        self.assertNotIn("CPU", " ".join(explicit["queries"]))
        self.assertNotIn("MIT", " ".join(explicit["queries"]))
        with tempfile.TemporaryDirectory(prefix="private-client-") as directory:
            root = Path(directory)
            (root / "requirements.txt").write_text("diffusers", encoding="utf-8")
            local = build_profile("local", root, constraints=["CPU only"])
            self.assertEqual(local["constraints"], ["CPU only"])
            self.assertNotIn(root.name, " ".join(local["queries"]))
            self.assertNotIn(str(root), json.dumps(local))

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
        for invalid in ["CPU only", [1]]:
            with self.assertRaises(ValueError):
                build_profile("idea", "chat", constraints=invalid)


if __name__ == "__main__":
    unittest.main()
