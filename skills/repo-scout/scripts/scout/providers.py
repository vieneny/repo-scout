"""Public repository adapters. Network failures remain explicit evidence gaps."""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .profile import MANIFESTS, detect_stack


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class ProviderError(RuntimeError):
    """A safe diagnostic without request credentials or response body content."""


class _SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        before, after = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        if after.scheme != "https" or before.netloc != after.netloc:
            raise ProviderError("Cross-origin API redirect refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HTTPClient:
    def __init__(self, base, headers=None, timeout=20, max_bytes=4_000_000):
        self.base = base.rstrip("/")
        self.headers = {"User-Agent": "Repo-Scout/0.1 (public-read-only)", "Accept": "application/json", **(headers or {})}
        self.timeout, self.max_bytes = timeout, max_bytes
        self.opener = urllib.request.build_opener(_SameOriginRedirect())

    def get(self, path, params=None, raw=False):
        if not path.startswith("/") or path.startswith("//") or "://" in path:
            raise ProviderError("API path must be relative to its configured provider")
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers=self.headers)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                body = response.read(self.max_bytes + 1)
                if len(body) > self.max_bytes:
                    raise ProviderError("API response exceeded the bounded inspection limit")
        except urllib.error.HTTPError as exc:
            raise ProviderError(f"HTTP {exc.code} from {urllib.parse.urlsplit(self.base).netloc} API") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderError(f"Network unavailable for {urllib.parse.urlsplit(self.base).netloc} API ({type(exc).__name__})") from None
        text = body.decode("utf-8", errors="replace")
        if raw:
            return text
        try:
            return json.loads(text)
        except ValueError:
            raise ProviderError("Provider returned an invalid JSON response") from None


def _number(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _license(value):
    if isinstance(value, dict):
        return value.get("spdx_id") or value.get("key") or value.get("name")
    return value if isinstance(value, str) else None


def _redact(text):
    text = re.sub(r"(?i)(https?://)[^\s/@]+:[^\s/@]+@", r"\1[redacted]@", text)
    text = re.sub(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16})\b", "[redacted credential]", text)
    return text[:12000]


def parse_identifier(identifier, provider):
    hosts = {"github": "github.com", "gitee": "gitee.com", "gitlab": "gitlab.com"}
    value = str(identifier).strip()
    if "://" in value:
        parts = urllib.parse.urlsplit(value)
        if parts.scheme != "https" or parts.hostname != hosts[provider] or parts.username or parts.password or parts.port not in (None, 443):
            raise ProviderError(f"Expected a public https://{hosts[provider]} repository URL")
        value = parts.path.strip("/")
    value = value.removesuffix(".git")
    segments = value.split("/")
    if len(segments) < 2 or (provider != "gitlab" and len(segments) != 2) or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) or part in {".", ".."} for part in segments):
        raise ProviderError("Expected owner/repository (GitLab subgroups are supported)")
    return value


