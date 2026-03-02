---
name: mineru-extract
description: >
  Use the official MinerU (mineru.net) parsing API to convert a URL (HTML pages like WeChat
  articles, or direct PDF/Office/image links) into clean Markdown + structured outputs.
  Use when web fetch/browser can't access or extracts messy content, and you want
  higher-fidelity parsing (layout/table/formula/OCR).
---

# MinerU Extract (Official API)

Use MinerU as an upstream "content normalizer": submit a URL to MinerU, poll for completion, download the result zip, and extract the main Markdown.

## Quick Start

### 1. Configure token

Set the `MINERU_TOKEN` environment variable (get it from https://mineru.net/apiManage).

### 2. Parse URL(s) -> Markdown (recommended)

MCP-style wrapper (returns JSON, optionally includes markdown text):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/mineru-extract/mineru_parse_documents.py \
  --file-sources "<URL1>,<URL2>" \
  --language ch \
  --enable-ocr \
  --model-version MinerU-HTML
```

With inline markdown in JSON output:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/mineru-extract/mineru_parse_documents.py \
  --file-sources "<URL>" \
  --model-version MinerU-HTML \
  --emit-markdown --max-chars 20000
```

### 3. Low-level single URL (print to stdout)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/mineru-extract/mineru_extract.py "<URL>" --model MinerU-HTML --print
```

## Model Selection

| URL type | Model | Notes |
|----------|-------|-------|
| `.pdf`, `.doc`, `.ppt`, `.png`, `.jpg` | `pipeline` | Auto-detected |
| HTML pages (WeChat, blogs, etc.) | `MinerU-HTML` | Auto-detected |
| Scanned documents | `vlm` | Manual selection needed |

## Parameters

| Parameter | Description |
|-----------|-------------|
| `--model` | `pipeline` / `vlm` / `MinerU-HTML` (auto-detected if not set) |
| `--ocr` / `--no-ocr` | Enable OCR (effective for pipeline/vlm) |
| `--table` / `--no-table` | Table recognition |
| `--formula` / `--no-formula` | Formula recognition |
| `--language ch\|en\|...` | Document language |
| `--page-ranges "2,4-6"` | Page selection (non-HTML only) |
| `--timeout 600` | Max wait time in seconds |
| `--cache` / `--no-cache` | Enable/disable result caching |

## Output

Results are saved to: `~/.cache/claude-search-skills/mineru-cache/<hash>/`

Contents:
- `<task_id>.zip` — Original MinerU result
- Extracted files (Markdown + JSON + assets)
- `meta.json` — Metadata for caching

## Failure Modes

- MinerU may fail to fetch some URLs (anti-bot / geo / login wall)
- Always report the failing URL + MinerU error message
- Fallback: provide an alternative URL or use content-extract probe layer

## References

- MinerU API docs: https://mineru.net/apiManage/docs
- MinerU output files: https://opendatalab.github.io/MinerU/reference/output_files/
