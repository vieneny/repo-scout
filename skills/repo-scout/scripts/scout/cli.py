"""Read-only research pipeline and offline report commands."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

from . import __version__
from .profile import build_profile
from .providers import get_provider, ProviderError
from .scoring import build_report
from .render import render_report


def read_json(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path, value):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _time():
    return datetime.now(timezone.utc).isoformat()


def _repo_provider(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("repository URLs must be public HTTPS URLs without credentials, query or fragment")
    provider = {"github.com": "github", "gitee.com": "gitee", "gitlab.com": "gitlab"}.get(parsed.hostname)
    if not provider or not parsed.path.strip("/"):
        raise ValueError("supported repository URL hosts: github.com, gitee.com, gitlab.com")
    return provider


def make_profile(args):
    if args.repo:
        provider = get_provider(_repo_provider(args.repo))
        candidate = provider.inspect(provider.resolve(args.repo))
        profile = build_profile("idea", candidate.get("description") or candidate["name"], stack=args.stack or candidate.get("stack"), capabilities=args.capability, audience=args.audience, constraints=args.constraint)
        profile.update(kind="repository", title=candidate["name"], repository_url=candidate["url"], seed_id=candidate["id"])
        profile["observations"] = [{"kind": "repository-metadata", "url": candidate["url"], "note": "Public metadata and bounded source inspection; candidate code was not executed."}]
        return profile
    return build_profile("local" if args.local else "idea", args.local or args.idea, stack=args.stack, capabilities=args.capability, audience=args.audience, constraints=args.constraint)


def discover(profile, sources, queries=None, limit=8, seeds=None):
    sources = list(dict.fromkeys(sources))
    if not sources or any(source not in {"github", "gitee", "gitlab"} for source in sources):
        raise ValueError("sources must be selected from github,gitee,gitlab")
    if profile.get("kind") == "local" and not queries and not profile.get("queries"):
        raise ValueError("Local profile has no abstract search terms; add --capability, --stack, or --query instead of sending a directory name")
    queries = list(dict.fromkeys(queries or profile.get("queries") or [profile["title"]]))
    if not queries or not all(isinstance(query, str) and query.strip() for query in queries):
        raise ValueError("at least one nonempty query is required")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 30:
        raise ValueError("limit must be between 1 and 30")
    seed_urls = list(dict.fromkeys(seeds or []))
    if len(seed_urls) > 30:
        raise ValueError("at most 30 distinct --repo-seed URLs can be resolved in one run")
    # Validate all URLs before touching the network. Aliases may resolve to one ID,
    # so the actual reserved-slot check uses distinct successful repository IDs.
    seed_sources = [(url, _repo_provider(url)) for url in seed_urls]
    candidates, receipts, supplied_ids = {}, [], []

    def merge(item, hit):
        identifier = item["id"]
        if identifier not in candidates:
            candidates[identifier] = dict(item, discovery=[])
        provenance = candidates[identifier]["discovery"]
        if hit not in provenance:
            provenance.append(hit)

    for url, source in seed_sources:
        try:
            item = get_provider(source).resolve(url)
            merge(item, {"type": "supplied", "query": None, "provider": source})
            if item["id"] not in supplied_ids:
                supplied_ids.append(item["id"])
            receipts.append({"provider": source, "query": url, "status": "ok", "count": 1, "type": "supplied", "retrieved_at": _time()})
        except ProviderError as exc:
            receipts.append({"provider": source, "query": url, "status": "error", "count": None, "error": str(exc), "type": "supplied", "retrieved_at": _time()})
    if len(supplied_ids) > limit:
        raise ValueError(f"{len(supplied_ids)} distinct supplied repositories exceed the --limit {limit} inspection budget; increase --limit or remove seeds")

    # Buckets identify a provider AND query. Query-only buckets put every hit from
    # the first provider before the others and can erase later providers at a
    # small inspection budget. Query-major pair order preserves explicit query
    # priority while giving each provider a first hit before deeper results.
    buckets = []
    providers = {source: get_provider(source) for source in sources}
    for query in queries[:6]:
        for source in sources:
            provider = providers[source]
            bucket = []
            try:
                results = provider.search(query, limit=limit)
                receipts.append({"provider": source, "query": query, "status": "ok", "count": len(results), "retrieved_at": _time()})
                for result in results:
                    if result["id"] == profile.get("seed_id"):
                        continue
                    merge(result, {"query": query, "type": "search", "provider": source})
                    if result["id"] not in bucket:
                        bucket.append(result["id"])
            except ProviderError as exc:
                receipts.append({"provider": source, "query": query, "status": "error", "count": None, "error": str(exc), "retrieved_at": _time()})
            buckets.append(bucket)
    # Explicitly supplied repositories reserve the first slots. With an
    # inspection limit smaller than the number of providers/pairs, the remaining
    # tail stays available and is counted as unreviewed by inspect_envelope.
    ordered = {identifier: candidates[identifier] for identifier in supplied_ids}
    for index in range(max([len(bucket) for bucket in buckets] or [0])):
        for bucket in buckets:
            if index < len(bucket):
                identifier = bucket[index]
                ordered.setdefault(identifier, candidates[identifier])
    ordered.update({key: value for key, value in candidates.items() if key not in ordered})
    return {"schema_version": 1, "profile": profile, "retrieved_at": _time(), "queries": queries, "receipts": receipts, "candidates": list(ordered.values())}


def inspect_envelope(envelope, limit=8):
    if envelope.get("schema_version") != 1 or not isinstance(envelope.get("candidates"), list):
        raise ValueError("expected a candidate envelope with schema_version 1")
    inspected = []
    for original in envelope["candidates"][:limit]:
        try:
            item = get_provider(original["provider"]).inspect(original)
        except ProviderError as exc:
            item = dict(original, inspection_errors=[str(exc)])
        inspected.append(item)
    result = dict(envelope, candidates=inspected, inspected_at=_time())
    result["inspection"] = {"available": len(envelope["candidates"]), "inspected": len(inspected), "unreviewed": max(0, len(envelope["candidates"]) - len(inspected))}
    return result


def _input_flags(parser):
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--idea", help="Project concept or learning goal")
    group.add_argument("--local", help="Local project directory, read only")
    group.add_argument("--repo", help="Public GitHub/Gitee/GitLab repository URL")
    parser.add_argument("--stack", action="append", default=[], help="Desired technology; repeatable")
    parser.add_argument("--capability", action="append", default=[], help="Core capability; repeatable")
    parser.add_argument("--constraint", action="append", default=[], help="Explicit setup, license, hardware, or other constraint; repeatable, retained for agent review")
    parser.add_argument("--audience", choices=["individual", "team", "enterprise"], default="individual")


def parser():
    root = argparse.ArgumentParser(description="Evidence-first open-source project research and offline reports")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    profile = commands.add_parser("profile", help="Build a project brief without uploading local source")
    _input_flags(profile); profile.add_argument("--out", required=True)
    search = commands.add_parser("search", help="Search configured public forges")
    search.add_argument("--profile", required=True); search.add_argument("--sources", default="github")
    search.add_argument("--query", action="append"); search.add_argument("--limit", type=int, default=8, help="Hits per provider/query (1..30); all collected candidates are retained"); search.add_argument("--out", required=True)
    inspect = commands.add_parser("inspect", help="Collect bounded candidate source evidence")
    inspect.add_argument("--input", required=True); inspect.add_argument("--limit", type=int, default=8); inspect.add_argument("--out", required=True)
    score = commands.add_parser("score", help="Rank evidence; no network")
    score.add_argument("--input", required=True); score.add_argument("--assessments"); score.add_argument("--config"); score.add_argument("--out", required=True)
    render = commands.add_parser("render", help="Write standalone interactive HTML; no network")
    render.add_argument("--input", required=True); render.add_argument("--out", required=True)
    run = commands.add_parser("run", help="Collect, inspect, score and render")
    _input_flags(run)
    run.add_argument("--out-dir", required=True); run.add_argument("--sources", default=None)
    run.add_argument("--query", action="append"); run.add_argument("--repo-seed", action="append", default=[], help="Reserve inspection slots for supplied public repository URLs; repeatable, distinct resolved seeds must fit --limit")
    run.add_argument("--limit", type=int, default=8, help="Total inspection budget (1..30); supplied seeds first, then provider/query pairs interleaved"); run.add_argument("--config"); run.add_argument("--assessments")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if hasattr(args, "limit") and not 1 <= args.limit <= 30:
            raise ValueError("limit must be between 1 and 30")
        if args.command == "profile":
            profile = make_profile(args); write_json(args.out, profile)
            result = {"profile": str(Path(args.out)), "kind": profile["kind"]}
        elif args.command == "search":
            envelope = discover(read_json(args.profile), [s.strip() for s in args.sources.split(",")], args.query, args.limit)
            write_json(args.out, envelope)
            result = {"search": str(Path(args.out)), "candidates": len(envelope["candidates"]), "errors": sum(row["status"] == "error" for row in envelope["receipts"])}
            if not any(row["status"] == "ok" for row in envelope["receipts"]):
                print(json.dumps(result)); return 3
        elif args.command == "inspect":
            envelope = inspect_envelope(read_json(args.input), args.limit); write_json(args.out, envelope)
            result = {"inspected": str(Path(args.out)), **envelope["inspection"]}
        elif args.command == "score":
            report = build_report(read_json(args.input), read_json(args.assessments) if args.assessments else None, read_json(args.config) if args.config else None)
            write_json(args.out, report); result = {"report": str(Path(args.out)), "ranked": len(report["items"])}
        elif args.command == "render":
            report = read_json(args.input); render_report(report, args.out)
            result = {"html": str(Path(args.out))}
        else:
            config = read_json(args.config) if args.config else {}
            # Validate configuration before making any network requests.
            from .scoring import normalized_weights
            normalized_weights(config.get("weights"))
            sources = args.sources.split(",") if args.sources else config.get("sources", ["github"])
            if not isinstance(sources, list):
                raise ValueError("config sources must be a list")
            output = Path(args.out_dir); output.mkdir(parents=True, exist_ok=True)
            profile = make_profile(args); write_json(output / "profile.json", profile)
            envelope = discover(profile, [s.strip() for s in sources], args.query, args.limit, args.repo_seed)
            write_json(output / "search.json", envelope)
            if not envelope["candidates"]:
                print(json.dumps({"search": str(output / "search.json"), "candidates": 0, "message": "No candidates; inspect source receipts before changing queries."})); return 3
            inspected = inspect_envelope(envelope, args.limit); write_json(output / "inspected.json", inspected)
            report = build_report(inspected, read_json(args.assessments) if args.assessments else None, config)
            write_json(output / "report.json", report); render_report(report, output / "report.html")
            result = {"output": str(output), "html": str(output / "report.html"), "report": str(output / "report.json"), "ranked": len(report["items"]), "source_errors": sum(row["status"] == "error" for row in envelope["receipts"])}
        print(json.dumps(result, ensure_ascii=False)); return 0
    except (ValueError, OSError, ProviderError, KeyError, TypeError) as exc:
        # API adapters provide credential-free messages. Never echo auth headers,
        # remote request bodies, or candidate environment configuration.
        print(json.dumps({"error": str(exc), "type": type(exc).__name__}, ensure_ascii=False), file=sys.stderr)
        return 2
