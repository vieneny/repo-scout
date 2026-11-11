# Contributing

Repo Scout helps people choose what to study and reuse. Changes should improve the decision, its evidence, or the time needed to reach it.

## Development setup

Use Python 3.10 or later. The core CLI and tests use the standard library; no candidate installation or model service is required.

```bash
python -m unittest discover -s tests -v
```

Run the relevant CLI command with a task-owned output directory when changing behavior. Keep generated personal reports outside committed examples. Never add credentials, local absolute paths, private source excerpts, or unreviewed external instructions to test fixtures.

## Provider changes

Implement the normalized interface in [docs/data-contract.md](docs/data-contract.md). Preserve nulls for missing facts and record failed requests separately from successful empty searches. Bound requests and response sizes. Send credentials only to the intended provider; do not put them in query strings or exceptions.

Add deterministic tests for representative payloads, missing fields, pagination/limits where relevant, and upstream failures. A mocked contract test proves adapter behavior, not live upstream availability. Record live checks separately with source and date.

## Scoring changes

Keep scoring deterministic and uncertainty visible. Test meaningful invariants: nonnegative finite weights, normalization, score bounds, unknown-versus-zero semantics, reproducible ordering, and evidence requirements. Do not add a high Star count or an enterprise label as a universal quality bonus.

Explain how a proposed rule improves a real brief. A directory name can support a structural observation, not a claim that tests passed or a business flow is complete. Preserve that distinction in reports and documentation.

## Report changes

Keep the report self-contained, keyboard usable, responsive, printable, and useful offline. User-controlled data must be treated as text and links must remain http(s)-only. Test embedded JSON and source content containing HTML/script delimiters. No CDN, analytics, external fonts, or background network requests.

Review generated screenshots after visual changes. Confirm that filters, comparison, local scoring changes, uncertainty, and source-failure messages remain understandable. Do not claim visual review merely because screenshot generation succeeded.

## Case studies

Include the brief, search/inspection receipts, assessment input, report JSON, and HTML when updating a public example. State retrieval dates and actual validation levels. Avoid retelling maintainer claims as independently tested behavior. Record useful negative findings and incomplete evidence instead of inventing a complete comparison.

## Pull requests

Describe the user-visible problem and resulting behavior, then list relevant validation and remaining limitations. Keep changes focused. Contributions are provided under the project's MIT license; third-party source material retains its own license and attribution requirements.
