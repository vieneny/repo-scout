# Sources, credentials, and evidence boundaries

Select sources with `--sources github`, `--sources gitee`, `--sources gitlab`, or a comma-separated combination. GitHub is the default. These names select adapters; they do not imply equal search coverage or that every upstream service is currently reachable.

| Source | API | Optional environment variables | Practical boundary |
|---|---|---|---|
| GitHub | `https://api.github.com` | `GITHUB_TOKEN` or `GH_TOKEN` | Anonymous rate limits are restrictive; search has a separate quota. Native qualifiers are useful for targeted searches. |
| Gitee | `https://gitee.com/api/v5` | `GITEE_TOKEN` | Search availability and permissions depend on the upstream API. An unavailable endpoint must remain an error in receipts. |
| GitLab | `https://gitlab.com/api/v4` | `GITLAB_TOKEN` | Public project search is not GitHub's search syntax; namespace and project identity require care. |

The bundled adapters use bounded read-only requests and public repository snapshots. They do not clone or execute candidate code. Tokens are sent only to their intended provider and are not written to reports. Do not put tokens in URLs, command arguments, committed configuration, screenshots, or example data.

`score` and `render` are offline. The generated HTML has no external scripts, fonts, analytics, or background API calls. Following a project/evidence link is a deliberate browser navigation.

## Query design

Start with the user's goal, domain, capabilities, and stack. Use short, contrasting query families, then inspect evidence rather than packing all requirements into one query. For GitHub, `language:`, `topic:`, `in:readme`, and `stars:` may help. Do not send those qualifiers unchanged to another source without checking its semantics.

Named repositories are seeds. Results discovered by a search are query hits. Keep those origins visible; reranking a seed is not a discovery. Multiple access clients for the same provider are not independent sources.

Other sources can be added through a provider adapter or by the host's documented read-only research route. Do not list Codeberg, SourceHut, a private GitLab instance, or web search as a bundled adapter until it is implemented and its limits are tested. Preserve provenance when incorporating externally researched candidates into an assessment.

## Partial failures

Search and inspection retain provider/query receipts and candidate inspection errors. A request that fails is not an empty result. Continue with available sources when they still support a useful bounded answer; report the missing coverage. Do not change credentials, relax transport checks, or silently substitute another source to hide a failure.

## Public sharing

A local project can be analyzed without publishing its source. Only include task-relevant abstract technology/capability terms in public queries. Inspect exported profiles and reports before sharing them: private project names, proprietary facts, internal URLs, and code-derived details can still be sensitive even without a source file body.
