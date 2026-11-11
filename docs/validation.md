# Validation record

Date: 2026-11-11. Candidate research is read-only. No candidate packages, model services or databases were installed or started.

## Local checks

- Python unittest suite: **38 tests, 37 passed, 1 skipped**. The skipped symlink case needs Windows symlink creation permission; the same regression runs where supported.
- Meaningful regressions cover local-source privacy boundaries, provider normalization/failure handling, public-only metadata, cross-origin credentials, multi-provider selection, seed priority/provenance, unknown score intervals, configurable ranking, stale-data dates, and HTML/script injection.
- CLI idea → profile, score → JSON, render → HTML exercised offline; a separate network-blocked fixture completed local project → discovery → inspection → assessments → report.
- A real public repository URL was profiled through the CLI without installing its code.
- Skill metadata validation passed; JavaScript syntax check passed.
- Bundled LangChain report rebuilds from saved inspected data and assessments without network access. The generated report JSON, HTML and Pages copy are checked for consistency.

## Live provider scope

See [provider-smoke.json](provider-smoke.json) for the bounded source receipts. Its offline-test count records the earlier provider-only validation, not the final suite above.

| Provider | Verified live | Limit |
|---|---|---|
| GitHub | Public search, 8-repository inspection, repository input | Stars and dates are snapshots; one tree request failed and remains visible |
| Gitee | Public search returned 0; direct repository metadata succeeded | Does not establish absence of projects; full inspection and authenticated path were not live-tested |
| GitLab.com | Public search, resolve, full bounded inspection | One small public repository; not general compatibility with private/self-hosted GitLab |

## Example scope

Three GitHub queries produced 26 unique candidates; 8 were selected for deeper static review. Seven dimensions include source-linked qualitative judgments and date/Stars heuristics. Missing license evidence stays unknown. All 8 candidates preserve source provenance. Qualitative source links use pinned commits.

Tests of Repo Scout do not prove that candidate projects install, pass tests, scale, isolate users or operate safely in production. Enterprise-oriented classification describes intended scope and operating effort.

## Browser and publication

The published HTTPS example is used for visual and interaction verification. Browser results and real screenshot paths will be recorded after that check.
