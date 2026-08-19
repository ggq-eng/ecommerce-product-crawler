# Platform Diagnostics Methodology

A repeatable procedure for assessing whether a target e-commerce site can be
crawled with **compliant** pure-HTTP techniques, before committing to code.
Follow this before writing any parser.

## 1. Probe the list/search page

```python
import requests, re
from bs4 import BeautifulSoup
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "\
     "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}, timeout=20)
print("status", r.status_code, "len", len(r.text), "url", r.url)
title = re.search(r"<title>(.*?)</title>", r.text, re.S)
print("title", title.group(1).strip() if title else None)
```

Decide SSR vs SPA by counting product-card markers in `r.text`:

```python
soup = BeautifulSoup(r.text, "html.parser")
print("cards:", len(soup.select(".product-box")))   # use the site's real selector
for marker in ["product-box", "p-name", "data-sku", "gl-item", "J_goodsList"]:
    print(marker, marker in r.text)
```

- **Many markers present** → SSR, proceed with `requests` + `bs4`.
- **Empty shell / few markers** → SPA (React/Vue). Pure HTTP cannot read the
  list; either use browser automation for the list, or pick another source.

## 2. Check for redirect-to-login / captcha

```python
print("login redirect:", r.url.startswith(("https://passport", "https://login")))
print("captcha in url:", any(k in r.url.lower() for k in ("verify","captcha","risk")))
for kw in ["验证码","访问验证","人机验证","登录后查看","请登录"]:
    print(kw, kw in r.text[:5000])
```

## 3. Find where price & rating live

Search the list and detail HTML for price/review keywords:

```python
for kw in ["promotionPrice","salePrice","qg_promotionPrice","reviewTotal","好评",
           "star-level","评分"]:
    print(kw, r.text.count(kw))
```

Possible outcomes:

- **Value in HTML** → extract with regex/`bs4` (ideal).
- **Async API reference in JS** (e.g. `pas.suning.com`, `p.3.cn`) → try the
  public endpoint with the correct SKU/vendor params. If it requires a signed
  token, **stop** — that is signature cracking (non-compliant).
- **Price rendered as an image / canvas** → cannot extract text even with a
  real browser; leave the field empty.
- **Rating behind a login-gated endpoint** → requires user-supplied Cookie;
  otherwise leave empty.

For JS-rendered-but-text fields, a real browser (Playwright) can read the
rendered DOM. For image/anti-scrape prices, nothing honest works — document it.

## 4. Confirm pagination format

```python
for page in [2, 3]:
    url = f"{base}?cp={page-1}"          # try common schemes
    # or f"{base}pg-{page}/" / f"{base}{page}/"
    rr = requests.get(url, headers=H, timeout=20)
    print(page, len(rr.text), len(BeautifulSoup(rr.text,"html.parser").select(".product-box")))
```

Record the working scheme; encode it in `search(keyword, page)`.

## 5. Findings from the Autumn-Fashion build (2026-08, China e-commerce)

| Platform | List page | Price | Rating | Verdict |
|---|---|---|---|---|
| 京东 PC | React SPA + signed `s_new.php` | async API | async API | Pure-HTTP **not** viable; needs browser for list + signed API for detail (non-compliant to fully automate) |
| 京东 mobile (`so.m.jd.com`) | redirects to verify | — | — | Risk-control blocks |
| 苏宁易购 | **SSR** (`.product-box`) | **image** (anti-scrape) + placeholder "38.00" | login-gated API | **Use as no-login default**; 4 fields (name/category/material/reviews) reliable; price/rating empty |
| 1688 | requires login | — | — | Needs auth |
| 淘宝/天猫/拼多多 | JS + login | JS | JS | Needs auth + likely signing |
| 亚马逊中国 | restructured/discontinued | — | — | No longer a shopping search |
| 考拉海购 | discontinued | — | — | Defunct |

**Rule of thumb:** when the obvious target (JD) is locked, fall back to an
SSR no-login source (Suning here) for the bulk fields, and clearly state which
fields are unavailable rather than faking them.

## 6. Captcha / anti-crawl detection heuristics

Put these in `parser.is_verify_page(resp)`:

```python
if any(k in resp.url.lower() for k in ("risk_handler","verify","captcha","slider")):
    return True
title = re.search(r"<title>(.*?)</title>", resp.text, re.S)
if title and any(w in title.group(1) for w in ("验证","访问拦截","出错啦","验证码")):
    return True
if len(resp.text) < 1500 and any(w in resp.text for w in ("验证码","访问验证","人机验证")):
    return True
return False
```

When detected, `main.py` **auto-pauses** (`anti_crawl_pause` seconds, default
120) and skips to the next keyword, logging the event — no signature bypass.

## 7. Compliance guardrails (always)

- No signature/parameter reversal, no CAPTCHA solver, no protocol emulation.
- Login state only via Cookie the **user** provides (`cookies_file` or
  `JD_COOKIE` env var).
- Low volume + gentle frequency; honor `robots.txt`.
- Empty fields are honest; fabricated fields are not.