def _signals(paths, complete):
    lower = [p.lower() for p in paths]
    checks = {
        "tests": any(re.search(r"(^|/)(tests?|__tests__)(/|\.)|(^|/)(test_[^/]+|[^/]+\.(test|spec)\.[^/]+)$", p) for p in lower),
        "ci": any(p.startswith(".github/workflows/") or p in {".gitlab-ci.yml", ".travis.yml", "jenkinsfile", "azure-pipelines.yml"} for p in lower),
        "docs": any(p.startswith(("docs/", "doc/")) or p.startswith("readme") for p in lower),
        "examples": any(re.search(r"(^|/)(examples?|tutorials?|cookbooks?|notebooks?)(/|$)", p) for p in lower),
        "deployment": any(p.rsplit("/", 1)[-1] in {"dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "helmfile.yaml", "vercel.json", "netlify.toml"} or p.startswith(("deploy/", "deployment/", "helm/")) for p in lower),
        "manifest": any(p.rsplit("/", 1)[-1] in MANIFESTS for p in paths),
    }
    return {key: present if present or complete else None for key, present in checks.items()}


class GitHubProvider:
    name = "github"
    web = "https://github.com"
    api = "https://api.github.com"

    def __init__(self, client=None):
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        self.client = client or HTTPClient(self.api, {"Authorization": "Bearer " + token} if token else {})

    def _normalize(self, item):
        if item.get("private") is True or item.get("visibility") in {"private", "internal"}:
            raise ProviderError("Private repositories are excluded from automatic public reports; use an abstract local profile")
        name = item.get("full_name")
        if not isinstance(name, str):
            raise ProviderError("Provider metadata has no repository name")
        return {"id": f"{self.name}:{name}", "provider": self.name, "name": name,
                "url": self.web + "/" + name, "description": item.get("description") or "",
                "stars": _number(item.get("stargazers_count")), "forks": _number(item.get("forks_count")),
                "language": item.get("language"), "topics": item.get("topics") or [],
                "created_at": item.get("created_at"), "updated_at": item.get("updated_at"),
                "pushed_at": item.get("pushed_at"), "archived": item.get("archived"),
                "license": _license(item.get("license")), "default_branch": item.get("default_branch") or "HEAD", "retrieved_at": now()}

    def resolve(self, identifier):
        name = parse_identifier(identifier, self.name)
        response = self.client.get("/repos/" + name)
        if not isinstance(response, dict):
            raise ProviderError("Provider returned invalid repository metadata")
        return self._normalize(response)

    def search(self, query, limit=10):
        limit = max(1, min(int(limit), 100))
        response = self.client.get("/search/repositories", {"q": query, "sort": "stars", "order": "desc", "per_page": limit})
        if not isinstance(response, dict) or not isinstance(response.get("items"), list):
            raise ProviderError("Provider returned invalid search results")
        return [self._normalize(item) for item in response["items"][:limit] if not item.get("private")]

    def _read_file(self, name, path, branch):
        response = self.client.get("/repos/" + name + "/contents/" + urllib.parse.quote(path, safe="/"), {"ref": branch})
        if not isinstance(response, dict) or response.get("encoding") != "base64" or not isinstance(response.get("content"), str):
            raise ProviderError("File content encoding is unsupported")
        try:
            body = base64.b64decode(response["content"], validate=False)
        except (ValueError, TypeError):
            raise ProviderError("File content is not valid base64") from None
        if len(body) > 65536:
            raise ProviderError("Manifest exceeded the bounded file limit")
        return body.decode("utf-8", errors="replace")

    def inspect(self, candidate):
        # Refresh metadata rather than trusting search snippets or supplied URL fields.
        item = self.resolve(candidate["name"])
        if "discovery" in candidate:
            item["discovery"] = candidate["discovery"]
        name, branch = item["name"], item["default_branch"]
        errors, evidence, paths = [], [{"url": item["url"], "kind": "metadata", "note": "Current provider metadata; no candidate code was run."}], []
        complete = False
        try:
            tree = self.client.get("/repos/" + name + "/git/trees/" + urllib.parse.quote(branch, safe=""), {"recursive": "1"})
            if not isinstance(tree, dict) or not isinstance(tree.get("tree"), list):
                raise ProviderError("Provider returned an invalid repository tree")
            paths = [entry["path"] for entry in tree["tree"] if entry.get("type") == "blob" and isinstance(entry.get("path"), str)]
            complete = not tree.get("truncated", False)
            if not complete:
                errors.append("tree: provider truncated the file tree; missing structures remain unknown")
            evidence.append({"url": item["url"] + "/tree/" + urllib.parse.quote(branch, safe=""), "kind": "structure", "note": "File-presence signals only; tests and deployment were not executed."})
        except ProviderError as exc:
            errors.append("tree: " + str(exc))
        readme = ""
        try:
            response = self.client.get("/repos/" + name + "/readme", {"ref": branch})
            if isinstance(response, dict) and response.get("encoding") == "base64":
                readme = base64.b64decode(response.get("content", "")).decode("utf-8", errors="replace")
                evidence.append({"url": response.get("html_url") or item["url"] + "#readme", "kind": "readme", "note": "Maintainer description; not independent runtime validation."})
            else:
                raise ProviderError("README encoding is unsupported")
        except (ProviderError, ValueError) as exc:
            errors.append("readme: " + str(exc))
        manifests = {}
        manifest_paths = sorted((p for p in paths if p.rsplit("/", 1)[-1] in MANIFESTS), key=lambda p: (p.count("/"), p))[:5]
        for path in manifest_paths:
            try:
                manifests[path] = self._read_file(name, path, branch)
                evidence.append({"url": item["url"] + "/blob/" + urllib.parse.quote(branch, safe="") + "/" + urllib.parse.quote(path), "kind": "manifest", "note": "Declared dependencies, not proof of exercised integrations."})
            except ProviderError as exc:
                errors.append("manifest " + path + ": " + str(exc))
        last_commit = latest_release = latest_commit_sha = None
        try:
            commits = self.client.get("/repos/" + name + "/commits", {"sha": branch, "per_page": 1})
            if isinstance(commits, list) and commits:
                last_commit = commits[0].get("commit", {}).get("committer", {}).get("date")
                latest_commit_sha = commits[0].get("sha")
                evidence.append({"url": commits[0].get("html_url") or item["url"] + "/commits", "kind": "commit", "note": "Latest default-branch commit; may be automated."})
        except ProviderError as exc:
            errors.append("commit: " + str(exc))
        try:
            releases = self.client.get("/repos/" + name + "/releases", {"per_page": 5})
            if not isinstance(releases, list):
                raise ProviderError("Provider returned invalid releases")
            published = [r for r in releases if not r.get("draft") and r.get("published_at")]
            if published:
                release = max(published, key=lambda r: r["published_at"])
                latest_release = release["published_at"]
                evidence.append({"url": release.get("html_url") or item["url"] + "/releases", "kind": "release", "note": "Latest observed published release; creation and push dates are separate."})
        except ProviderError as exc:
            errors.append("release: " + str(exc))
        item.update(last_commit_at=last_commit, latest_release_at=latest_release, readme_excerpt=_redact(readme), stack=detect_stack(manifests), signals=_signals(paths, complete), evidence=evidence, inspection_errors=errors,
                    inspection={"tree_complete": complete, "file_count": len(paths) if complete else None, "inspected_manifests": list(manifests), "latest_commit_sha": latest_commit_sha})
        return item


class GiteeProvider(GitHubProvider):
    name = "gitee"
    web = "https://gitee.com"
    api = "https://gitee.com/api/v5"

    def __init__(self, client=None):
        token = os.environ.get("GITEE_TOKEN")
        self.client = client or HTTPClient(self.api, {"Authorization": "token " + token} if token else {})

    def search(self, query, limit=10):
        limit = max(1, min(int(limit), 100))
        response = self.client.get("/search/repositories", {"q": query, "sort": "stars_count", "order": "desc", "per_page": limit})
        if not isinstance(response, list):
            raise ProviderError("Gitee returned invalid search results")
        return [self._normalize(item) for item in response[:limit] if not item.get("private")]


class GitLabProvider:
    name = "gitlab"
    web = "https://gitlab.com"
    api = "https://gitlab.com/api/v4"

    def __init__(self, client=None):
        token = os.environ.get("GITLAB_TOKEN")
        self.client = client or HTTPClient(self.api, {"PRIVATE-TOKEN": token} if token else {})

    def _normalize(self, item):
        if item.get("visibility") in {"private", "internal"}:
            raise ProviderError("Private repositories are excluded from automatic public reports; use an abstract local profile")
        name = item.get("path_with_namespace")
        if not isinstance(name, str):
            raise ProviderError("GitLab metadata has no repository name")
        return {"id": "gitlab:" + name, "provider": self.name, "name": name, "url": self.web + "/" + name,
                "description": item.get("description") or "", "stars": _number(item.get("star_count")), "forks": _number(item.get("forks_count")),
                "language": None, "topics": item.get("topics") or item.get("tag_list") or [], "created_at": item.get("created_at"),
                "updated_at": item.get("last_activity_at"), "pushed_at": None, "archived": item.get("archived"),
                "license": _license(item.get("license")), "default_branch": item.get("default_branch") or "HEAD", "retrieved_at": now()}

    def resolve(self, identifier):
        name = parse_identifier(identifier, self.name)
        response = self.client.get("/projects/" + urllib.parse.quote(name, safe=""), {"license": "true"})
        if not isinstance(response, dict):
            raise ProviderError("GitLab returned invalid project metadata")
        return self._normalize(response)

    def search(self, query, limit=10):
        limit = max(1, min(int(limit), 100))
        response = self.client.get("/projects", {"search": query, "visibility": "public", "order_by": "star_count", "sort": "desc", "per_page": limit, "simple": "true"})
        if not isinstance(response, list):
            raise ProviderError("GitLab returned invalid search results")
        return [self._normalize(item) for item in response[:limit]]

    def _read_file(self, project, path, branch):
        return self.client.get(project + "/repository/files/" + urllib.parse.quote(path, safe="") + "/raw", {"ref": branch}, raw=True)

    def inspect(self, candidate):
        item = self.resolve(candidate["name"])
        if "discovery" in candidate:
            item["discovery"] = candidate["discovery"]
        name, branch = item["name"], item["default_branch"]
        project = "/projects/" + urllib.parse.quote(name, safe="")
        evidence = [{"url": item["url"], "kind": "metadata", "note": "Current public project metadata; no code was executed."}]
        errors, paths, complete = [], [], False
        try:
            tree = self.client.get(project + "/repository/tree", {"recursive": "true", "per_page": 100, "ref": branch})
            if not isinstance(tree, list):
                raise ProviderError("GitLab returned an invalid repository tree")
            paths = [entry["path"] for entry in tree if entry.get("type") == "blob" and isinstance(entry.get("path"), str)]
            complete = len(tree) < 100
            if not complete:
                errors.append("tree: inspection uses the first 100 paths; missing structures remain unknown")
            evidence.append({"url": item["url"] + "/-/tree/" + urllib.parse.quote(branch, safe=""), "kind": "structure", "note": "Bounded file inventory; no tests were executed."})
        except ProviderError as exc:
            errors.append("tree: " + str(exc))
        readme = ""
        readme_path = next((p for p in paths if p.lower() in {"readme.md", "readme.rst", "readme"}), "README.md")
        try:
            readme = self._read_file(project, readme_path, branch)
            evidence.append({"url": item["url"] + "/-/blob/" + urllib.parse.quote(branch, safe="") + "/" + urllib.parse.quote(readme_path), "kind": "readme", "note": "Maintainer description; untested."})
        except ProviderError as exc:
            errors.append("readme: " + str(exc))
        manifests = {}
        for path in sorted((p for p in paths if p.rsplit("/", 1)[-1] in MANIFESTS), key=lambda p: (p.count("/"), p))[:5]:
            try:
                manifests[path] = self._read_file(project, path, branch)[:65536]
                evidence.append({"url": item["url"] + "/-/blob/" + urllib.parse.quote(branch, safe="") + "/" + urllib.parse.quote(path), "kind": "manifest", "note": "Declared dependencies only."})
            except ProviderError as exc:
                errors.append("manifest " + path + ": " + str(exc))
        last_commit = latest_release = latest_commit_sha = None
        try:
            commits = self.client.get(project + "/repository/commits", {"ref_name": branch, "per_page": 1})
            if isinstance(commits, list) and commits:
                last_commit = commits[0].get("committed_date")
                latest_commit_sha = commits[0].get("id")
                evidence.append({"url": commits[0].get("web_url") or item["url"] + "/-/commits/" + urllib.parse.quote(branch, safe=""), "kind": "commit", "note": "Latest default-branch commit; may be automated."})
        except ProviderError as exc:
            errors.append("commit: " + str(exc))
        try:
            releases = self.client.get(project + "/releases", {"per_page": 5})
            if not isinstance(releases, list):
                raise ProviderError("GitLab returned invalid releases")
            published = [release for release in releases if release.get("released_at") and not release.get("upcoming_release")]
            if published:
                release = max(published, key=lambda r: r["released_at"])
                latest_release = release["released_at"]
                evidence.append({"url": release.get("_links", {}).get("self") or item["url"] + "/-/releases", "kind": "release", "note": "Latest observed release date."})
        except ProviderError as exc:
            errors.append("release: " + str(exc))
        item.update(last_commit_at=last_commit, latest_release_at=latest_release, readme_excerpt=_redact(readme), stack=detect_stack(manifests), signals=_signals(paths, complete), evidence=evidence, inspection_errors=errors,
                    inspection={"tree_complete": complete, "file_count": len(paths) if complete else None, "inspected_manifests": list(manifests), "latest_commit_sha": latest_commit_sha})
        return item


def get_provider(name, client=None):
    providers = {"github": GitHubProvider, "gitee": GiteeProvider, "gitlab": GitLabProvider}
    try:
        return providers[name.lower()](client=client)
    except (KeyError, AttributeError):
        raise ProviderError("Unsupported source; choose github, gitee, or gitlab") from None
