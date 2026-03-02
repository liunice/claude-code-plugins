#!/usr/bin/env python3
"""
Intelligent content extraction: URL -> clean Markdown/text.

Decision tree:
  1. Check domain whitelist -> if match, go directly to MinerU
  2. probe_url(): use requests + trafilatura.extract() to get body text
  3. Apply heuristics (anti-crawl keyword detection, minimum length 800 chars)
  4. If probe fails + MINERU_TOKEN is set -> fallback to MinerU
  5. Return unified JSON result contract

This is a complete replacement for WebFetch / Tavily extract.

Usage:
  python3 content_extract.py --url "https://example.com"
  python3 content_extract.py --url "https://mp.weixin.qq.com/s/xxx"
  python3 content_extract.py --url "https://example.com/paper.pdf" --mineru-model pipeline

Based on openclaw-search-skills (https://github.com/blessonism/openclaw-search-skills).
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print('{"error": "requests library not installed. Run: pip3 install requests"}',
          file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Domain whitelist: sites that always need MinerU (anti-crawl / JS-rendered)
# ---------------------------------------------------------------------------
_WHITELIST_PATH = Path(__file__).parent.parent.parent / "references" / "domain-whitelist.md"

_DEFAULT_WHITELIST = {
    "mp.weixin.qq.com",
    "weixin.qq.com",
    "zhihu.com",
    "zhuanlan.zhihu.com",
    "xiaohongshu.com",
    "xhslink.com",
    "bilibili.com",
}


def _load_whitelist() -> set:
    """Load domain whitelist from references file, with built-in fallback."""
    domains = set(_DEFAULT_WHITELIST)
    if _WHITELIST_PATH.exists():
        try:
            for line in _WHITELIST_PATH.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    # Handle markdown list items: "- domain.com" or "* domain.com"
                    cleaned = re.sub(r'^[-*]\s*', '', line).strip()
                    # Handle markdown bold/code: "**domain.com**" or "`domain.com`"
                    cleaned = re.sub(r'[*`]', '', cleaned).strip()
                    if cleaned and "." in cleaned and " " not in cleaned:
                        domains.add(cleaned)
        except Exception:
            pass
    return domains


def _is_whitelisted(url: str) -> bool:
    """Check if a URL's domain matches the whitelist."""
    whitelist = _load_whitelist()
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        return False
    for domain in whitelist:
        if hostname == domain or hostname.endswith("." + domain):
            return True
    return False


def _is_binary_url(url: str) -> bool:
    """Check if URL likely points to a binary file (PDF, Office, image)."""
    lower = url.lower().split("?")[0]
    return lower.endswith((
        ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    ))


# ---------------------------------------------------------------------------
# Anti-crawl heuristics
# ---------------------------------------------------------------------------
# Keywords that indicate content was blocked or requires JavaScript
_ANTICRAWL_KEYWORDS = [
    "请在微信客户端打开",
    "请使用微信扫描二维码",
    "enable javascript",
    "please enable javascript",
    "access denied",
    "just a moment",
    "checking your browser",
    "cloudflare",
    "captcha",
    "验证码",
    "请完成验证",
    "robot",
    "automated access",
]

_MIN_CONTENT_LENGTH = 800  # Minimum chars for "good" extraction


def _is_anticrawl(text: str) -> bool:
    """Check if extracted text looks like an anti-crawl block page."""
    if not text:
        return True
    lower = text.lower()
    for kw in _ANTICRAWL_KEYWORDS:
        if kw.lower() in lower:
            return True
    return False


# ---------------------------------------------------------------------------
# Probe: lightweight extraction via requests + trafilatura
# ---------------------------------------------------------------------------
def probe_url(url: str, timeout: int = 20) -> dict:
    """Attempt to extract content from a URL using requests + trafilatura.

    Returns:
      {"ok": True, "title": ..., "content": ..., "content_length": ..., "method": "trafilatura|bs4|regex"}
      or {"ok": False, "reason": ...}
    """
    try:
        resp = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        })
        resp.raise_for_status()
    except Exception as e:
        return {"ok": False, "reason": f"HTTP request failed: {e}"}

    html = resp.text

    # Extract title
    title = ""
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()

    # Layer 1: trafilatura (preferred)
    content = ""
    method = "none"
    try:
        import trafilatura
        extracted = trafilatura.extract(html, include_links=True, include_comments=False)
        if extracted:
            content = extracted.strip()
            method = "trafilatura"
    except Exception:
        pass

    # Layer 2: BeautifulSoup fallback
    if len(content) < 200:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            # Remove script/style/nav/footer
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            bs_text = soup.get_text(separator='\n', strip=True)
            bs_text = re.sub(r'\n{3,}', '\n\n', bs_text).strip()
            if len(bs_text) > len(content):
                content = bs_text
                method = "bs4"
        except Exception:
            pass

    # Layer 3: regex fallback
    if not content:
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        content = re.sub(r'\s+', ' ', text).strip()
        if content:
            method = "regex"

    # Anti-crawl check
    if _is_anticrawl(content):
        return {"ok": False, "reason": "Anti-crawl page detected"}

    # Length check
    if len(content) < _MIN_CONTENT_LENGTH:
        return {"ok": False, "reason": f"Content too short ({len(content)} chars < {_MIN_CONTENT_LENGTH})"}

    return {
        "ok": True,
        "title": title,
        "content": content,
        "content_length": len(content),
        "method": method,
    }


