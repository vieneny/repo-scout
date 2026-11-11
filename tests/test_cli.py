import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).parents[1] / "skills/repo-scout/scripts"))
from scout.cli import discover, main, inspect_envelope
from scout.providers import ProviderError


class FakeProvider:
    def search(self, query, limit=8):
        if query == "failed":
            raise ProviderError("Service unavailable")
        return [{"id": "github:a/" + query, "provider": "github", "name": "a/" + query, "description": query, "url": "https://github.com/a/" + query}]

    def inspect(self, candidate):
        return dict(candidate, signals={"tests": True})


class MultiProvider:
    def __init__(self, source, calls):
        self.source = source
        self.calls = calls

    def _candidate(self, name):
        host = {"github": "github.com", "gitee": "gitee.com", "gitlab": "gitlab.com"}[self.source]
        return {"id": self.source + ":" + name, "provider": self.source, "name": name, "description": name, "url": "https://" + host + "/" + name}

    def search(self, query, limit=8):
        self.calls.append(("search", self.source, query, limit))
        return [self._candidate("test/" + query + "-" + str(index)) for index in range(1, limit + 1)]

    def resolve(self, url):
        self.calls.append(("resolve", self.source, url))
        return self._candidate(urlsplit(url).path.strip("/").removesuffix(".git"))

    def inspect(self, candidate):
        self.calls.append(("inspect", self.source, candidate["id"]))
        return dict(candidate, signals={"tests": True})


