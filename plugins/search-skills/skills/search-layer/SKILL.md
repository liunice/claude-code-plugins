---
name: search-layer
description: >
  DEFAULT search tool for ALL search/lookup needs. Multi-source search (Brave+Exa+Tavily+Grok)
  with intent-aware scoring and deduplication. Automatically classifies query intent and adjusts
  search strategy, scoring weights, and result synthesis. Use for ANY query that requires web
  search — factual lookups, research, news, comparisons, resource finding, status checks, etc.
  Do NOT use WebSearch directly; always route through this skill.
---

# Search Layer — Intent-Aware Multi-Source Search Protocol

Four search sources: Brave + Exa + Tavily + Grok. Selects strategy, adjusts weights, and synthesizes by intent.

## Execution Flow

```
User query
    |
[Phase 1] Intent classification -> determine search strategy
    |
[Phase 2] Query decomposition & expansion -> generate sub-queries
    |
[Phase 3] Multi-source parallel search -> search.py (Brave+Exa+Tavily+Grok)
    |
[Phase 4] Merge & rank -> dedup + intent-weighted scoring
    |
[Phase 5] Knowledge synthesis -> structured output
```

---

## Phase 1: Intent Classification

After receiving a search request, **classify intent first**, then decide search strategy.

| Intent | Signal words | Mode | Freshness | Weight bias |
|--------|-------------|------|-----------|-------------|
| **Factual** | "what is X", "definition of X" | answer | — | authority 0.5 |
| **Status** | "latest X", "X progress", "X update" | deep | pw/pm | freshness 0.5 |
| **Comparison** | "X vs Y", "X compared to Y" | deep | py | keyword 0.4 + authority 0.4 |
| **Tutorial** | "how to X", "X tutorial", "X guide" | answer | py | authority 0.5 |
| **Exploratory** | "about X", "X ecosystem", "deep dive X" | deep | — | authority 0.5 |
| **News** | "X news", "this week X" | deep | pd/pw | freshness 0.6 |
| **Resource** | "X official site", "X GitHub", "X docs" | fast | — | keyword 0.5 |

> See `references/intent-guide.md` for detailed classification guide.

---

## Phase 2: Query Decomposition & Expansion

### General rules
- **Tech synonyms**: k8s->Kubernetes, JS->JavaScript, Go->Golang, Postgres->PostgreSQL
- **Chinese tech queries**: also generate English variants

### By intent

| Intent | Expansion strategy | Example |
|--------|-------------------|---------|
| Factual | Add "definition", "explained" | "WebTransport" -> + "WebTransport explained overview" |
| Status | Add year, "latest", "update" | "Deno progress" -> + "Deno 2.0 latest 2026" |
| Comparison | Split into 3 sub-queries | "Bun vs Deno" -> "Bun vs Deno", "Bun advantages", "Deno advantages" |
| Tutorial | Add "tutorial", "guide", "step by step" | "Rust CLI" -> + "Rust CLI tutorial guide" |
| Exploratory | Split into 2-3 angles | "RISC-V" -> "RISC-V overview", "RISC-V ecosystem", "RISC-V use cases" |
| News | Add "news", "announcement", date | "AI news" -> + "AI news this week 2026" |
| Resource | Add resource type | "Anthropic MCP" -> + "Anthropic MCP official documentation" |

---

## Phase 3: Multi-Source Parallel Search

Run search.py with appropriate parameters:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/search-layer/search.py \
  --queries "sub-query-1" "sub-query-2" "sub-query-3" \
  --mode deep \
  --intent status \
  --freshness pw \
  --num 5
```

**Source participation by mode:**

| Mode | Brave | Exa | Tavily | Grok | Notes |
|------|-------|-----|--------|------|-------|
| fast | fallback | preferred | - | fallback | Single source: exa > brave > grok (Tavily reserved for answer mode) |
| deep | yes | yes | yes | yes | All configured sources in parallel |
| answer | - | - | yes | - | Tavily only (includes AI answer) |

**Parameters:**

| Parameter | Description |
|-----------|-------------|
| `--queries` | Multiple sub-queries in parallel |
| `--mode` | fast / deep / answer |
| `--intent` | Intent type for scoring weights |
| `--freshness` | pd(24h) / pw(week) / pm(month) / py(year) |
| `--domain-boost` | Comma-separated domains to boost (+0.2 authority) |
| `--source` | Comma-separated source filter (brave,exa,tavily,grok) |
| `--num` | Results per source per query |

**Grok source notes:**
- Uses OpenAI-compatible Chat Completions API (default endpoint: `https://api.x.ai/v1`)
- Default model: `grok-4.20-beta`
- Auto-detects time-sensitive queries and injects current time context
- If GROK_API_KEY is not set, Grok source is silently skipped

---

## Phase 3.5: Reference Tracking (Thread Pulling)

When results contain GitHub issue/PR links and intent is Status or Exploratory, auto-trigger reference tracking.

### search.py --extract-refs (batch)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/search-layer/search.py "query" --mode deep --intent status --extract-refs
```

### fetch_thread.py (single URL deep fetch)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/search-layer/fetch_thread.py "https://github.com/owner/repo/issues/123" --format json
```

Supports: GitHub issues/PRs, HN, Reddit, V2EX, generic web pages.

---

## Phase 4: Result Ranking

### Scoring formula

```
score = w_keyword * keyword_match + w_freshness * freshness_score + w_authority * authority_score
```

Weights are determined by intent (see Phase 1 table).

> See `references/authority-domains.json` for the full domain scoring table.

---

## Phase 5: Knowledge Synthesis

### Sources summary (MUST display)

Before presenting results, **always** display the `sources` field from the JSON output as a brief summary table or list showing:
- Which platforms were queried
- Status of each (ok / error / no_key / skipped)
- Number of results returned per platform
- Time elapsed per platform (seconds)

Example format:
```
Search sources: Brave (5 results, 1.2s) | Exa (5 results, 2.1s) | Tavily (5 results, 0.9s) | Grok (error: timeout, 60.0s)
```

### Content synthesis

- **Answer first, then sources** (don't start with "I searched...")
- **Group by topic, not by source**
- **Flag conflicting info** from different sources
- **Confidence expression**: multi-source agreement -> direct statement; single source -> cite it; conflict -> present both

---

## Degradation Strategy

- Any single source fails -> continue with remaining sources
- search.py entirely fails -> inform user and suggest retrying
- **Never block the main flow because one source fails**

---

## Quick Reference

| Scenario | Command |
|----------|---------|
| Quick fact | `search.py "query" --mode answer --intent factual` |
| Deep research | `search.py "query" --mode deep --intent exploratory` |
| Latest updates | `search.py "query" --mode deep --intent status --freshness pw` |
| Comparison | `search.py --queries "A vs B" "A pros" "B pros" --intent comparison` |
| Find resource | `search.py "query" --mode fast --intent resource` |
