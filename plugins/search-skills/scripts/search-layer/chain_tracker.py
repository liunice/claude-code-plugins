#!/usr/bin/env python3
"""
Recursive content fetcher with LLM relevance gate.

Starting from a list of seed URLs, fetches content, extracts links with
anchor+context, scores them via LLM, and recursively follows high-scoring
links up to max_depth=3.

Usage:
  python3 chain_tracker.py \
    --query "Rust async runtime performance" \
    --urls "https://..." "https://..." \
    [--depth 3] [--threshold 0.5] [--max-per-level 3] [--output results.json]

Based on openclaw-search-skills (https://github.com/blessonism/openclaw-search-skills).
"""

import json
import sys
import argparse
from pathlib import Path

# Add scripts dir to path for sibling imports
sys.path.insert(0, str(Path(__file__).parent))
import fetch_thread
import relevance_gate


# ---------------------------------------------------------------------------
# Knowledge state updater
# ---------------------------------------------------------------------------
def _update_knowledge(knowledge_state: str, node: dict, creds: dict) -> str:
    """Ask LLM to update knowledge_state after reading a new node."""
    title = node.get("title", "")
    body = (node.get("body", "") or "")[:500]
    comments_text = " ".join(c.get("body", "")[:100] for c in node.get("comments", [])[:5])

    prompt = f"""Current knowledge state: {knowledge_state or 'Nothing known yet.'}

Just read: "{title}"
Content summary: {body}
{f'Key comments: {comments_text}' if comments_text else ''}

Update the knowledge state in 1-2 sentences:
- What new facts were learned?
- What is still unclear or needs more investigation?

Respond with ONLY the updated knowledge state text, no preamble."""

    try:
        raw = relevance_gate._call_llm(prompt, creds)
        return raw.strip()
    except Exception:
        return f"{knowledge_state} Also read: {title}." if knowledge_state else f"Read: {title}."


# ---------------------------------------------------------------------------
# Candidate extractor
# ---------------------------------------------------------------------------
def _get_candidates(node: dict) -> list:
    """Extract candidate links from a fetched node."""
    candidates = []
    seen = set()
    for link in node.get("links", []):
        url = link.get("url", "")
        if url and url not in seen:
            seen.add(url)
            candidates.append({
                "url": url,
                "anchor": link.get("anchor", ""),
                "context": link.get("context", ""),
            })
    for ref in node.get("refs", []):
        url = ref.get("url", "")
        if url and url not in seen:
            seen.add(url)
            candidates.append({
                "url": url,
                "anchor": ref.get("type", "reference"),
                "context": ref.get("context", ""),
            })
    return candidates


# ---------------------------------------------------------------------------
# Main tracker
# ---------------------------------------------------------------------------
def track(query: str, seed_urls: list, max_depth: int = 3,
          threshold: float = 0.5, max_per_level: int = 3) -> dict:
    """Run recursive chain tracking from seed URLs."""
    creds = relevance_gate._load_creds()
    visited = set()
    nodes = []
    knowledge_state = ""
    queue = [(url, 0, 1.0, "seed") for url in seed_urls]

    while queue:
        url, depth, score, reason = queue.pop(0)
        canon = url.rstrip("/")
        if canon in visited or depth > max_depth:
            continue
        visited.add(canon)

        sys.stderr.write(f"[chain_tracker] depth={depth} fetching: {url}\n")
        try:
            data = fetch_thread.fetch_thread_url(url)
        except Exception as e:
            sys.stderr.write(f"[chain_tracker] fetch failed: {e}\n")
            continue

        node = {
            "url": url, "depth": depth,
            "type": data.get("type", "unknown"),
            "title": data.get("title", ""),
            "body": (data.get("body", "") or "")[:2000],
            "comments": data.get("comments", [])[:10],
            "score": score, "reason": reason,
        }
        nodes.append(node)

        knowledge_state = _update_knowledge(knowledge_state, node, creds)
        sys.stderr.write(f"[chain_tracker] knowledge: {knowledge_state[:100]}\n")

        if depth >= max_depth:
            continue

        candidates = _get_candidates(data)
        if not candidates:
            continue

        candidates = candidates[:20]
        scored = relevance_gate.score_candidates(
            query=query, candidates=candidates,
            knowledge_state=knowledge_state,
            threshold=threshold, creds=creds,
        )
        for c in scored[:max_per_level]:
            queue.append((c["url"], depth + 1, c["score"], c.get("reason", "")))

    return {
        "query": query,
        "knowledge_state": knowledge_state,
        "nodes": nodes,
        "total_fetched": len(nodes),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Recursive chain tracker with LLM relevance gate")
    ap.add_argument("--query", required=True)
    ap.add_argument("--urls", nargs="+", required=True)
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--max-per-level", type=int, default=3)
    ap.add_argument("--output", help="Write results to file instead of stdout")
    args = ap.parse_args()

    result = track(
        query=args.query, seed_urls=args.urls,
        max_depth=args.depth, threshold=args.threshold,
        max_per_level=args.max_per_level,
    )

    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(out)
        sys.stderr.write(f"[chain_tracker] results written to {args.output}\n")
    else:
        print(out)


if __name__ == "__main__":
    main()
