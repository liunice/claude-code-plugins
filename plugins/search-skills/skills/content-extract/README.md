# content-extract

Intelligent URL content extraction skill for the [search-skills](../../README.md) plugin. Converts any URL into clean text/Markdown through a multi-layer extraction pipeline with automatic fallback.

## Decision Tree

```mermaid
flowchart TD
    A[URL input] --> B{Binary file?<br/>PDF/Office/image}
    B -- yes --> M1[MinerU<br/>preserves structure]
    M1 -- ok --> R1([return])
    M1 -- fail --> T

    B -- no --> C{Domain whitelist?<br/>WeChat/Zhihu/etc}
    C -- yes --> M2[MinerU]
    M2 -- ok --> R2([return])
    M2 -- fail --> P

    C -- no --> P[Probe: trafilatura / bs4 / regex]
    P -- pass --> R3([return])
    P -- fail --> T

    T[Tavily Extract<br/>cloud rendering] -- ok --> R4([return])
    T -- fail --> E[Exa Contents<br/>cache + live crawl]
    E -- ok --> R5([return])
    E -- fail --> D{MinerU already<br/>tried?}
    D -- no --> M3[MinerU<br/>last resort]
    M3 -- ok --> R6([return])
    M3 -- fail --> ERR([error])
    D -- yes --> ERR
```

## Extraction Paths

| URL Type | Fallback Order | Rationale |
|----------|----------------|-----------|
| **Binary files** (PDF, Office, images) | MinerU → Tavily → Exa | MinerU preserves document structure (tables, formulas, OCR) |
| **Whitelisted domains** (WeChat, Zhihu, etc.) | MinerU → Probe → Tavily → Exa | These anti-crawl sites are specifically optimized for MinerU |
| **Normal URLs** | Probe → Tavily → Exa → MinerU | Free/fast probe first; cloud rendering for anti-crawl; MinerU as last resort |

## Extraction Methods

| Method | Type | Speed | Cost | Best For |
|--------|------|-------|------|----------|
| **Probe** (trafilatura / bs4 / regex) | Local | Fastest | Free | Standard HTML pages |
| **Tavily Extract** | Cloud API | Fast | Paid | Anti-crawl / JS-rendered pages |
| **Exa Contents** | Cloud API | Fast (cached) | Paid | Indexed pages; live crawl fallback |
| **MinerU** | Cloud API | Slow (async polling) | Paid | PDFs, Office docs, OCR, table extraction |

## Design Decisions

- **Probe first for normal URLs**: Most pages are standard HTML. Using the free local extractor avoids unnecessary API calls.
- **MinerU first for binary/whitelisted**: MinerU produces the highest-quality output for documents (preserving structure, tables, and formulas) and for specific anti-crawl sites it's been optimized for.
- **MinerU last for normal URLs**: When probe fails on a normal URL (typically due to anti-crawl), cloud rendering services (Tavily/Exa) are faster and better suited than MinerU's document parsing engine.
- **No duplicate MinerU calls**: If MinerU was already tried in the binary/whitelist step, it's skipped in the fallback chain.

## Anti-Crawl Detection

The probe step includes heuristic checks that trigger fallback:

1. **Keyword detection** — Response contains known anti-crawl phrases (e.g., "enable javascript", "checking your browser", "captcha")
2. **Minimum length** — Extracted content shorter than 800 characters is considered incomplete

See [`references/heuristics.md`](../../references/heuristics.md) for the full keyword list.

## Domain Whitelist

Certain domains always skip the probe and go directly to MinerU, because they are known to require server-side rendering:

- `mp.weixin.qq.com` — WeChat articles
- `zhihu.com` / `zhuanlan.zhihu.com` — Zhihu
- `xiaohongshu.com` / `xhslink.com` — Xiaohongshu
- `bilibili.com` — Bilibili

See [`references/domain-whitelist.md`](../../references/domain-whitelist.md) for the full list. The whitelist is loaded at runtime and can be extended without code changes.

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition loaded by Claude Code (usage examples, output contract) |
| [`../../scripts/content-extract/content_extract.py`](../../scripts/content-extract/content_extract.py) | Main extraction script with all extraction methods and fallback logic |

## Environment Variables

All API keys are optional. The script uses whichever services are configured and skips the rest.

| Variable | Used By |
|----------|---------|
| `TAVILY_API_KEY` | Tavily Extract API |
| `EXA_API_KEY` | Exa Contents API |
| `MINERU_TOKEN` | MinerU parsing API |

## Dependencies

- `requests` — HTTP client
- `trafilatura` — Primary content extractor
- `beautifulsoup4` + `lxml` — Fallback extractor
