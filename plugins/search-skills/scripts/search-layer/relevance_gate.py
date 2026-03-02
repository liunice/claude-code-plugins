#!/usr/bin/env python3
"""
LLM-based relevance scoring for chain tracking.

Given an original query, current knowledge_state, and a list of candidate
links (with anchor_text + context), calls an LLM to batch-score each candidate
and returns only those above the threshold.

Uses Grok via OpenAI-compatible API. Credentials loaded from environment variables.

Usage (standalone):
  python3 relevance_gate.py \
    --query "Rust async runtime performance" \
    --knowledge "Already know: Tokio vs async-std comparison." \
    --candidates '[{"url":"...","anchor":"...","context":"..."}]' \
    --threshold 0.5

Based on openclaw-search-skills (https://github.com/blessonism/openclaw-search-skills).
"""

import json
import os
import sys
import argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError


# ---------------------------------------------------------------------------
# Credentials loader (pure environment variables)
# ---------------------------------------------------------------------------
def _load_creds() -> dict:
    """Load Grok API credentials from environment variables."""
    keys = {}
    if v := os.environ.get("GROK_API_KEY"):
        keys["grok_key"] = v
    # Defaults for URL and model
    keys["grok_url"] = os.environ.get("GROK_API_URL", "https://api.x.ai/v1")
    keys["grok_model"] = os.environ.get("GROK_MODEL", "grok-4.20-beta")
    return keys


# ---------------------------------------------------------------------------
# LLM call (OpenAI-compatible API)
# ---------------------------------------------------------------------------
def _call_llm(prompt: str, creds: dict) -> str:
    """Call Grok (or any OpenAI-compatible API) and return response text."""
    url = creds.get("grok_url", "https://api.x.ai/v1").rstrip("/") + "/chat/completions"
    api_key = creds.get("grok_key", "")
    model = creds.get("grok_model", "grok-4.20-beta")

    if not api_key:
        raise ValueError("No LLM API key configured (GROK_API_KEY missing)")

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1024,
        "stream": False,
    }).encode()

    req = Request(url, data=payload, method="POST", headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    })

    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()

        # Handle SSE streaming response (server ignores stream:false)
        if raw.startswith("data:"):
            content_parts = []
            for line in raw.splitlines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    obj = json.loads(chunk)
                    delta = obj["choices"][0].get("delta", {})
                    if text := delta.get("content"):
                        content_parts.append(text)
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
            return "".join(content_parts)

        data = json.loads(raw)
        return data["choices"][0]["message"]["content"]

    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"LLM API error {e.code}: {body[:200]}")


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------
def _build_prompt(query: str, knowledge_state: str, candidates: list) -> str:
    cand_lines = []
    for i, c in enumerate(candidates, 1):
        anchor = c.get("anchor") or c.get("context", "")[:60]
        context = c.get("context", "")[:150]
        url = c.get("url", "")
        cand_lines.append(f'{i}. anchor="{anchor}" url={url}\n   context="{context}"')

    candidates_text = "\n".join(cand_lines)

    return f"""You are a research assistant evaluating whether web links are worth following.

Original query: {query}

What we already know: {knowledge_state or "Nothing yet."}

Candidate links to evaluate:
{candidates_text}

For each candidate, score 0.0-1.0 how likely following this link will provide NEW, RELEVANT information to answer the original query.
- Score > 0.7: definitely follow (directly relevant, likely new info)
- Score 0.4-0.7: maybe follow (somewhat relevant or unclear)
- Score < 0.4: skip (irrelevant, duplicate, or noise)

Respond with ONLY a JSON array, no explanation outside JSON:
[
  {{"id": 1, "score": 0.9, "reason": "one sentence"}},
  {{"id": 2, "score": 0.2, "reason": "one sentence"}},
  ...
]"""


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------
def score_candidates(
    query: str,
    candidates: list,
    knowledge_state: str = "",
    threshold: float = 0.4,
    creds: dict | None = None,
) -> list:
    """Score candidates and return those above threshold."""
    if not candidates:
        return []

    if creds is None:
        creds = _load_creds()

    prompt = _build_prompt(query, knowledge_state, candidates)

    try:
        raw = _call_llm(prompt, creds)
    except Exception as e:
        sys.stderr.write(f"[relevance_gate] LLM call failed: {e}, returning all candidates\n")
        return [dict(c, score=0.5, reason="LLM unavailable") for c in candidates]

    try:
        text = raw.strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:])
            text = text.rstrip("`").strip()
        scores = json.loads(text)
    except json.JSONDecodeError:
        sys.stderr.write(f"[relevance_gate] Failed to parse LLM response: {raw[:200]}\n")
        return [dict(c, score=0.5, reason="parse error") for c in candidates]

    score_map = {item["id"]: item for item in scores if "id" in item}
    result = []
    for i, c in enumerate(candidates, 1):
        s = score_map.get(i, {})
        score = float(s.get("score", 0.5))
        if score >= threshold:
            result.append({**c, "score": score, "reason": s.get("reason", "")})

    result.sort(key=lambda x: x["score"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="LLM relevance gate for chain tracking")
    ap.add_argument("--query", required=True)
    ap.add_argument("--knowledge", default="")
    ap.add_argument("--candidates", required=True,
                    help='JSON array of {"url","anchor","context"} objects')
    ap.add_argument("--threshold", type=float, default=0.4)
    args = ap.parse_args()

    try:
        candidates = json.loads(args.candidates)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid candidates JSON: {e}"}))
        sys.exit(1)

    results = score_candidates(
        query=args.query, candidates=candidates,
        knowledge_state=args.knowledge, threshold=args.threshold,
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
