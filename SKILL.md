---
name: ecommerce-product-crawler
description: "Build compliant e-commerce product crawlers that extract structured item data (name, category, material, price, rating, review count) with pagination, rate limiting (random 1-3s intervals), User-Agent rotation, login Cookie injection, captcha auto-pause, retry/timeout handling, cleaning and dedup, and UTF-8 CSV export with file+console logging. Use this skill when a user asks to 采集电商商品数据, 写个爬虫抓商品, 爬取某平台的商品信息, or needs a robust anti-ban-aware scraper template. It bundles a working Suning-based example and a platform-diagnostic methodology for adapting to other sites without cracking signatures or bypassing CAPTCHAs."
agent_created: true
---

# E-commerce Product Crawler

A reusable, compliance-first workflow for building e-commerce product-data
crawlers. The bundled `scripts/` is a complete, runnable example (Suning
易购 target) demonstrating every required capability. Copy it as a starting
point, then adapt only the **parser** to the target platform.

## When to use

- User asks to collect product data from any e-commerce / shopping site.
- User needs pagination, rate limiting, anti-ban handling, cleaning, and CSV
  export for a scraping task.
- User already has a half-built scraper and wants the robust structure
  (fetcher / parser / cleaner / saver / logger) applied.

## What the bundle guarantees (the 6 requirements)

| Requirement | Where it lives |
|---|---|
| Pagination + all fields | `parser.py::search(keyword, page)` + `fetch_detail` |
| Dedup (name/ID) + filter missing + normalize price/rating | `cleaner.py::clean_products` |
| UTF-8 CSV | `saver.py::save_products` (`encoding="utf-8"`) |
| Random 1–3s interval, UA rotation, Cookie, captcha auto-pause | `fetcher.py` + `config.py` + `main.py` |
| Exception handling (timeout / HTTP error / parse fail), single page never aborts run | `fetcher.py` + `main.py` (`continue` on failure) |
| Logging: progress / errors / final stats, file + console | `logger.py` + `main.py` |

## How to build a crawler with this skill

### Step 1 — Diagnose the target platform (read `references/platform-diagnostics.md`)

Before writing code, determine:

1. **Is the list page server-side rendered (SSR)?** Fetch it with `requests`
   and count product-card markers. If the HTML is a near-empty shell, the site is
   a React/Vue SPA and pure-HTTP fetching will not work (see the Jingdong case
   in the reference).
2. **Are prices/ratings in the HTML or loaded by JS?** Search the response for
   price/review keywords. If missing, they come from an async API (often signed)
   or are rendered as images.
3. **Is login required?** Look for redirects to a login/verify page.
4. **Captcha / risk-control signals** — record the URL patterns and page-title
   strings that indicate interception (used later in `is_verify_page`).

Apply the findings to choose a source that needs **no signature cracking**.
Prefer an SSR, no-login source for the bulk fields; offer a **Playwright**
browser-render module only as an optional, compliant add-on to fill JS-only
fields.

### Step 2 — Copy the template and configure

```bash
cp -r scripts/ my_crawler/
cd my_crawler
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
```

Edit `config.py`:

- `DEFAULT_KEYWORDS` — map `{search_term: 款式类别}`.
- `min_interval` / `max_interval` — set to `1.0` / `3.0` (seconds).
- `cookies_file` — path to a user-supplied login Cookie (`k=v; k2=v2`).
- `proxies`, `anti_crawl_pause`, `csv_encoding`, `output_file`.

### Step 3 — Implement the platform parser

Subclass the pattern in `parser.py::SuningParser`:

- `search(keyword, page)` → list of `Product` (list-page DOM selectors).
- `fetch_detail(product)` → fill price/material from the detail page.
- `is_verify_page(resp)` → return `True` on captcha / risk / verify pages.
- Register `is_verify_page` as `fetcher.verify_callback` in `__init__`.

The cleaner, saver, logger, and main loop **do not change** between platforms.

### Step 4 — Run, verify, iterate

```bash
python main.py --pages 1 --detail-limit 4 --no-browser --interval 1 3 \
    --output demo.csv
```

Check `logs/crawler.log` and the final stats line. If price/rating come back
empty on an SSR-but-JS-price platform, enable the browser path:

```bash
pip install playwright && playwright install chromium
python main.py --pages 1            # automatically uses browser for price/rating
```

## Compliance rules (non-negotiable)

- Use **only** rate limiting, UA rotation, retries, and user-provided login
  Cookies. **Never** crack signatures, reverse protocols, or bypass CAPTCHAs.
- Respect `robots.txt` and the site's terms; keep volume low (1–3 pages/keyword
  by default) and frequency gentle.
- If a field cannot be obtained honestly (e.g. price rendered as an image,
  rating gated behind login), **leave it empty** — never fabricate data.
- Surface the limitation clearly in the final report so the user is not misled.

## Files in `scripts/`

| File | Role |
|---|---|
| `config.py` | All tunable parameters (keywords, intervals, UA pool, proxies, cookies, encoding) |
| `fetcher.py` | `Fetcher`: session reuse, throttle, retry/backoff, UA rotation, cookie/proxy injection, captcha detection hook |
| `parser.py` | `Product` dataclass + `SuningParser` (list + detail + `is_verify_page`) |
| `cleaner.py` | Dedup by SKU/name, filter invalid, normalize price/rating |
| `saver.py` | UTF-8 CSV writer (overwrite/append) |
| `logger.py` | Console + rotating file logger |
| `detail_browser.py` | Optional Playwright module to fill JS-only price/rating (graceful degrade if absent) |
| `main.py` | CLI entry; orchestrates the whole pipeline + final stats |
| `requirements.txt` | `requests`, `beautifulsoup4`, `playwright` (optional) |
