# Scoring with visible uncertainty

Repo Scout ranks suitability for a specific brief. It does not certify software or assign universal project quality.

| Criterion key | Default weight | What the judgment should address |
|---|---:|---|
| `relevance` | 25 | Match to the actual problem, input, output, and required capabilities |
| `stack_fit` | 15 | Languages, frameworks, database, platform, versions, and integration fit |
| `completeness` | 15 | Evidence that the relevant workflow is implemented and reasonably documented/tested |
| `maintenance` | 10 | Meaningful recent work, releases, maintainer responses, archived status, and stability |
| `learning_fit` | 15 | Readability, examples, setup effort, scope, and the learner's experience |
| `reuse` | 15 | License, useful boundaries, dependency burden, and integration work |
| `popularity` | 5 | Public adoption signals such as Stars/Forks, interpreted in source context |

Each criterion uses a value from 0 to 5 or `null`, plus a reason, evidence links, and a status. A source-reviewed value requires a relevant evidence link and an explanation. `heuristic` means a transparent approximation, not a verified result. `unknown` means the material fact is unavailable or not assessed.

## Bounds and coverage

For weights normalized to a total of 100:

```text
lower bound = sum(weight × value / 5) for known criteria
upper bound = lower bound + sum(weight) for unknown criteria
coverage = sum(weight) for known criteria / 100
review coverage = sum(weight) for source-reviewed criteria / 100
```

The reported `score` is the conservative lower bound. Unknown criteria widen the interval; they are not factual zero scores. A reviewed zero has evidence and does not widen the interval. Default ordering is lower bound, then known-evidence coverage, then project name. Review the interval and coverage alongside rank, especially when candidates have uneven evidence.

The report can locally change weights and reorder candidates without calling a server. Its scoring should remain consistent with the report JSON. Values describe the brief at the snapshot date; do not present small point differences as measured performance.

## Configure priorities

Pass a JSON file through `--config weights.json`:

```json
{
  "weights": {
    "relevance": 25,
    "stack_fit": 15,
    "completeness": 15,
    "maintenance": 10,
    "learning_fit": 15,
    "reuse": 15,
    "popularity": 5
  }
}
```

Use finite nonnegative numbers with a positive total. The CLI normalizes them. Increase `learning_fit` for a beginner; increase `completeness` and `reuse` when adapting a real application. “Enterprise-oriented” is an audience/scope label, not an automatic score bonus.

Completeness is relative to the desired outcome. A readable Java application with a real business flow and database may fit a graduation project better than a large enterprise platform. A media tool may be unusable for the brief if its required GPU, paid API, model access, or output rights conflict with a constraint. Explain these effects under the existing relevance, completeness, learning, or reuse criteria without double-counting a single issue across every score. See [scenarios.md](scenarios.md) for domain-specific evidence to inspect. If a decisive requirement is unknown, expose the gap and its score uncertainty.

## Avoid weak proxies

- The primary GitHub language does not establish the full stack. Read manifests and configuration.
- A tests directory, CI file, or Dockerfile establishes structure, not successful tests or deployment. Automated completeness judgments are deliberately limited; source review adds the decisive context.
- Record creation time, latest code commit, latest release, and retrieval date separately. `updated_at` can reflect metadata changes. `pushed_at` may include bots or non-code changes. A stable project can remain useful without frequent releases.
- Stars are attention, not active users or correctness. Cross-provider counts are not interchangeable measurements.
- Personal suitability depends on setup and conceptual burden. A smaller example can beat a mature platform for learning. Enterprise readiness requires much more than a README claim or repository size.
- A permissive license can improve reuse fit, but licensing details and third-party assets still require source-specific review. A missing license remains unknown/restricted rather than assumed open for reuse.
