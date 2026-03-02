# Content Extraction Heuristics

Rules used by `content_extract.py` to determine if a probe extraction succeeded or failed.

## Anti-Crawl Keyword Detection

If the extracted text contains any of these keywords (case-insensitive), the extraction
is considered blocked and MinerU fallback is triggered:

### Chinese anti-crawl indicators
- 请在微信客户端打开
- 请使用微信扫描二维码
- 验证码
- 请完成验证

### English anti-crawl indicators
- enable javascript
- please enable javascript
- access denied
- just a moment
- checking your browser
- cloudflare
- captcha
- robot
- automated access

## Minimum Content Length

- **Threshold: 800 characters**
- If extracted content is shorter than 800 chars, the extraction is considered a failure.
- This catches pages that return only navigation/header/footer without actual content.

## Extraction Layer Priority

1. **trafilatura** — Primary extractor. Best for article-style pages. Produces clean text.
2. **BeautifulSoup** — Fallback when trafilatura extracts < 200 chars. Strips script/style/nav/footer tags.
3. **Regex** — Last resort. Strips all HTML tags. Usually noisy but catches edge cases.
4. **MinerU** — External API fallback. Handles JS-rendered pages, PDFs, and anti-crawl sites.

## Binary File Detection

URLs ending with these extensions skip the probe and go directly to MinerU:
- `.pdf`, `.doc`, `.docx`, `.ppt`, `.pptx`, `.xls`, `.xlsx`
- `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`
