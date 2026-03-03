# search-skills

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin providing **multi-source search** and **intelligent content extraction**, designed to replace the built-in `WebSearch` and `WebFetch` tools.

Based on [openclaw-search-skills](https://github.com/blessonism/openclaw-search-skills), adapted for Claude Code's plugin architecture.

## Features

- **5-source parallel search**: Brave + Exa + Tavily + Grok + Twitter (Twitter is opt-in)
- **Intent-aware scoring**: 7 intent types with adaptive weights
- **Smart content extraction**: trafilatura probe with MinerU / Tavily Extract / Exa Contents fallback
- **Thread pulling**: Recursive reference tracking for GitHub issues, HN, Reddit, V2EX
- **Hook-based interception**: Transparently replaces `WebSearch` / `WebFetch`

## How It Works

This plugin uses **PreToolUse hooks** to intercept `WebSearch` and `WebFetch` calls. When intercepted, the hook denies the tool call and provides a ready-to-use Bash command that runs the corresponding Python script. Claude then executes the script via Bash to get results.

No MCP server is needed.

## Installation

```bash
# In Claude Code, add the marketplace and install
/plugin marketplace add liunice/claude-code-plugins
/plugin install search-skills@liunice-plugins
```

After installation, run the setup command to configure API keys and install Python dependencies:

```bash
/search-skills:setup
```

Restart Claude Code to activate the hooks.

## Environment Variables

API keys are configured in `~/.claude/settings.json` under the `env` field:

```json
{
  "env": {
    "BRAVE_API_KEY": "your-key",
    "TAVILY_API_KEY": "your-key"
  }
}
```

Run `/search-skills:setup` for guided configuration, or see `.env.example` for the full variable reference.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BRAVE_API_KEY` | At least one of four | — | [Brave Search API](https://brave.com/search/api/) key |
| `EXA_API_KEY` | At least one of four | — | [Exa](https://exa.ai) API key |
| `TAVILY_API_KEY` | At least one of four | — | [Tavily](https://tavily.com) API key |
| `GROK_API_KEY` | At least one of four | — | [xAI Grok](https://docs.x.ai/docs/overview) API key |
| `GROK_API_URL` | No | `https://api.x.ai/v1` | Grok API base URL (OpenAI-compatible endpoint) |
| `GROK_MODEL` | No | `grok-4.20-beta` | Grok model name |
| `TWITTER_API_KEY` | No (opt-in) | — | [twitterapi.io](https://twitterapi.io) API key (NOT the official X/Twitter API) |
| `GROK_TIMEOUT` | No | `120` | Grok API request timeout in seconds |
| `SEARCH_TIMEOUT` | No | `30` | Brave/Exa/Tavily API request timeout in seconds |
| `MINERU_TOKEN` | No | — | [MinerU](https://mineru.net/apiManage) bearer token (for anti-crawl/PDF scenarios) |

> **Note:** At least one standard search source API key (Brave/Exa/Tavily/Grok) must be configured. Sources without keys are silently skipped. Twitter is opt-in and cannot serve as the sole source.

> **Note:** Grok uses the [OpenAI-compatible Chat Completions API](https://docs.x.ai/docs/guides/using_openai_sdk). Any OpenAI-compatible endpoint can be used by setting `GROK_API_URL`.

> **Note:** Twitter is an **opt-in** source — it never runs by default. Use `--source twitter` to explicitly include it. The API key is from [twitterapi.io](https://twitterapi.io), a third-party service, NOT the official X/Twitter API.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/search-layer/search.py` | Multi-source search with intent-aware scoring |
| `scripts/search-layer/twitter_search.py` | Twitter/X operations: tweet search, user tweets (via [twitterapi.io](https://twitterapi.io)) |
| `scripts/search-layer/fetch_thread.py` | Deep thread fetcher (GitHub, HN, Reddit, V2EX, web) |
| `scripts/search-layer/chain_tracker.py` | Recursive reference chain tracker |
| `scripts/search-layer/relevance_gate.py` | LLM-based relevance scoring for chain tracking |
| `scripts/content-extract/content_extract.py` | URL → Markdown with trafilatura + MinerU/Tavily/Exa fallback |
| `scripts/mineru-extract/mineru_extract.py` | MinerU API single-URL extractor |
| `scripts/mineru-extract/mineru_parse_documents.py` | MinerU API batch extractor |

> **Note:** `chain_tracker.py` depends on `relevance_gate.py`, which uses Grok as the LLM to score link relevance. `GROK_API_KEY` is required for recursive reference tracking to work properly. Without it, the relevance gate falls back to returning all candidates unscored. `fetch_thread.py` works independently and does not require Grok.

## Search Modes

The `search.py` script supports three search modes, automatically selected based on query intent:

| Mode | Behavior | Use case |
|------|----------|----------|
| `fast` | Single source only (exa > brave > grok) | Quick resource lookups, finding official docs/sites |
| `deep` | All configured standard sources in parallel; opt-in sources (e.g. Twitter) only with explicit `--source` | Research, comparisons, status updates, news (default) |
| `answer` | Tavily only, with AI-generated answer | Factual questions, how-to queries |

The `search-layer` skill classifies query intent and picks the appropriate mode automatically. See `skills/search-layer/SKILL.md` for the full intent → mode mapping.

## Skills

| Skill | Description |
|-------|-------------|
| `search-layer` | Full search protocol: intent classification → query expansion → multi-source retrieval → scoring → synthesis |
| `content-extract` | URL content extraction decision tree: whitelist → probe → MinerU / Tavily / Exa fallback |
| `mineru-extract` | MinerU API usage: model selection, parameters, output handling |

## Upstream

Based on [openclaw-search-skills](https://github.com/blessonism/openclaw-search-skills), commit [`0c9c987`](https://github.com/blessonism/openclaw-search-skills/commit/0c9c9870e45729602ffa81612c2f95914bf39d4d) (2026-02-28).

## License

MIT