class CLITests(unittest.TestCase):
    def test_failed_search_is_not_a_successful_zero_result(self):
        with patch("scout.cli.get_provider", return_value=FakeProvider()):
            result = discover({"title": "test", "queries": ["failed", "good"]}, ["github"])
        self.assertEqual([row["status"] for row in result["receipts"]], ["error", "ok"])
        self.assertIsNone(result["receipts"][0]["count"])
        self.assertEqual(len(result["candidates"]), 1)

    def test_local_directory_name_is_never_a_fallback_query(self):
        with patch("scout.cli.get_provider") as provider:
            with self.assertRaises(ValueError):
                discover({"kind": "local", "title": "secret-client-name", "queries": []}, ["github"])
        provider.assert_not_called()

    def test_inspection_records_unreviewed_tail(self):
        with patch("scout.cli.get_provider", return_value=FakeProvider()):
            envelope = discover({"title": "test", "queries": ["one", "two"]}, ["github"])
            result = inspect_envelope(envelope, 1)
        self.assertEqual(result["inspection"], {"available": 2, "inspected": 1, "unreviewed": 1})

    def test_small_budget_interleaves_providers_before_deeper_hits(self):
        calls = []
        with patch("scout.cli.get_provider", side_effect=lambda source: MultiProvider(source, calls)):
            envelope = discover({"title": "test", "queries": ["one"]}, ["github", "gitee", "gitlab"], limit=2)
            result = inspect_envelope(envelope, limit=2)
        self.assertEqual([item["provider"] for item in envelope["candidates"]], ["github", "gitee", "gitlab", "github", "gitee", "gitlab"])
        self.assertEqual([item["provider"] for item in result["candidates"]], ["github", "gitee"])
        self.assertEqual(result["inspection"], {"available": 6, "inspected": 2, "unreviewed": 4})
        self.assertEqual(envelope["candidates"][2]["discovery"], [{"query": "one", "type": "search", "provider": "gitlab"}])

    def test_interleaving_distinguishes_each_provider_query_pair(self):
        calls = []
        with patch("scout.cli.get_provider", side_effect=lambda source: MultiProvider(source, calls)):
            result = discover({"title": "test", "queries": ["one", "two"]}, ["github", "gitee", "gitlab"], limit=2)
        self.assertEqual([item["id"] for item in result["candidates"][:6]], [
            "github:test/one-1", "gitee:test/one-1", "gitlab:test/one-1",
            "github:test/two-1", "gitee:test/two-1", "gitlab:test/two-1",
        ])

    def test_supplied_seed_reserves_slot_and_merges_discovered_provenance(self):
        calls = []
        with patch("scout.cli.get_provider", side_effect=lambda source: MultiProvider(source, calls)):
            envelope = discover({"title": "test", "queries": ["one"]}, ["github", "gitee", "gitlab"], limit=2, seeds=["https://gitlab.com/test/one-2"])
            result = inspect_envelope(envelope, limit=2)
        seed = result["candidates"][0]
        self.assertEqual(seed["id"], "gitlab:test/one-2")
        self.assertEqual([hit["type"] for hit in seed["discovery"]], ["supplied", "search"])
        self.assertEqual(sum(item["id"] == seed["id"] for item in envelope["candidates"]), 1)
        self.assertEqual(result["candidates"][1]["id"], "github:test/one-1")
        self.assertEqual(envelope["receipts"][0]["type"], "supplied")

    def test_seed_aliases_share_one_slot_but_excess_distinct_seeds_fail(self):
        calls = []
        with patch("scout.cli.get_provider", side_effect=lambda source: MultiProvider(source, calls)):
            result = discover({"title": "test", "queries": ["one"]}, ["github"], limit=2,
                              seeds=["https://github.com/test/seed", "https://github.com/test/seed.git"])
        self.assertEqual(result["candidates"][0]["id"], "github:test/seed")
        self.assertEqual(sum(item["id"] == "github:test/seed" for item in result["candidates"]), 1)
        calls.clear()
        with patch("scout.cli.get_provider", side_effect=lambda source: MultiProvider(source, calls)):
            with self.assertRaisesRegex(ValueError, "exceed.*inspection budget"):
                discover({"title": "test", "queries": ["one"]}, ["github", "gitee", "gitlab"], limit=2,
                         seeds=["https://github.com/test/a", "https://gitee.com/test/b", "https://gitlab.com/test/c"])
        self.assertFalse(any(call[0] == "search" for call in calls))

    def test_excess_seed_resolution_budget_fails_before_network(self):
        with patch("scout.cli.get_provider") as provider:
            with self.assertRaisesRegex(ValueError, "at most 30 distinct"):
                discover({"title": "test", "queries": ["one"]}, ["github"], limit=2,
                         seeds=["https://github.com/test/seed-" + str(index) for index in range(31)])
        provider.assert_not_called()

    def test_offline_cli_profile_score_and_render_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile_path = root / "profile.json"
            self.assertEqual(main(["profile", "--idea", "Learn LangChain RAG", "--stack", "Python", "--constraint", "CPU only", "--constraint", "MIT license", "--out", str(profile_path)]), 0)
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertEqual(profile["constraints"], ["CPU only", "MIT license"])
            envelope = {"schema_version": 1, "profile": profile, "candidates": [{"id": "github:a/a", "name": "a/a", "provider": "github", "url": "https://github.com/a/a", "description": "Python LangChain RAG", "stars": 200}]}
            (root / "input.json").write_text(json.dumps(envelope), encoding="utf-8")
            with patch("scout.cli.get_provider", side_effect=AssertionError("Offline operation used network")):
                self.assertEqual(main(["score", "--input", str(root / "input.json"), "--out", str(root / "report.json")]), 0)
                self.assertEqual(main(["render", "--input", str(root / "report.json"), "--out", str(root / "report.html")]), 0)
            self.assertIn("LangChain", (root / "report.html").read_text(encoding="utf-8"))
            self.assertEqual(json.loads((root / "report.json").read_text(encoding="utf-8"))["profile"]["constraints"], ["CPU only", "MIT license"])

    def test_run_retains_constraints_without_making_them_search_terms(self):
        with tempfile.TemporaryDirectory() as temp:
            calls = []
            with patch("scout.cli.get_provider", side_effect=lambda source: MultiProvider(source, calls)):
                result = main(["run", "--idea", "学习Java的毕设设计项目", "--constraint", "No paid API", "--constraint", "CPU only", "--limit", "1", "--out-dir", temp])
            self.assertEqual(result, 0)
            root = Path(temp)
            profile = json.loads((root / "profile.json").read_text(encoding="utf-8"))
            report = json.loads((root / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(profile["constraints"], ["No paid API", "CPU only"])
            self.assertEqual(report["profile"]["constraints"], profile["constraints"])
            searches = [call[2] for call in calls if call[0] == "search"]
            self.assertTrue(searches)
            self.assertTrue(all("Java" in query and ("graduation-project" in query or "毕业设计" in query) for query in searches))
            self.assertFalse(any("paid" in query or "CPU" in query for query in searches))


if __name__ == "__main__":
    unittest.main()
