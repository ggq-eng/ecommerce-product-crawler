"""可选模块：用 Playwright 真实浏览器渲染苏宁详情页，补全「价格 / 用户综合评分」。

为什么需要它：
- 苏宁详情页主价格由 JS 异步渲染（且以"价格图片"返回，纯 HTTP 正则无法提取）；
- 评分/好评率依赖需登录态的异步评价接口，公开页面不展示。
- 本模块启动无头 Chromium 执行 JS，能稳定读取渲染后的主价格文本；
  评分如页面有展示则一并提取，否则留空（不伪造）。

合规说明：
- 仅做"模拟真实浏览器渲染"，复用登录态 Cookie（如有）、遵守限速，不破解任何签名/协议。
- 属于浏览器自动化，请在目标网站允许的前提下、控制频率使用。

依赖（可选，按需安装）：
    pip install playwright
    playwright install chromium

未安装 Playwright 时，本模块自动降级（返回 (None, None)），main.py 不会报错。
"""

import logging
import re

log = logging.getLogger("fashion_crawler")

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def fetch_price_rating(url: str, timeout_ms: int = 20000) -> tuple:
    """渲染详情页，返回 (price: float|None, rating: float|None)。

    任何异常都返回 (None, None)，由调用方决定如何处理（留空/记录）。
    """
    if not PLAYWRIGHT_AVAILABLE:
        return None, None

    price = None
    rating = None
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # 设置中文 UA，避免被导向非预期页面
            page.set_extra_http_headers({"Accept-Language": "zh-CN,zh;q=0.9"})
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)  # 等待价格 JS 渲染完成

            # ---- 价格：主价格区（避开"抢购价"占位区）----
            price_text = ""
            for sel in ["#mainPrice", ".mainprice", ".price-container", ".price-block",
                        ".product-price", "[class*=mainPrice]"]:
                el = page.query_selector(sel)
                if el:
                    price_text = (el.inner_text() or "").strip()
                    if price_text:
                        break
            m = re.search(r"(\d+(?:\.\d{1,2})?)", price_text.replace(",", ""))
            if m:
                price = float(m.group(1))

            # ---- 评分：页面若展示好评率/星级则提取 ----
            for sel in [".star-level", ".evaluate-grade", "#commentRate", ".good-rate",
                        "[class*=rating]", "[class*=satisfy]", ".score"]:
                el = page.query_selector(sel)
                if el:
                    rt = (el.inner_text() or "").strip()
                    mm = re.search(r"(\d+(?:\.\d+)?)", rt)
                    if mm:
                        rating = float(mm.group(1))
                        break

            browser.close()
    except Exception as e:
        log.warning("Playwright 详情渲染失败 %s: %s", url, e)
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        return None, None

    log.info("浏览器补全 %s | 价格=%s | 评分=%s",
             url.split("/")[-1][:20], price or "无", rating or "无")
    return price, rating
