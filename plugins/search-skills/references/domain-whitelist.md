# Domain Whitelist

Sites that prioritize MinerU for content extraction (heavy anti-crawl platforms).

When a URL matches any domain below, `content_extract.py` tries MinerU first
(best for these sites), then falls back to Probe → Exa → Tavily if MinerU fails.

## Chinese platforms (heavy anti-crawl)

- mp.weixin.qq.com
- weixin.qq.com
- zhihu.com
- zhuanlan.zhihu.com
- xiaohongshu.com
- xhslink.com
- bilibili.com
- weibo.com
- douyin.com
- toutiao.com
- 36kr.com
- juejin.cn

## Notes

- This list is intentionally conservative. Most sites work fine with the normal extraction path (Probe → Exa → Tavily → MinerU).
- Add domains here only when MinerU produces significantly better results than the normal path (e.g., sites with heavy anti-crawl that MinerU has been specifically optimized for).
- For non-whitelisted domains, the full fallback chain handles extraction failures automatically.
