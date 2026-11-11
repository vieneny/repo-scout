# Agent assessment handoff

The helper collects facts; the host agent evaluates what those facts mean for the user's goal. Add an assessment file after source inspection, then pass it to `score --assessments` or `run --assessments`.

Match `id` exactly to a candidate in `inspected.json`, including the provider prefix. Candidate metadata such as Stars and timestamps comes from collection rather than this file. Use `criteria` keys from [scoring.md](scoring.md).

```json
{
  "schema_version": 1,
  "assessments": [
    {
      "id": "github:owner/repository",
      "summary": "Explain why this project fits this learning goal.",
      "category": "application",
      "stack": ["Python", "LangChain"],
      "audience": {
        "label": "individual",
        "reason": "Describe setup and conceptual effort, not company size.",
        "evidence": ["https://github.com/owner/repository/blob/main/README.md"]
      },
      "criteria": {
        "stack_fit": {
          "value": 5,
          "reason": "Inspected dependencies and imports confirm the relevant runtime stack.",
          "evidence": ["https://github.com/owner/repository/blob/main/requirements.txt"],
          "status": "source-reviewed"
        },
        "completeness": {
          "value": 3,
          "reason": "Describe inspected implementation and remaining gaps.",
          "evidence": ["https://github.com/owner/repository/blob/main/README.md"],
          "status": "source-reviewed"
        },
        "learning_fit": {
          "value": null,
          "reason": "No setup or examples were inspected yet.",
          "evidence": [],
          "status": "unknown"
        }
      },
      "strengths": ["A concrete strength supported by inspected evidence"],
      "gaps": ["A task-relevant missing or unverified capability"],
      "usage_requirements": ["Describe a setup, model or operating requirement actually found in the documentation; state what remains unknown."],
      "usage_evidence": ["https://github.com/owner/repository/blob/main/README.md"],
      "learning_path": ["Start with the relevant example, then read its implementation."]
    }
  ]
}
```

The URLs above illustrate the schema; replace them with actual inspected public sources. Prefer implementation or manifest links for implementation/stack claims and release/commit links for time claims. Do not reuse a README URL as generic evidence for unrelated claims.

The optional `stack` field supplements or corrects incomplete automatic detection by replacing the collected list. Omit it to preserve the detected stack. Supply a nonempty list of nonempty technology names, and include a `source-reviewed` `stack_fit` judgment with public links to the manifests or implementation actually inspected. List the primary runtime stack; do not present development or test dependencies as application requirements. Stars and timestamps remain collector metadata.

Use optional `usage_requirements` for nonempty notes about actual setup, hardware, supported inputs/outputs, model downloads, API costs, and code/model/asset licensing. A nonempty list requires public http(s) links in `usage_evidence`; both fields appear in detail and comparison views. Label undocumented values as unknown, attribute published performance numbers to their source, and distinguish maintainer samples from your own execution. Do not assume a permissive code license also covers model weights, training data or generated assets. Omit these fields when they add no useful decision evidence.

Supported criterion statuses are `source-reviewed`, `heuristic`, and `unknown`. Values must be finite numbers from 0 through 5, or `null`. Do not mark execution as source review: if runtime testing was separately authorized, describe exactly what was executed and its result in the reason or evidence, without implying a full production audit.

Audience labels distinguish `individual`, `team`, `enterprise-oriented`, and `unknown`. The user's target audience is a scoring preference; the candidate's label describes observed setup and scope. The exact JSON remains available to the reader alongside the rendered report.
