---
name: content-extract
description: >
  Intelligent URL content extraction. Converts any URL to clean text/markdown using
  a multi-layer approach: trafilatura fast probe -> Exa Contents -> Tavily Extract
  -> MinerU API. Handles anti-crawl sites (WeChat, Zhihu, Xiaohongshu, Cloudflare-protected)
  and binary files (PDF, Office docs) automatically.
  Do NOT use WebFetch directly; always route through this skill.
---

# Content Extract — Intelligent URL -> Text/Markdown

## Core Principles

- **Unified entry point**: All URL-to-text extraction goes through this skill. Never call WebFetch directly.
- **Cost-aware probing**: Try the free local probe first; only call paid cloud APIs when probe fails.
- **Traceable results**: Always return the source URL and extraction method used.
- **Graceful failure**: When all methods fail, return structured error with all failure reasons — never raw exceptions.

## Workflow

Input: `url`

**Step 1 — Binary file detection**

If URL ends with `.pdf`, `.docx`, `.pptx`, etc., skip probe and go directly to MinerU (best for preserving document structure).

**Step 2 — Domain whitelist (skip probe)**

If URL matches a whitelisted domain (WeChat, Zhihu, etc.), skip probe and go directly to MinerU.

- Whitelist file: `references/domain-whitelist.md`
- Whitelisted URLs use `model_version=MinerU-HTML`

**Step 3 — Probe (free, fastest)**

Use `requests` + trafilatura/bs4/regex to extract content locally.

- Failure conditions (handled automatically):
  - HTTP 403/401/5xx
  - Anti-crawl keywords detected (captcha, "enable javascript", etc.)
  - Content shorter than 800 characters

**Step 4 — Exa Contents**

Cache-first with live crawl fallback. Better for anti-crawl pages. Requires `EXA_API_KEY`.

**Step 5 — Tavily Extract**

Cloud rendering for JS-rendered pages. Requires `TAVILY_API_KEY`.

**Step 6 — MinerU (last resort)**

Skip if already tried in Step 1/2. Requires `MINERU_TOKEN`.

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

Success:
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

Failure:
```json
{
  "ok": false,
  "url": "https://...",
  "error": "Probe: Anti-crawl page detected; Exa: ...; Tavily: ...; MinerU: ..."
}
```

## Delivery Rules

- Output must always include the source `url` and `method` used.
- If all extraction methods fail, return `ok: false` with aggregated error reasons.
- Do NOT attempt to bypass login walls or CAPTCHAs — this skill handles parsing and routing only.
- If extraction fails for a protected page, suggest alternatives (e.g., user provides accessible URL, or use browser automation as last resort).

## References

- Domain whitelist: `references/domain-whitelist.md`
