---
name: content-extract
description: >
  Intelligent URL content extraction. Converts any URL to clean text/markdown using
  a multi-layer approach: trafilatura fast probe -> Tavily Extract -> Exa Contents
  -> MinerU API. Handles anti-crawl sites (WeChat, Zhihu, Xiaohongshu, Cloudflare-protected)
  and binary files (PDF, Office docs) automatically.
  Do NOT use WebFetch directly; always route through this skill.
---

# Content Extract — Intelligent URL -> Text/Markdown

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
  "error": "Probe: Anti-crawl page detected; Tavily: ...; Exa: ...; MinerU: ..."
}
```

## Key Behaviors

- **Normal URLs**: Automatically tries multiple extraction methods in sequence until one succeeds.
- **Binary files** (PDF, Office, images): Prioritizes MinerU for structure-preserving extraction.
- **Anti-crawl sites** (WeChat, Zhihu, Cloudflare-protected): Automatically detected and routed to cloud-based extractors.
- All fallback logic is handled internally — just pass the URL and read the result.
