"""Render a ranked research snapshot as one portable, offline HTML document."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _embedded_json(value: Any) -> str:
    """Keep data inert even when a source contains an HTML closing script tag."""
    return (json.dumps(value, ensure_ascii=False, allow_nan=False)
            .replace("&", "\\u0026")
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029"))


def _report_date(value: Any) -> str:
    """Format each timestamp independently; generation is never a data date."""
    if not isinstance(value, str) or not value:
        return "未知"
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return "未知"
        return stamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return "未知"


def render_report(report: dict[str, Any], output_path: str | Path) -> Path:
    """Write a standalone report; no network calls or candidate execution occur.

    The browser treats repository text as textContent, and all outgoing source
    links are checked for http(s) schemes before being made clickable.
    """
    if not isinstance(report, dict):
        raise ValueError("Report must be an object")
    if report.get("schema_version") != 1:
        raise ValueError("Unsupported report schema_version; expected 1")
    if not isinstance(report.get("items"), list):
        raise ValueError("Report items must be a list")
    if not isinstance(report.get("profile", {}), dict):
        raise ValueError("Report profile must be an object")
    assets = Path(__file__).resolve().parents[2] / "assets"
    template = (assets / "report.html").read_text(encoding="utf-8")
    title = str(report.get("title") or report.get("profile", {}).get("title") or "Repo Scout 项目参考报告")
    substitutions = {
        "__REPORT_TITLE__": html.escape(title, quote=True),
        "__REPORT_STYLE__": (assets / "report.css").read_text(encoding="utf-8"),
        "__REPORT_DATA__": _embedded_json(report),
        "__REPORT_SCRIPT__": (assets / "report.js").read_text(encoding="utf-8"),
        "__SNAPSHOT_DATE__": html.escape(_report_date(report.get("retrieved_at"))),
        "__INSPECTED_DATE__": html.escape(_report_date(report.get("inspected_at"))),
        "__GENERATED_DATE__": html.escape(_report_date(report.get("generated_at"))),
    }
    # Substitute only placeholders in the template, never matching a marker
    # that happens to occur inside untrusted repository text or the title.
    pattern = re.compile("|".join(re.escape(key) for key in substitutions))
    rendered = pattern.sub(lambda match: substitutions[match.group()], template)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    return target
