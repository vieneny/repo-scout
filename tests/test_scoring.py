import copy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "skills/repo-scout/scripts"))
from scout.scoring import build_report, normalized_weights, validate_assessments


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.envelope = {"schema_version": 1, "profile": {"title": "Learn RAG", "goal": "rag", "stack": ["Python"]}, "candidates": [{"id": "github:a/a", "name": "a/a", "url": "https://github.com/a/a", "provider": "github", "stars": None, "license": None}]}

    def test_unknown_criteria_widen_interval_without_becoming_zero_judgments(self):
        report = build_report(self.envelope)
        item = report["items"][0]
        self.assertIsNone(item["criteria"]["maintenance"]["value"])
        self.assertEqual(item["criteria"]["maintenance"]["status"], "unknown")
        self.assertGreater(item["score_upper"], item["score"])
        self.assertLess(item["coverage"], 1)
        self.assertEqual(item["review_coverage"], 0)

    def test_reviewed_score_needs_evidence_and_reason(self):
        review = {"schema_version": 1, "assessments": [{"id": "github:a/a", "criteria": {"relevance": {"value": 5, "status": "source-reviewed", "reason": "Matches", "evidence": []}}}]}
        with self.assertRaises(ValueError):
            build_report(self.envelope, review)
        review["assessments"][0]["criteria"]["relevance"]["evidence"] = ["https://github.com/a/a/blob/main/README.md"]
        report = build_report(self.envelope, review)
        self.assertEqual(report["items"][0]["review_coverage"], .25)

    def test_collected_stack_preserved_when_review_omits_stack(self):
        self.envelope["candidates"][0]["stack"] = ["Python"]
        review = {"schema_version": 1, "assessments": [{"id": "github:a/a", "summary": "Reviewed description"}]}
        report = build_report(self.envelope, review)
        self.assertEqual(report["items"][0]["stack"], ["Python"])
        report["items"][0]["stack"].append("LangChain")
        self.assertEqual(self.envelope["candidates"][0]["stack"], ["Python"])

    def test_source_review_can_correct_incomplete_stack_without_mutating_inputs(self):
        self.envelope["candidates"][0]["stack"] = ["Python"]
        reviewed_stack = ["Python", "LangChain", "LangGraph", "FAISS", "Chroma"]
        review = {"schema_version": 1, "assessments": [{"id": "github:a/a", "stack": reviewed_stack, "criteria": {"stack_fit": {"value": 5, "status": "source-reviewed", "reason": "Imports and dependency manifest confirm the runtime stack.", "evidence": ["https://github.com/a/a/blob/main/requirements.txt"]}}}]}
        original_envelope, original_review = copy.deepcopy(self.envelope), copy.deepcopy(review)
        item = build_report(self.envelope, review)["items"][0]
        self.assertEqual(item["stack"], reviewed_stack)
        self.assertEqual(item["criteria"]["stack_fit"]["status"], "source-reviewed")
        self.assertEqual(item["criteria"]["stack_fit"]["value"], 5)
        item["stack"].append("FastAPI")
        self.assertEqual(self.envelope, original_envelope)
        self.assertEqual(review, original_review)

    def test_stack_override_rejects_missing_or_invalid_technology_names(self):
        for stack in [None, "Python", [], [1], [""], ["  "], ["Python", None]]:
            with self.subTest(stack=stack):
                row = {"id": "github:a/a", "stack": stack, "criteria": {"stack_fit": {"value": 5, "status": "source-reviewed", "reason": "Inspected dependencies", "evidence": ["https://github.com/a/a/blob/main/requirements.txt"]}}}
                with self.assertRaises(ValueError):
                    validate_assessments({"schema_version": 1, "assessments": [row]}, {"github:a/a"})

    def test_stack_override_requires_reviewed_fit_and_public_evidence(self):
        judgments = [
            None,
            {"value": 5, "status": "heuristic", "reason": "Keyword match", "evidence": ["https://github.com/a/a"]},
            {"value": None, "status": "unknown", "reason": "Not checked", "evidence": []},
            {"value": 5, "status": "source-reviewed", "reason": "Inspected dependencies", "evidence": []},
            {"value": 5, "status": "source-reviewed", "reason": "Inspected dependencies", "evidence": ["https://user:secret@example.com/requirements.txt"]},
        ]
        for judgment in judgments:
            with self.subTest(judgment=judgment):
                row = {"id": "github:a/a", "stack": ["Python", "LangChain"], "criteria": {} if judgment is None else {"stack_fit": judgment}}
                with self.assertRaises(ValueError):
                    validate_assessments({"schema_version": 1, "assessments": [row]}, {"github:a/a"})

    def test_reweighting_can_change_ranking(self):
        envelope = copy.deepcopy(self.envelope)
        envelope["candidates"].append(dict(envelope["candidates"][0], id="github:b/b", name="b/b"))
        reviews = {"schema_version": 1, "assessments": []}
        for name, relevance, reuse in [("a", 5, 1), ("b", 1, 5)]:
            reviews["assessments"].append({"id": f"github:{name}/{name}", "criteria": {key: {"value": value, "status": "source-reviewed", "reason": "Source checked", "evidence": [f"https://github.com/{name}/{name}"]} for key, value in [("relevance", relevance), ("reuse", reuse)]}})
        self.assertEqual(build_report(envelope, reviews)["items"][0]["name"], "a/a")
        weights = {key: 0 for key in normalized_weights()}; weights["reuse"] = 1
        self.assertEqual(build_report(envelope, reviews, {"weights": weights})["items"][0]["name"], "b/b")

    def test_nonfinite_negative_and_all_zero_weights_rejected(self):
        for weights in [{"relevance": float("nan")}, {"reuse": -1}, {key: 0 for key in normalized_weights()}, {"typo": 1}]:
            with self.assertRaises(ValueError):
                normalized_weights(weights)

    def test_future_commit_does_not_create_score_above_maximum(self):
        self.envelope["candidates"][0]["last_commit_at"] = "2099-01-01T00:00:00Z"
        result = build_report(self.envelope, now=datetime(2026, 11, 11, tzinfo=timezone.utc))["items"][0]
        self.assertEqual(result["criteria"]["maintenance"]["value"], 5)

    def test_rescoring_preserves_collection_date_separate_from_generation(self):
        self.envelope["retrieved_at"] = "2020-01-01T00:00:00Z"
        self.envelope["inspected_at"] = "2020-01-02T00:00:00Z"
        report = build_report(self.envelope, now=datetime(2026, 11, 11, tzinfo=timezone.utc))
        self.assertEqual(report["retrieved_at"], "2020-01-01T00:00:00Z")
        self.assertEqual(report["inspected_at"], "2020-01-02T00:00:00Z")
        self.assertTrue(report["generated_at"].startswith("2026-11-11"))

    def test_duplicate_unknown_candidate_and_credential_url_rejected(self):
        for row in [{"id": "github:not/inspected", "criteria": {}}, {"id": "github:a/a", "criteria": {"reuse": {"value": 4, "status": "source-reviewed", "reason": "test", "evidence": ["https://user:secret@example.com"]}}}]:
            with self.assertRaises(ValueError):
                validate_assessments({"schema_version": 1, "assessments": [row]}, {"github:a/a"})


if __name__ == "__main__":
    unittest.main()
