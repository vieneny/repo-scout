"""Rebuild the bundled research result offline and verify the scoring artifact."""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/repo-scout/scripts"))
from scout.scoring import build_report
from scout.render import render_report
from datetime import datetime

case = ROOT / "examples/langchain"
read = lambda name: json.loads((case / name).read_text(encoding="utf-8"))
stored = read("report.json")
rebuilt = build_report(read("inspected.json"), read("assessments.json"), now=datetime.fromisoformat(stored["generated_at"].replace("Z", "+00:00")))
if stored != rebuilt:
    raise SystemExit("Example report differs from the inspected evidence and assessments")
with tempfile.TemporaryDirectory() as temp:
    rendered = render_report(rebuilt, Path(temp) / "report.html")
    if rendered.read_bytes() != (case / "report.html").read_bytes():
        raise SystemExit("Example HTML is stale; regenerate with the current renderer")
    if rendered.read_bytes() != (ROOT / "docs/index.html").read_bytes():
        raise SystemExit("Published demo is stale; copy the rebuilt example to docs/index.html")
print(f"Offline example verified: {len(stored['items'])} candidates; no network or candidate code execution")
