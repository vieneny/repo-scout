"""Security and portability guarantees of the offline HTML renderer."""
import json
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/repo-scout/scripts"))
from scout.render import render_report


class DocumentParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.external_resources = []
        self.scripts = []
        self.current = None
        self.title = ""
        self.in_title = False
        self.fields = {}
        self.current_field = None
        self.field_tag = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id") in ("snapshotDate", "retrievedDate", "generatedDate", "inspectedDate"):
            self.current_field = attrs["id"]
            self.field_tag = tag
            self.fields[self.current_field] = ""
        if tag == "script":
            self.current = {"attrs": attrs, "data": ""}
            self.scripts.append(self.current)
        if tag == "title":
            self.in_title = True
        if tag in ("script", "img", "iframe", "link") and (attrs.get("src") or attrs.get("href")):
            self.external_resources.append(attrs)

    def handle_endtag(self, tag):
        if tag == self.field_tag:
            self.current_field = None
            self.field_tag = None
        if tag == "script":
            self.current = None
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.current is not None:
            self.current["data"] += data
        if self.in_title:
            self.title += data
        if self.current_field:
            self.fields[self.current_field] += data


class RenderTests(unittest.TestCase):
    def report(self):
        return {"schema_version": 1, "title": "LangChain 学习", "profile": {"goal": "Learn RAG", "stack": ["Python"]}, "weights": {}, "source_receipts": [], "items": []}

    def render(self, report):
        with tempfile.TemporaryDirectory() as tmp:
            path = render_report(report, Path(tmp) / "nested/report.html")
            return path.read_text(encoding="utf-8")

    def test_untrusted_text_cannot_close_data_script_or_title(self):
        report = self.report()
        payload = '</script><script src="https://evil.invalid/x.js">attack</script>\u2028&<title>'
        report["title"] = '<img src=x onerror="attack()">'
        report["items"] = [{"name": payload, "description": payload, "url": "javascript:attack()"}]
        document = self.render(report)
        parser = DocumentParser()
        parser.feed(document)
        self.assertEqual(len(parser.scripts), 2)
        self.assertFalse(parser.external_resources)
        embedded = next(script["data"] for script in parser.scripts if script["attrs"].get("id") == "report-data")
        self.assertEqual(json.loads(embedded)["items"][0]["description"], payload)
        self.assertIn('<img src=x onerror="attack()">', parser.title)
        self.assertNotIn("<img src=x", document.split("</title>", 1)[0])

    def test_report_is_self_contained_and_never_renders_remote_markdown(self):
        report = self.report()
        report["items"] = [{"name": "test/repo", "readme_excerpt": '![remote](https://evil.invalid/beacon.png)', "url": "https://github.com/test/repo"}]
        document = self.render(report)
        parser = DocumentParser()
        parser.feed(document)
        self.assertEqual(parser.external_resources, [])
        self.assertIn("connect-src 'none'", document)
        self.assertNotIn("__REPORT_", document)
        self.assertIn("safeUrl", document)
        self.assertNotIn(".innerHTML", document)
        self.assertIn("textContent", document)

    def test_rejects_nonfinite_json_and_unsupported_contract(self):
        report = self.report()
        report["items"] = [{"stars": float("nan")}]
        with self.assertRaises(ValueError):
            self.render(report)
        report["schema_version"] = 999
        with self.assertRaisesRegex(ValueError, "schema_version"):
            self.render(report)
        with self.assertRaisesRegex(ValueError, "items"):
            self.render({"schema_version": 1, "items": "wrong"})

    def test_preserves_unicode_snapshot_and_source_failures(self):
        report = self.report()
        report["source_receipts"] = [{"provider": "gitee", "query": "智能体", "status": "error", "error": "HTTP 403"}]
        report["generated_at"] = "2026-11-11T05:00:00+00:00"
        document = self.render(report)
        parser = DocumentParser(); parser.feed(document)
        stored = json.loads(next(s["data"] for s in parser.scripts if s["attrs"].get("id") == "report-data"))
        self.assertEqual(stored, report)

    def test_source_placeholder_text_is_not_recursively_substituted(self):
        report = self.report()
        report["title"] = "__REPORT_SCRIPT__"
        report["items"] = [{"name": "__REPORT_STYLE__", "description": "__REPORT_SCRIPT__ __REPORT_DATA__ __REPORT_TITLE__"}]
        document = self.render(report)
        parser = DocumentParser(); parser.feed(document)
        stored = json.loads(next(s["data"] for s in parser.scripts if s["attrs"].get("id") == "report-data"))
        self.assertEqual(stored, report)
        self.assertEqual(len(parser.scripts), 2)

    def test_data_snapshot_inspection_and_generation_are_independent(self):
        report = self.report()
        report.update(retrieved_at="2026-11-08T23:10:00-03:00", inspected_at="2026-11-09T03:15:00Z", generated_at="2026-11-11T05:00:00+00:00")
        parser = DocumentParser(); parser.feed(self.render(report))
        self.assertEqual(parser.fields["snapshotDate"], "数据快照 2026-11-09 02:10 UTC")
        self.assertEqual(parser.fields["retrievedDate"], "2026-11-09 02:10 UTC")
        self.assertEqual(parser.fields["inspectedDate"], "2026-11-09 03:15 UTC")
        self.assertEqual(parser.fields["generatedDate"], "2026-11-11 05:00 UTC")

    def test_legacy_report_does_not_substitute_generation_for_snapshot(self):
        report = self.report()
        report["generated_at"] = "2026-11-11T05:00:00Z"
        parser = DocumentParser(); parser.feed(self.render(report))
        self.assertEqual(parser.fields["snapshotDate"], "数据快照 未知")
        self.assertEqual(parser.fields["retrievedDate"], "未知")
        self.assertEqual(parser.fields["inspectedDate"], "未知")
        self.assertEqual(parser.fields["generatedDate"], "2026-11-11 05:00 UTC")

    def test_discovery_records_remain_inert_and_distinct(self):
        report = self.report()
        report["items"] = [
            {"name": "provided/repo", "discovery": [{"type": "supplied", "query": None}]},
            {"name": "searched/repo", "discovery": [{"type": "search", "query": '<script>alert("query")</script>'}]},
        ]
        parser = DocumentParser(); parser.feed(self.render(report))
        data = json.loads(next(s["data"] for s in parser.scripts if s["attrs"].get("id") == "report-data"))
        self.assertEqual(data["items"], report["items"])
        self.assertEqual(len(parser.scripts), 2)
        self.assertFalse(parser.external_resources)

    def test_creative_usage_constraints_remain_inert_and_optional(self):
        payload = '</script><img src="https://evil.invalid/pixel" onerror="attack()">'
        report = self.report()
        legacy_parser = DocumentParser(); legacy_parser.feed(self.render(report))
        legacy_data = json.loads(next(s["data"] for s in legacy_parser.scripts if s["attrs"].get("id") == "report-data"))
        self.assertNotIn("constraints", legacy_data["profile"])
        report["profile"]["constraints"] = ["Windows；仅 CPU", payload]
        report["items"] = [{"name": "creative/workflow", "category": "workflow", "usage_requirements": ["需要独立模型权重；商用条件待核查", payload], "usage_evidence": ["https://example.com/model-card", "javascript:attack()"]}]
        parser = DocumentParser(); parser.feed(self.render(report))
        data = json.loads(next(s["data"] for s in parser.scripts if s["attrs"].get("id") == "report-data"))
        self.assertEqual(data, report)
        self.assertEqual(len(parser.scripts), 2)
        self.assertFalse(parser.external_resources)


if __name__ == "__main__":
    unittest.main()
