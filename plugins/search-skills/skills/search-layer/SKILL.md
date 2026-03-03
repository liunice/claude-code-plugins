---
name: search-layer
description: >
  DEFAULT search tool for ALL search/lookup needs. Multi-source search (Brave+Exa+Tavily+Grok+Twitter)
  with intent-aware scoring and deduplication. Automatically classifies query intent and adjusts
  search strategy, scoring weights, and result synthesis. Use for ANY query that requires web
  search — factual lookups, research, news, comparisons, resource finding, status checks, etc.
  Twitter is an opt-in source for X/Twitter content (requires --source twitter).
  Do NOT use WebSearch directly; always route through this skill.
---

# Search Layer — Intent-Aware Multi-Source Search Protocol

Five search sources: Brave + Exa + Tavily + Grok + Twitter. Selects strategy, adjusts weights, and synthesizes by intent. Twitter is opt-in only.

## Execution Flow

```
User query
    |
[Phase 1] Intent classification -> determine search strategy
    |
[Phase 2] Query decomposition & expansion -> generate sub-queries
    |
[Phase 3] Multi-source parallel search -> search.py / twitter_search.py
    ├── [3.1] Twitter/X operations (when targeting X content)
    └── [3.2] Reference tracking (when results contain thread links)
    |
[Phase 4] Ranking & synthesis -> dedup + scoring + structured output
```