# ---------------------------------------------------------------------------
# MinerU fallback
# ---------------------------------------------------------------------------
def _mineru_extract(url: str, model: str | None = None, max_chars: int = 20000) -> dict:
    """Call MinerU API via the mineru_parse_documents.py script.

    Returns {"ok": True, "content": ..., ...} or {"ok": False, "reason": ...}
    """
    token = os.environ.get("MINERU_TOKEN")
    if not token:
        return {"ok": False, "reason": "MINERU_TOKEN not configured"}

    # Import the mineru module
    mineru_script = Path(__file__).parent.parent / "mineru-extract" / "mineru_parse_documents.py"
    if not mineru_script.exists():
        return {"ok": False, "reason": f"MinerU script not found at {mineru_script}"}

    import importlib.util
    spec = importlib.util.spec_from_file_location("mineru_parse_documents", str(mineru_script))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    try:
        # Determine model version
        if not model:
            lower = url.lower()
            if lower.endswith((".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg")):
                model = "pipeline"
            else:
                model = "MinerU-HTML"

        api_base = os.environ.get("MINERU_API_BASE", "https://mineru.net")
        meta = mod.parse_one_url(
            api_base=api_base, token=token, source_url=url,
            enable_ocr=False, language="ch", page_ranges=None,
            model_version=model, enable_table=None, enable_formula=None,
            extra_formats=None, timeout_sec=600, poll_interval=3.0,
            cache=True, force=False,
        )

        # Read markdown content
        md_path = meta.get("markdown_path")
        if md_path and Path(md_path).exists():
            content = Path(md_path).read_text(encoding="utf-8", errors="replace")
            if max_chars and len(content) > max_chars:
                content = content[:max_chars] + "\n\n[TRUNCATED]"
            return {
                "ok": True,
                "title": "",
                "content": content,
                "content_length": len(content),
                "method": "mineru",
                "mineru_meta": meta,
            }
        else:
            return {"ok": False, "reason": "MinerU produced no markdown output"}
    except Exception as e:
        return {"ok": False, "reason": f"MinerU extraction failed: {e}"}


# ---------------------------------------------------------------------------
# Main extraction logic
# ---------------------------------------------------------------------------
def extract(url: str, mineru_model: str | None = None, max_chars: int = 20000) -> dict:
    """Extract content from a URL using the decision tree.

    Returns unified JSON result contract:
      {
        "ok": bool,
        "url": str,
        "title": str,
        "content": str,
        "content_length": int,
        "method": "trafilatura|bs4|regex|mineru",
        "fallback_used": bool,
        "error": str (only if ok=False)
      }
    """
    result = {
        "ok": False,
        "url": url,
        "title": "",
        "content": "",
        "content_length": 0,
        "method": "none",
        "fallback_used": False,
    }

    # Step 1: Binary files go directly to MinerU
    if _is_binary_url(url):
        mineru_result = _mineru_extract(url, model=mineru_model, max_chars=max_chars)
        if mineru_result["ok"]:
            result.update(mineru_result)
            result["url"] = url
            result["fallback_used"] = True
        else:
            result["error"] = mineru_result.get("reason", "Binary file extraction failed")
        return result

    # Step 2: Domain whitelist check -> MinerU directly
    if _is_whitelisted(url):
        mineru_result = _mineru_extract(url, model=mineru_model or "MinerU-HTML", max_chars=max_chars)
        if mineru_result["ok"]:
            result.update(mineru_result)
            result["url"] = url
            result["fallback_used"] = True
            return result
        # If MinerU fails, still try probe as fallback
        print(f"[content-extract] MinerU failed for whitelisted domain, trying probe: {mineru_result.get('reason', '')}", file=sys.stderr)

    # Step 3: Probe with trafilatura
    probe_result = probe_url(url)
    if probe_result["ok"]:
        result.update(probe_result)
        result["url"] = url
        result["ok"] = True
        return result

    # Step 4: Probe failed -> MinerU fallback (if token is configured)
    print(f"[content-extract] Probe failed: {probe_result.get('reason', '')}, trying MinerU fallback", file=sys.stderr)
    mineru_result = _mineru_extract(url, model=mineru_model, max_chars=max_chars)
    if mineru_result["ok"]:
        result.update(mineru_result)
        result["url"] = url
        result["fallback_used"] = True
        return result

    # Step 5: Everything failed
    result["error"] = (
        f"Probe: {probe_result.get('reason', 'unknown')}; "
        f"MinerU: {mineru_result.get('reason', 'not attempted')}"
    )
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Intelligent content extraction: URL -> clean text/markdown")
    ap.add_argument("--url", required=True, help="URL to extract content from")
    ap.add_argument("--mineru-model", default=None,
                    help="MinerU model version (pipeline|vlm|MinerU-HTML). Auto-detected if not set.")
    ap.add_argument("--max-chars", type=int, default=20000,
                    help="Max characters to return (default 20000)")
    args = ap.parse_args()

    result = extract(args.url, mineru_model=args.mineru_model, max_chars=args.max_chars)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
