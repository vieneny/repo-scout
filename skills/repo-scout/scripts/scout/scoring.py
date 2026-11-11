"""Transparent bounded scoring. A missing fact is not a negative finding."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import math
import re
from urllib.parse import urlsplit

DEFAULT_WEIGHTS = {
    "relevance": 25, "stack_fit": 15, "completeness": 15,
    "maintenance": 10, "learning_fit": 15, "reuse": 15, "popularity": 5,
}
CRITERIA = tuple(DEFAULT_WEIGHTS)
STATUSES = {"source-reviewed", "heuristic", "unknown"}
PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense", "0BSD"}


def normalized_weights(weights=None):
    result = dict(DEFAULT_WEIGHTS)
    if weights is not None:
        if not isinstance(weights, dict) or set(weights) - set(CRITERIA):
            raise ValueError("weights must use the seven documented criterion names")
        result.update(weights)
    for value in result.values():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError("weights must be finite nonnegative numbers")
    total = sum(result.values())
    if total <= 0:
        raise ValueError("at least one weight must be positive")
    return {key: value * 100 / total for key, value in result.items()}


def _http_url(value):
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme in {"https", "http"} and bool(parsed.hostname) and not parsed.username and not parsed.password


def validate_assessments(assessments, candidate_ids):
    if not isinstance(assessments, dict) or assessments.get("schema_version") != 1:
        raise ValueError("assessments require schema_version 1")
    rows = assessments.get("assessments")
    if not isinstance(rows, list):
        raise ValueError("assessments must be a list")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("id") not in candidate_ids or row["id"] in seen:
            raise ValueError("assessment ID must identify one unique inspected candidate")
        seen.add(row["id"])
        criteria = row.get("criteria", {})
        if not isinstance(criteria, dict) or set(criteria) - set(CRITERIA):
            raise ValueError("assessment has an unknown criterion")
        for key, item in criteria.items():
            if not isinstance(item, dict):
                raise ValueError(f"{key}: expected an assessment object")
            value, status = item.get("value"), item.get("status")
            if status not in STATUSES:
                raise ValueError(f"{key}: invalid evidence status")
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 5):
                raise ValueError(f"{key}: value must be null or a finite number from 0 to 5")
            if (value is None) != (status == "unknown"):
                raise ValueError(f"{key}: unknown requires null, and null requires unknown status")
            evidence = item.get("evidence", [])
            if not isinstance(evidence, list) or not all(_http_url(url) for url in evidence):
                raise ValueError(f"{key}: evidence must contain public http(s) URLs without credentials")
            if not isinstance(item.get("reason"), str) or not item["reason"].strip():
                raise ValueError(f"{key}: a reason is required")
            if status == "source-reviewed" and not evidence:
                raise ValueError(f"{key}: source-reviewed judgments require evidence links")
        if "stack" in row:
            if not isinstance(row["stack"], list) or not row["stack"] or not all(isinstance(value, str) and value.strip() for value in row["stack"]):
                raise ValueError("stack must be a nonempty list of nonempty strings")
            if criteria.get("stack_fit", {}).get("status") != "source-reviewed":
                raise ValueError("stack overrides require a source-reviewed stack_fit judgment with evidence links")
        for field in ("strengths", "gaps", "learning_path"):
            if field in row and (not isinstance(row[field], list) or not all(isinstance(v, str) for v in row[field])):
                raise ValueError(f"{field} must be a list of strings")
        audience = row.get("audience")
        if audience is not None:
            if not isinstance(audience, dict) or audience.get("label") not in {"individual", "team", "enterprise-oriented", "unknown"}:
                raise ValueError("audience label must be individual, team, enterprise-oriented, or unknown")
            if not isinstance(audience.get("reason"), str) or not audience["reason"].strip():
                raise ValueError("audience requires a reason")
            if not isinstance(audience.get("evidence", []), list) or not all(_http_url(url) for url in audience.get("evidence", [])):
                raise ValueError("audience evidence must contain http(s) URLs")
    return {row["id"]: row for row in rows}


def _criterion(value, reason, evidence=(), status="heuristic"):
    return {"value": value, "reason": reason, "evidence": [url for url in evidence if _http_url(url)], "status": "unknown" if value is None else status}


def _terms(text):
    stop = {"with", "from", "this", "that", "your", "project", "application", "build", "learn", "learning", "using", "and", "for", "the"}
    return {word.casefold() for word in re.findall(r"[A-Za-z][A-Za-z0-9.+#_-]{1,}", text) if word.casefold() not in stop}


def _date(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except ValueError:
        return None


def automatic_criteria(profile, candidate, now):
    url = candidate.get("url", "")
    links = [url]
    signals = candidate.get("signals") or {}
    text = " ".join(str(candidate.get(key) or "") for key in ("name", "description", "readme_excerpt")) + " " + " ".join(candidate.get("stack") or [])
    desired = _terms(" ".join([profile.get("title", ""), profile.get("goal", ""), *profile.get("capabilities", [])]))
    matches = desired & _terms(text)
    relevance = min(4.0, len(matches) / max(1, min(6, len(desired))) * 5) if desired else None
    stack = profile.get("stack") or []
    found = [item for item in stack if item.casefold() in text.casefold() or item.casefold() == str(candidate.get("language", "")).casefold()]
    fit = len(found) / len(stack) * 5 if stack else None
    structural = [signals.get(key) for key in ("manifest", "tests", "ci", "docs", "examples", "deployment")]
    known = [value for value in structural if isinstance(value, bool)]
    complete = min(2.5, sum(value is True for value in known) / len(known) * 2.5) if known else None
    commit_key = "last_commit_at" if candidate.get("last_commit_at") else "pushed_at"
    commit = _date(candidate.get(commit_key))
    if candidate.get("archived") is True:
        maintenance, maintenance_reason = 0, "仓库已归档；这影响维护适合度，不代表代码无法学习。"
    elif commit:
        days = max(0, (now - commit).days)
        maintenance = 5 if days <= 30 else 4 if days <= 90 else 3 if days <= 180 else 2 if days <= 365 else 1 if days <= 730 else 0.5
        maintenance_reason = f"距离 {commit_key} 约 {days} 天；仅日期启发式，未判定提交是否有实质业务变化。"
    else:
        maintenance, maintenance_reason = None, "没有可靠的默认分支提交或推送时间；更新时间不是代码维护证据。"
    learn_signals = [signals.get("docs"), signals.get("examples")]
    learning = min(3, 1 + sum(value is True for value in learn_signals)) if any(isinstance(value, bool) for value in learn_signals) else None
    license_name = candidate.get("license")
    reuse = 3.5 if license_name in PERMISSIVE else 2 if license_name and license_name not in {"NOASSERTION", "Other", "unknown"} else None
    stars = candidate.get("stars")
    popularity = min(5, math.log10(stars + 1)) if isinstance(stars, int) and not isinstance(stars, bool) and stars >= 0 else None
    return {
        "relevance": _criterion(relevance, f"关键词启发式命中 {', '.join(sorted(matches)) or '无'}；业务匹配仍需源码审阅。", links),
        "stack_fit": _criterion(fit, f"目标技术栈命中 {', '.join(found) or '无'}；语言占比不等于完整技术栈。", links),
        "completeness": _criterion(complete, "仅检查文件与目录结构信号，上限 2.5/5；没有执行主流程、测试或部署。", links),
        "maintenance": _criterion(maintenance, maintenance_reason, links),
        "learning_fit": _criterion(learning, "基于文档/示例结构，上限 3/5；尚未核对个人学习所需的完整步骤。", links),
        "reuse": _criterion(reuse, f"许可证元数据：{license_name or '未知'}；组件边界与依赖成本尚未审阅。", links),
        "popularity": _criterion(popularity, "当前平台 Stars 的对数指标，100,000 Stars 达到上限；不等于用户数或代码质量。", links),
    }


def totals(criteria, weights):
    lower = upper = known = reviewed = 0.0
    for key, weight in weights.items():
        item = criteria[key]
        value = item.get("value")
        if value is None:
            upper += weight
        else:
            contribution = weight * value / 5
            lower += contribution
            upper += contribution
            known += weight
            if item.get("status") == "source-reviewed":
                reviewed += weight
    return {"score": round(lower, 2), "score_upper": round(upper, 2), "coverage": round(known / 100, 4), "review_coverage": round(reviewed / 100, 4)}


def build_report(envelope, assessments=None, config=None, now=None):
    if envelope.get("schema_version") != 1 or not isinstance(envelope.get("candidates"), list):
        raise ValueError("expected a schema_version 1 candidate envelope")
    profile = envelope.get("profile")
    if not isinstance(profile, dict) or not isinstance(profile.get("title"), str):
        raise ValueError("candidate envelope requires a profile with a title")
    candidates = envelope["candidates"]
    ids = [item.get("id") for item in candidates]
    if any(not isinstance(item, str) or not item for item in ids) or len(set(ids)) != len(ids):
        raise ValueError("candidate IDs must be nonempty and unique")
    config = config or {}
    weights = normalized_weights(config.get("weights"))
    reviews = validate_assessments(assessments, set(ids)) if assessments else {}
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    items = []
    for original in candidates:
        candidate = deepcopy(original)
        criteria = automatic_criteria(profile, candidate, now)
        assessment = reviews.get(candidate["id"], {})
        criteria.update(deepcopy(assessment.get("criteria", {})))
        for field in ("summary", "category", "stack", "audience", "strengths", "gaps", "learning_path"):
            if field in assessment:
                candidate[field] = deepcopy(assessment[field])
        candidate.setdefault("summary", candidate.get("description") or "待审阅")
        candidate.setdefault("category", "unknown")
        candidate.setdefault("audience", {"label": "unknown", "reason": "尚未核对个人/团队所需资源；不根据 Stars 推断企业成熟度。", "evidence": []})
        candidate.setdefault("strengths", [])
        candidate.setdefault("gaps", ["当前为结构与元数据初筛，尚未完成源码证据审阅。"])
        candidate.setdefault("learning_path", [])
        candidate["criteria"] = criteria
        candidate.update(totals(criteria, weights))
        items.append(candidate)
    items.sort(key=lambda item: (-item["score"], -item["coverage"], item.get("name", item["id"])))
    for rank, item in enumerate(items, 1):
        item["rank"] = rank
    return {
        "schema_version": 1, "title": profile["title"], "generated_at": now.isoformat(),
        "retrieved_at": envelope.get("retrieved_at"),
        "inspected_at": envelope.get("inspected_at"),
        "profile": deepcopy(profile), "weights": weights,
        "source_receipts": deepcopy(envelope.get("receipts", [])),
        "methodology": {
            "version": "1.0", "scale": "0..5", "ranking": "weighted lower bound, then known evidence coverage, then name",
            "unknown": "Null means unknown. The interval includes its possible contribution; it is not a scored failure.",
            "limits": "Scores serve this brief. Source review is not runtime acceptance or enterprise certification. Stars describe attention, not quality.",
            "assessment_count": len(reviews), "candidate_execution": False,
        }, "items": items,
    }
