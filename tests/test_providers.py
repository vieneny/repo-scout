import base64
import io
import json
import os
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/repo-scout/scripts"))
from scout.providers import GitHubProvider, GitLabProvider, GiteeProvider, HTTPClient, ProviderError, _SameOriginRedirect, get_provider, parse_identifier


def metadata(**overrides):
    return {"full_name": "owner/project", "private": False, "description": "Project", "stargazers_count": 120, "forks_count": 9, "language": "Python", "default_branch": "main", "created_at": "2020-01-01T00:00:00Z", "updated_at": "2026-11-11T00:00:00Z", "pushed_at": "2026-10-01T00:00:00Z", "license": {"spdx_id": "MIT"}, **overrides}


class FakeClient:
    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    def get(self, path, params=None, raw=False):
        self.calls.append((path, params, raw))
        value = self.replies.get(path, ProviderError("HTTP 404 from fixture API"))
        if isinstance(value, Exception):
            raise value
        return value


class ProviderTests(unittest.TestCase):
    def test_github_inspection_separates_dates_and_static_signals(self):
        readme = "# Project\nMaintainer claims, not a runtime test"
        package = '[project]\ndependencies=["langchain", "fastapi"]'
        client = FakeClient({
            "/repos/owner/project": metadata(),
            "/repos/owner/project/git/trees/main": {"tree": [{"path": p, "type": "blob"} for p in ("pyproject.toml", "tests/test_flow.py", ".github/workflows/test.yml", "docs/setup.md", "README.md")], "truncated": False},
            "/repos/owner/project/readme": {"encoding": "base64", "content": base64.b64encode(readme.encode()).decode(), "html_url": "https://github.com/owner/project/blob/main/README.md"},
            "/repos/owner/project/contents/pyproject.toml": {"encoding": "base64", "content": base64.b64encode(package.encode()).decode()},
            "/repos/owner/project/commits": [{"commit": {"committer": {"date": "2026-10-01T00:00:00Z"}}, "html_url": "https://github.com/owner/project/commit/abc"}],
            "/repos/owner/project/releases": [{"published_at": "2026-09-01T00:00:00Z", "draft": False, "html_url": "https://github.com/owner/project/releases/tag/v1"}],
        })
        item = GitHubProvider(client).inspect({"name": "owner/project", "url": "https://evil.invalid", "discovery": {"kind": "seed", "query": None}})
        self.assertEqual(item["url"], "https://github.com/owner/project")
        self.assertEqual(item["last_commit_at"], "2026-10-01T00:00:00Z")
        self.assertEqual(item["latest_release_at"], "2026-09-01T00:00:00Z")
        self.assertNotEqual(item["last_commit_at"], item["updated_at"])
        self.assertEqual(item["signals"], {"tests": True, "ci": True, "docs": True, "examples": False, "deployment": False, "manifest": True})
        self.assertIn("LangChain", item["stack"])
        self.assertEqual(item["inspection_errors"], [])
        self.assertEqual(item["discovery"], {"kind": "seed", "query": None})
        self.assertEqual(item["inspection"]["inspected_manifests"], ["pyproject.toml"])

    def test_truncated_tree_missing_signals_are_unknown(self):
        client = FakeClient({"/repos/owner/project": metadata(), "/repos/owner/project/git/trees/main": {"tree": [{"path": "README.md", "type": "blob"}], "truncated": True}})
        item = GitHubProvider(client).inspect({"name": "owner/project"})
        self.assertIsNone(item["signals"]["tests"])
        self.assertTrue(item["signals"]["docs"])
        self.assertTrue(item["inspection_errors"])

    def test_error_response_is_not_an_empty_success(self):
        client = FakeClient({"/search/repositories": ProviderError("HTTP 403 from fixture API")})
        with self.assertRaises(ProviderError):
            GitHubProvider(client).search("langchain")
        with self.assertRaises(ProviderError):
            GiteeProvider(FakeClient({"/search/repositories": {"message": "denied"}})).search("langchain")

    def test_private_remote_repositories_are_excluded(self):
        with self.assertRaises(ProviderError):
            GitHubProvider(FakeClient({"/repos/owner/project": metadata(private=True)})).resolve("owner/project")
        with self.assertRaises(ProviderError):
            GitLabProvider(FakeClient({"/projects/group%2Frepo": {"path_with_namespace": "group/repo", "visibility": "private"}})).resolve("group/repo")

    def test_gitlab_search_uses_provider_specific_fields(self):
        client = FakeClient({"/projects": [{"path_with_namespace": "group/sub/repo", "star_count": 40, "forks_count": 2, "visibility": "public", "last_activity_at": "2026-11-01T00:00:00Z"}]})
        item = GitLabProvider(client).search("agent", limit=3)[0]
        self.assertEqual(item["id"], "gitlab:group/sub/repo")
        self.assertEqual(item["stars"], 40)
        self.assertIsNone(item["pushed_at"])
        self.assertEqual(client.calls[0][1]["visibility"], "public")

    def test_tokens_are_scoped_to_exact_provider(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "github-value", "GITEE_TOKEN": "gitee-value", "GITLAB_TOKEN": "gitlab-value"}, clear=True):
            self.assertEqual(get_provider("github").client.headers["Authorization"], "Bearer github-value")
            self.assertEqual(get_provider("gitee").client.headers["Authorization"], "token gitee-value")
            self.assertEqual(get_provider("gitlab").client.headers["PRIVATE-TOKEN"], "gitlab-value")
            self.assertNotIn("PRIVATE-TOKEN", get_provider("github").client.headers)

    def test_urls_and_cross_origin_redirects_rejected(self):
        self.assertEqual(parse_identifier("https://gitlab.com/group/sub/repo.git", "gitlab"), "group/sub/repo")
        for value in ("http://github.com/owner/repo", "https://github.com.evil.test/owner/repo", "https://user:secret@github.com/owner/repo", "../repo"):
            with self.assertRaises(ProviderError):
                parse_identifier(value, "github")
        with self.assertRaises(ProviderError):
            _SameOriginRedirect().redirect_request(urllib.request.Request("https://api.github.com/repos/o/r"), None, 302, "Found", {}, "https://evil.test/collect")

    def test_http_errors_do_not_expose_token_or_query(self):
        client = HTTPClient("https://api.github.com", {"Authorization": "Bearer do-not-show"})
        with patch.object(client.opener, "open", side_effect=urllib.error.HTTPError("https://api.github.com?q=private-value", 403, "do-not-show", {}, None)):
            with self.assertRaises(ProviderError) as caught:
                client.get("/search/repositories", {"q": "private-value"})
        self.assertNotIn("do-not-show", str(caught.exception))
        self.assertNotIn("private-value", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
