# Validation record

Date: 2026-11-11. Candidate research is read-only. No candidate packages, model services or databases were installed or started.

## Local checks

- Python unittest suite: **52 tests, 51 passed, 1 skipped**. The skipped symlink case needs Windows symlink creation permission; the same regression runs where supported.
- Meaningful regressions cover local-source privacy boundaries, provider normalization/failure handling, public-only metadata, cross-origin credentials, multi-provider selection, seed priority/provenance, evidence-backed stack corrections, unknown score intervals, configurable ranking, stale-data dates, and HTML/script injection. The broader-scenario expansion adds Chinese Java graduation-goal recognition, creative-tool dependency/capability detection, explicit constraints that stay out of automatic public queries, and source-linked operating requirements in scoring/rendering.
- CLI idea → profile, score → JSON, render → HTML exercised offline; a separate network-blocked fixture completed local project → discovery → inspection → assessments → report.
- An independent review also completed two network-blocked synthetic workflows: the exact direct-reference Java graduation brief, and a ComfyUI/video brief with Windows/no-paid-API constraints. It checked profile/query intent, static dependency parsing, private sentinel exclusion, sourced usage requirements and inert hostile text in rendered HTML.
- A real public repository URL was profiled through the CLI without installing its code.
- Skill metadata validation passed; JavaScript syntax check passed.
- Bundled LangChain report rebuilds from saved inspected data and assessments without network access. The generated report JSON, HTML and Pages copy are checked for consistency.
- [GitHub Actions verification](https://github.com/vieneny/repo-scout/actions/runs/42981012452) passed on Ubuntu and Windows with Python 3.10 and 3.12; the JavaScript job also passed. That run tested broader-scenario implementation commit `c6b8c9831179ece56b73c590da4cdbd85143ed6f`. Later publication checks are available in [Actions](https://github.com/vieneny/repo-scout/actions/workflows/checks.yml).

## Live provider scope

See [provider-smoke.json](provider-smoke.json) for the bounded source receipts. Its offline-test count records the earlier provider-only validation, not the final suite above.

| Provider | Verified live | Limit |
|---|---|---|
| GitHub | Public search, 8-repository inspection, repository input | Stars and dates are snapshots; one tree request failed and remains visible |
| Gitee | Public search returned 0; direct repository metadata succeeded | Does not establish absence of projects; full inspection and authenticated path were not live-tested |
| GitLab.com | Public search, resolve, full bounded inspection | One small public repository; not general compatibility with private/self-hosted GitLab |

## Example scope

Three GitHub queries produced 26 unique candidates; 8 were selected for deeper static review. Seven dimensions include source-linked qualitative judgments and date/Stars heuristics. Missing license evidence stays unknown. All 8 candidates preserve source provenance. Qualitative source links use pinned commits.

The Java graduation and creative-tool prompts in the READMEs are usage examples, not additional live research results. The new scenario behavior is covered by offline fixtures; the bundled LangChain data retains its original collection dates when its HTML presentation is regenerated.

Tests of Repo Scout do not prove that candidate projects install, pass tests, scale, isolate users or operate safely in production. Enterprise-oriented classification describes intended scope and operating effort.

## Browser and publication

The [published HTTPS example](https://vieneny.github.io/repo-scout/) was opened and tested in the in-app browser at its default viewport; the unmodified captures are 772 × 750. The page had no document-level horizontal overflow, and the captured console contained no errors. The broader-scenario update was reopened to verify the new search/detail labels, search for `RAGNotebook`, and three-project comparison, then refresh the screenshot. This is one browser/viewport check, not a full cross-browser or mobile compatibility certification.

Verified interactions:

- Search for `RAGNotebook` yields one result; a nonexistent term shows the empty state, and clearing restores the list.
- The team filter yields two candidates; sorting by Stars puts LangChain, LangGraph and Chatchat first.
- Weight presets recalculate displayed percentages and ranking; reset restores the saved defaults.
- Three selected candidates open a comparison table. Selecting a fourth is rejected with an explicit limit notice; Escape closes the dialog.
- Light/dark switching, evidence expansion and discovery provenance display work.
- The final page shows the source-reviewed runtime stacks, including the recovered LangChain/LangGraph stack for `agent-craft`.

Real, unmodified browser captures are included in the READMEs: [overview.jpg](screenshots/overview.jpg) and [compare.jpg](screenshots/compare.jpg). They were captured from the published report, not generated as mockups. The online report and public `main` were verified after publication; no local application server was started.
