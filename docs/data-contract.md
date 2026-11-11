# Portable report contract (v1)

Repo Scout is an agent skill plus a Python 3.10+ standard-library CLI. Nothing installs or executes candidate repositories. All paths below are relative to the project root.

The self-contained distributable skill is `skills/repo-scout/`. Python entrypoint: `skills/repo-scout/scripts/repo_scout.py`. Internal package: `skills/repo-scout/scripts/scout/`. HTML/CSS/JS assets: `skills/repo-scout/assets/`.

## Profiles

`schema_version: 1`, `kind: idea|local|repository`, `title`, `goal`, `stack: string[]`, `capabilities: string[]`, `queries: string[]`, `target_audience: individual|team|enterprise`, optional `observations: []`. A local profile records only relative filenames and technology names; no absolute paths, source bodies, environment values, private remote credentials, or secrets. The agent can enrich the profile without uploading source files.

## Provider candidates

Every candidate has `id` (`github:owner/repo`, etc.), `provider`, `name` (`owner/repo`), `url`, `description`, `stars` (integer or null), `forks`, `language`, `topics`, `created_at`, `updated_at`, `pushed_at`, `archived`, `license`, `default_branch`, `retrieved_at`.

Inspection adds `last_commit_at`, `latest_release_at`, `readme_excerpt`, `stack: string[]`, `signals` (boolean/null `tests`, `ci`, `docs`, `examples`, `deployment`, `manifest`), `evidence` (objects with `url`, `kind`, `note`), and `inspection_errors: []`. File presence is a structural signal, never a runtime or enterprise-readiness claim.

`scout.providers.get_provider(name)` returns a provider implementing `search(query, limit=10) -> list[dict]`, `inspect(candidate) -> dict`, and `resolve(identifier) -> dict`. Network errors use `ProviderError` and never look like an empty successful search. `scout.profile.build_profile(kind, value, stack=None, capabilities=None, audience='individual') -> dict` analyzes an idea or local directory. Repository input is resolved and inspected by the CLI then turned into the same profile shape. No network access in `profile.py`.

## Search / inspection envelopes

`schema_version`, `profile`, `retrieved_at`, `queries`, `receipts: [{provider, query, status: ok|error, count, error?}]`, `candidates`. A partial provider failure is retained in receipts. Explicit `--repo` seeds are labeled as supplied, not discovered. Discovery ranking is not a quality score.

## Agent assessments

An assessment file contains `schema_version: 1`, `assessments: []`. Each assessment has candidate `id`, optional `summary`, `category`, `stack: string[]`, `audience: {label, reason, evidence: string[]}`, `strengths: string[]`, `gaps: string[]`, `learning_path: string[]`, and `criteria`.

An optional `stack` replaces the automatically detected stack after source review; omit it to preserve collected values. It must be a nonempty list of nonempty technology names and requires a `source-reviewed` `stack_fit` criterion with public evidence links to inspected manifests or implementation. Use it to correct incomplete detection, not to infer dependencies from a repository's name.

Criterion keys are `relevance`, `stack_fit`, `completeness`, `maintenance`, `learning_fit`, `reuse`, `popularity`. Each value is `{value: number 0..5 or null, reason: string, evidence: string[], status: 'source-reviewed'|'heuristic'|'unknown'}`. A source-reviewed non-null judgment requires an evidence link and an explanation. No candidate execution is implied. Do not fabricate missing metrics or public evidence.

Default weights: relevance 25, stack_fit 15, completeness 15, maintenance 10, learning_fit 15, reuse 15, popularity 5. Profiles prioritize personal learning by default; enterprise size is not a bonus.

## Ranked reports

`schema_version: 1`, `title`, `generated_at` (report generation), `retrieved_at` (discovery collection), `inspected_at` (inspection completion), `profile`, `weights`, `source_receipts`, `methodology`, `items`. Rescoring preserves the collection dates; each item also retains its metadata retrieval time. Each item preserves candidate metadata, merges assessment fields and has `criteria`, `score` (conservative weighted lower bound /100), `score_upper` (unknown criteria at maximum), `coverage` (known weight /100), `review_coverage` (weight with source-reviewed judgments /100), `rank`. Unknown is distinct from a scored zero. Sort by lower bound descending, coverage descending, then name. Configured weights must be finite nonnegative numbers, with a positive sum; normalize them to 100. Rank is for this brief, not a universal quality score.

`scout.render.render_report(report, output_path)` writes one offline self-contained HTML with escaped embedded JSON. It must not fetch external scripts, fonts, analytics, images, or candidate URLs. Project links are http(s)-only. Report controls may rerank with local weights, filter candidates, and compare selected projects. Preserve provenance, source failures, uncertainty, and snapshot dates.

## CLI contract

Commands: `profile (--idea TEXT|--local PATH|--repo URL) [--stack ...] [--capability ...] [--audience ...] --out FILE`; `search --profile FILE --sources github,gitee,gitlab [--query TEXT ...] [--limit N] --out FILE`; `inspect --input FILE [--limit N] --out FILE`; `score --input FILE [--assessments FILE] [--config FILE] --out FILE`; `render --input FILE --out FILE`; `run (--idea TEXT|--local PATH|--repo URL) --out-dir DIR [--sources ...] [--query TEXT ...] [--repo-seed URL ...] [--limit N] [--stack ...] [--capability ...] [--audience ...] [--config FILE] [--assessments FILE]`. `run` writes profile.json, search.json, inspected.json, report.json, report.html and emits compact JSON paths. `score` and `render` are fully offline. UTF-8 is required.
