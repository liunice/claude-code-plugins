---
name: content-extract
description: >
  Intelligent URL content extraction. Converts any URL to clean text/markdown using
  a multi-layer approach: trafilatura fast probe -> heuristics check -> MinerU API fallback.
  Use when you need to read the full content of a web page. Handles anti-crawl sites
  (WeChat, Zhihu, Xiaohongshu) and binary files (PDF, Office docs) automatically.
  Do NOT use WebFetch directly; always route through this skill.
---

# Content Extract — Intelligent URL -> Text/Markdown

## Decision Tree

```
URL input
    |
[1] Binary file? (PDF/Office/image) --yes--> MinerU directly
    |no
[2] Domain whitelist? (WeChat/Zhihu/etc) --yes--> MinerU directly
    |no
[3] Probe: requests + trafilatura
    |
[4] Heuristics check:
    - Anti-crawl keywords detected? -> fail
    - Content < 800 chars? -> fail
    |pass
    Return content
    |fail
[5] MINERU_TOKEN configured? --yes--> MinerU fallback
    |no
    Return error with probe failure reason
```

## Usage

```bash
# Standard extraction (auto-detects best method)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/content-extract/content_extract.py --url "https://example.com/article"

# Anti-crawl site (auto-routes to MinerU if token configured)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/content-extract/content_extract.py --url "https://mp.weixin.qq.com/s/xxx"

# PDF/binary file
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/content-extract/content_extract.py --url "https://example.com/paper.pdf"

# Force specific MinerU model
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/content-extract/content_extract.py --url "https://example.com" --mineru-model MinerU-HTML

# Limit output length
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/content-extract/content_extract.py --url "https://example.com" --max-chars 10000
```

## Output Contract

```json
{
  "ok": true,
  "url": "https://...",
  "title": "Page Title",
  "content": "Extracted text content...",
  "content_length": 5432,
  "method": "trafilatura",
  "fallback_used": false
}
```

On failure:
```json
{
  "ok": false,
  "url": "https://...",
  "error": "Probe: Anti-crawl page detected; MinerU: MINERU_TOKEN not configured"
}
```

## Domain Whitelist

Sites that always route to MinerU (anti-crawl / JS-rendered):
- `mp.weixin.qq.com` — WeChat articles
- `zhihu.com` / `zhuanlan.zhihu.com` — Zhihu
- `xiaohongshu.com` / `xhslink.com` — Xiaohongshu
- `bilibili.com` — Bilibili

> See `references/domain-whitelist.md` for the full list.

## Anti-Crawl Heuristics

Probe extraction is considered failed if:
1. Response contains anti-crawl keywords (CAPTCHA, "enable javascript", etc.)
2. Extracted content is shorter than 800 characters

> See `references/heuristics.md` for the full heuristics reference.

## Extraction Layers

| Layer | Method | When used |
|-------|--------|-----------|
| 1 | trafilatura | Primary extractor, best for article-style pages |
| 2 | BeautifulSoup | Fallback when trafilatura extracts < 200 chars |
| 3 | Regex strip | Last resort when BS4 is unavailable |
| 4 | MinerU API | Anti-crawl/binary fallback (requires MINERU_TOKEN) |

## Dependencies

- `requests` — HTTP client
- `trafilatura` — Primary content extractor
- `beautifulsoup4` + `lxml` — Fallback extractor
- `MINERU_TOKEN` env var — Optional, for MinerU fallback
