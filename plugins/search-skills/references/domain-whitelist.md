# Domain Whitelist

Sites that always route to MinerU for content extraction (anti-crawl / JS-rendered / login wall).

When a URL matches any domain below, `content_extract.py` skips the trafilatura probe
and goes directly to MinerU API (if `MINERU_TOKEN` is configured).

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

## Paywalled / JS-rendered sites

- medium.com
- substack.com
- bloomberg.com
- wsj.com
- nytimes.com
- ft.com

## Notes

- This list is intentionally conservative. Most sites work fine with trafilatura.
- Add domains here only when trafilatura consistently fails to extract meaningful content.
- The probe layer will still attempt extraction for non-whitelisted domains, falling back to MinerU on failure.