> Jump to [Quick Reference](#quick-reference) for common commands.

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

**Twitter/X query detection:** When the query specifically targets X/Twitter content (signal words: `x.com`, `twitter`, `tweet`, `trending on X`), use `twitter_search.py` directly — see "Phase 3.1: Twitter/X Operations" below. Do NOT route through `search.py`; the Phase 3.1 workflows are self-contained.

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

### Twitter query optimization

When expanding queries for Twitter (via `twitter_search.py search` or `search.py --source twitter`), **combine variants with the `OR` operator** in a single query instead of making separate API calls. This reduces paid API usage.

```
# Bad: 2 API calls
twitter_search.py search "GPT 5.4" --num 5
twitter_search.py search "GPT-5.4" --num 5

# Good: 1 API call with OR
twitter_search.py search "\"GPT 5.4\" OR \"GPT-5.4\"" --num 5
```

Use OR for: spelling variants, synonyms, abbreviations (e.g. `"k8s" OR "Kubernetes"`), version number formats (e.g. `"5.4" OR "5-4"`).

---

## Phase 3: Multi-Source Parallel Search

Run search.py with appropriate parameters. **Always set Bash timeout to 600000ms (10 min)** — search.py manages per-source timeouts internally; the Bash timeout is only a safety net to avoid premature termination.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/search-layer/search.py \
  --queries "sub-query-1" "sub-query-2" "sub-query-3" \
  --mode deep \
  --intent status \
  --freshness pw \
  --num 5
```

**Source participation by mode:**

| Mode | Brave | Exa | Tavily | Grok | Twitter | Notes |
|------|-------|-----|--------|------|---------|-------|
| fast | fallback | preferred | - | fallback | - | Single source: exa > brave > grok (Tavily reserved for answer mode) |
| deep | yes | yes | yes | yes | opt-in | All configured sources in parallel; Twitter only with `--source twitter` |
| answer | - | - | yes | - | - | Tavily only (includes AI answer) |

**Parameters:**

| Parameter | Description |
|-----------|-------------|
| `--queries` | Multiple sub-queries in parallel |
| `--mode` | fast / deep / answer |
| `--intent` | Intent type for scoring weights |
| `--freshness` | pd(24h) / pw(week) / pm(month) / py(year) |
| `--domain-boost` | Comma-separated domains to boost (+0.2 authority) |
| `--source` | Comma-separated source filter (brave,exa,tavily,grok,twitter). Only listed sources run. Opt-in sources like twitter require explicit inclusion |
| `--twitter-max-queries` | Max Twitter API calls per invocation (default: 3, controls cost) |
| `--num` | Results per source per query |

**Grok source notes:**
- Uses OpenAI-compatible Chat Completions API (default endpoint: `https://api.x.ai/v1`)
- Default model: `grok-4.20-beta`
- Auto-detects time-sensitive queries and injects current time context
- If GROK_API_KEY is not set, Grok source is silently skipped

**Timeout environment variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARCH_TIMEOUT` | 30 (seconds) | Per-request timeout for Brave, Exa, Tavily, Twitter |
| `GROK_TIMEOUT` | 120 (seconds) | Per-request timeout for Grok (LLM calls are slower) |

Both values must stay under 600s — the Bash tool has a hard ceiling of 10 minutes, and the slowest source determines total runtime.

**Twitter source in search.py (deep mode):**
- **Opt-in only**: never runs unless explicitly requested via `--source twitter`
- Delegates to `twitter_search.py` module internally
- Paid API — use `--twitter-max-queries N` (default 3) to control cost per invocation

### Degradation strategy

- Any single source fails -> continue with remaining sources
- search.py entirely fails -> inform user and suggest retrying
- **Never block the main flow because one source fails**

### Phase 3.1: Twitter/X Operations

For queries targeting X/Twitter content, use `twitter_search.py` directly.

**IMPORTANT — single-call principle:** Each scenario below maps to exactly **one** `twitter_search.py` call (except the two-phase "Get a specific account's tweets" which uses one `search.py` + one `twitter_search.py`). Rules:
- After the call returns, synthesize and present results **immediately**. Do NOT retry with different keywords, broader date ranges, or alternative query variants.
- Do NOT make additional `search.py`, Grok, or any other calls to "supplement" or "add context".
- If results seem sparse, present what was returned — do not chase more data.
- Only use other sources if the user **explicitly** asks for web results alongside Twitter results.

**Scenario routing:**

| Scenario | Example | Workflow |
|----------|---------|----------|
| **Get a specific account's tweets** | "OpenAI latest tweet", "what did Elon Musk post on X" | Two-phase: (1) find handle via regular web search (search.py), (2) call `user-tweets` |
| **Get a specific account's tweets with time/keyword filter** | "OpenAI tweets in last 24h", "Elon Musk's tweets about AI" | Single-phase: call `search` with `--from` (+ `--within` and/or keyword) |
| **Search tweet content by keyword** | "AI trending on X", "tweets about GPT-5" | Single-phase: call `search` directly |
| **Get trending topics** | "Twitter trends", "trending on X", "what's hot on X" | Single-phase: call `trends` directly |
| **Get top tweets in a region** | "top tweets in US", "most popular tweets in Japan" | Two-phase: (1) `trends` with woeid to get topic names, (2) `search` with those topics |

**Routing hints — `user-tweets` vs `search --from`:**
- **`user-tweets` does NOT support time or keyword filtering.** It only returns the N most recent tweets.

| Need | Use | Why |
|------|-----|-----|
| Latest tweets from a user (no filtering) | `user-tweets` | Timeline endpoint, chronological order |
| A user's tweets about a specific topic | `search --from` | Supports keyword filtering |
| A user's tweets within a time range | `search --from` | Supports `--within` for relative time |
| A user's tweets including replies | `user-tweets --include-replies` | Only `user-tweets` supports this |

**Routing hints — `trends` vs `search`:**
- **`trends` returns topic names, NOT actual tweets.** Use it to discover what's trending, then follow up with `search` if the user wants actual tweet content.
- When the user asks for "popular/hot/trending" **tweets** in a location without a specific keyword, use the two-phase workflow: (1) call `trends --woeid {id}` to get trending topic names, (2) combine the top topic names with `OR` into a single `search` call with `--query-type Top`.
- When the user asks for tweets **about a specific topic** (e.g. "popular tweets about AI"), use `search` with `--query-type Top` directly — no need for `trends`.

#### twitter_search.py subcommands

```bash
# Search tweets by keyword (last 24 hours)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/search-layer/twitter_search.py \
  search "AI news" --within 24h --num 5

# Search a specific author's tweets about a topic (last 30 days)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/search-layer/twitter_search.py \
  search "GPT-5" --from openai --within 30d

# Get a user's latest tweets (by handle)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/search-layer/twitter_search.py \
  user-tweets --username openai --num 1

# Get trending topics (worldwide by default)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/search-layer/twitter_search.py \
  trends --num 5

# Get trending topics for a specific location (US)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/search-layer/twitter_search.py \
  trends --woeid 23424977 --num 10
```

**`search` parameters:**

| Parameter | Description |
|-----------|-------------|
| `query` (positional) | Search keywords |
| `--from` | Filter by author handle (without @) |
| `--within` | Relative time window: `24h`, `7d`, `30d`, etc. Maps to Twitter's `within_time:` operator |
| `--query-type` | Latest (default) / Top |
| `--num` | Max results (default: 5, API max: 20) |

**`user-tweets` parameters:**

| Parameter | Description |
|-----------|-------------|
| `--username` | Twitter handle, without @ (required) |
| `--include-replies` | Include replies (default: exclude) |
| `--num` | Max results (default: 5) |

**`trends` parameters:**

| Parameter | Description |
|-----------|-------------|
| `--woeid` | Where On Earth ID (default: 1 = Worldwide) |
| `--num` | Max trends to return (default: 5) |

**Common woeid values**: Worldwide (1), US (23424977), UK (23424975), Japan (23424856), China (23424748). See `references/woeid-table.md` for the full table.

**Two-phase workflow example** ("get OpenAI's latest tweet"):

```
Phase 1 — Find the handle (use regular web sources, NOT Twitter API):
  search.py "OpenAI official X Twitter account" --mode fast → extract handle from results

Phase 2 — Get tweets (use Twitter API):
  twitter_search.py user-tweets --username OpenAI --num 1
```

**Two-phase workflow example** ("top 5 tweets in China"):

```
Phase 1 — Get trending topics (use Twitter API):
  twitter_search.py trends --woeid 23424748 --num 5
  → extracts topic names, e.g. ["TopicA", "TopicB", "TopicC", ...]

Phase 2 — Search top tweets for those topics (use Twitter API):
  twitter_search.py search "TopicA OR TopicB OR TopicC" --query-type Top --within 24h --num 5
```

**Important notes:**
- Uses [twitterapi.io](https://twitterapi.io) API (NOT the official X/Twitter API). Requires `TWITTER_API_KEY`.
- Paid API — minimize calls. When the handle is already known or can be confidently inferred, skip Phase 1 and call `user-tweets` directly.
- **Combine query variants with `OR`** to reduce API calls (see Phase 2 "Twitter query optimization").
- Each call returns up to 20 results (one page, no pagination).

**Fallback when `TWITTER_API_KEY` is not configured:**
When `twitter_search.py` fails (missing API key, API error, etc.), fall back to `search.py --mode deep` with `--domain-boost x.com` to prioritize X/Twitter content in ranking. Do NOT add `site:x.com` to the query. Follow the same single-call principle — present whatever results are returned without additional retry.

---

### Phase 3.2: Reference Tracking (Thread Pulling)

**When to use:** After Phase 2 search completes, if the results contain discussion thread URLs (GitHub issues/PRs, HN, Reddit, V2EX) **and** the intent is Status or Exploratory, add `--extract-refs` to fetch and extract references from each result. This is not automatic — you must decide to add the flag based on the search results.

#### search.py --extract-refs (batch)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/search-layer/search.py "query" --mode deep --intent status --extract-refs
```

#### fetch_thread.py (single URL deep fetch)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/search-layer/fetch_thread.py "https://github.com/owner/repo/issues/123" --format json
```

Supports: GitHub issues/PRs, HN, Reddit, V2EX, generic web pages.

> Note: `--extract-refs` uses `fetch_thread.py` internally and does not require Grok. For deeper recursive reference chain tracking, use `chain_tracker.py` directly (requires `GROK_API_KEY`).

---

## Phase 4: Ranking & Synthesis

### Scoring formula

```
score = w_keyword * keyword_match + w_freshness * freshness_score + w_authority * authority_score
```

Weights are determined by intent (see Phase 1 table).

> See `references/authority-domains.json` for the full domain scoring table.

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

### Twitter API result display

When results include Twitter data, the `title` field contains engagement metrics: `👀 views ｜👍 likes ｜🔁 retweets`. **Always display these metrics** alongside each tweet in the output, e.g.:

```
- @username: "tweet content..." (👀 36.2K ｜👍 576 ｜🔁 66)
  https://x.com/username/status/123
```

Twitter results have `published_date` in UTC (e.g. `2026-02-27T13:31:31Z`). Convert to the user's local timezone when displaying.

### Content synthesis

- **Answer first, then sources** (don't start with "I searched...")
- **Group by topic, not by source**
- **Flag conflicting info** from different sources
- **Confidence expression**: multi-source agreement -> direct statement; single source -> cite it; conflict -> present both

---

## Quick Reference

| Scenario | Command |
|----------|---------|
| Quick fact | `search.py "query" --mode answer --intent factual` |
| Deep research | `search.py "query" --mode deep --intent exploratory` |
| Latest updates | `search.py "query" --mode deep --intent status --freshness pw` |
| Comparison | `search.py --queries "A vs B" "A pros" "B pros" --intent comparison` |
| Find resource | `search.py "query" --mode fast --intent resource` |
| Twitter: keyword search | `twitter_search.py search "AI news" --within 24h --num 5` |
| Twitter: author + topic | `twitter_search.py search "GPT-5" --from openai` |
| Twitter: user's latest | `twitter_search.py user-tweets --username openai --num 1` |
| Twitter: trending topics | `twitter_search.py trends --woeid 1 --num 5` |
