# Research and rendering workflow

## 1. Create a profile

Choose one input. Paths are examples; use a task-owned output folder.

```bash
python <skill-directory>/scripts/repo_scout.py profile --idea "A personal knowledge assistant using LangChain and local documents" --stack Python --capability RAG --audience individual --out ./results/profile.json
python <skill-directory>/scripts/repo_scout.py profile --local ./my-project --out ./results/profile.json
python <skill-directory>/scripts/repo_scout.py profile --repo https://github.com/langchain-ai/langchain --out ./results/profile.json
```

The profile records a title, goal, stack, capabilities, queries, and target audience. For local input, the scanner reads bounded known manifests and records only technology names and relative filenames. It does not establish business completeness. The host should check the project's actual core flow and refine the goal before searching. Keep search terms abstract enough for public disclosure.

For an idea, clarify concrete input/output and the learning level when that would change the choice: “learn LangChain” can mean its core abstractions, a small RAG application, or operating a multi-user platform. The same repository may score differently for those goals.

## 2. Discover and inspect

```bash
python <skill-directory>/scripts/repo_scout.py search --profile ./results/profile.json --sources github --query "langchain rag tutorial" --query "langchain chatbot examples" --limit 8 --out ./results/search.json
python <skill-directory>/scripts/repo_scout.py inspect --input ./results/search.json --limit 6 --out ./results/inspected.json
```

Use the user's selected sources. GitHub is the default; Gitee and GitLab are configurable adapters. Query syntax differs across providers. When a helper route is unavailable, an available read-only connector or host search may supplement discovery; retain its actual query, source, retrieval time, and project identity. Do not claim helper-collected evidence for manually supplied findings.

The helper returns search receipts and inspection errors. A partial failure permits a bounded conclusion about inspected results, not a claim that the failed source has no matching repositories. Review source coverage before narrowing the shortlist.

The standalone `search --limit` controls hits per provider/query. `inspect --limit` and `run --limit` control the total inspection budget. Discovery retains the collected tail in `search.json`; inspection records how many remain unreviewed. Query/provider combinations are interleaved before applying the inspection budget. A small budget still cannot guarantee coverage of every source or query.

Inspect candidate capabilities against the brief, not an arbitrary checklist. For a RAG learning application, for example, trace document ingestion, indexing, retrieval, generation, and configuration. Authentication or multi-tenancy may be irrelevant to a personal tutorial but decisive for a shared service.

## 3. Add the agent's evidence-based assessment

The initial report uses transparent heuristics from public metadata and structural signals. For the final shortlist, the host reads decisive source paths and writes `assessments.json` as described in [assessment.md](assessment.md). Keep “maintainer says,” “source inspected,” and “executed successfully” distinct.

Use immutable commit links when practical for implementation claims. A branch URL is acceptable when paired with the snapshot's retrieval time. Add useful strengths, gaps, and a short learning path: which file, module, or example to read first and why.

## 4. Score and render offline

```bash
python <skill-directory>/scripts/repo_scout.py score --input ./results/inspected.json --assessments ./results/assessments.json --out ./results/report.json
python <skill-directory>/scripts/repo_scout.py render --input ./results/report.json --out ./results/report.html
```

Optional `--config weights.json` changes scoring weights. See [scoring.md](scoring.md). No network or model call is needed for these two commands. The HTML includes its data, styles, and interaction code, so the reader does not need Python or a service.

## Shortcut

```bash
python <skill-directory>/scripts/repo_scout.py run --idea "Learn LangChain with a small RAG application" --stack Python --capability RAG --sources github --limit 6 --out-dir ./results
```

`run` writes `profile.json`, `search.json`, `inspected.json`, `report.json`, and `report.html`. It can accept `--assessments` when those judgments already exist. Without assessments, describe the result as an initial heuristic pass. Add `--repo-seed <public-url>` for known candidates; these are supplied seeds, not search discoveries.

Distinct successfully resolved seeds reserve the first inspection slots. A seed later returned by a query retains both supplied and search provenance; aliases resolving to one identity are deduplicated. If the distinct resolved seeds exceed `run --limit`, the command reports an error instead of silently omitting a supplied project. Increase the budget or narrow the seed list.

The saved report separates discovery collection (`retrieved_at`), inspection completion (`inspected_at`), and report generation (`generated_at`). Offline rescoring preserves collection dates. Do not label generation time as a fresh API retrieval; candidate metadata also has its own retrieval date.

## Delivery check

Confirm that the report answers the actual brief, distinguishes known from unverified information, preserves unavailable sources, and provides concrete study/reuse recommendations. Check local/private information before sharing. Reading a report is not permission to upload it, publish it, or modify the input project.
