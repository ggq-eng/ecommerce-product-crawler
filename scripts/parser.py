"""解析层：苏宁易购公开搜索页实现（服务端渲染，纯 HTTP 即可采集）。

数据来源：
- 列表页 https://search.suning.com/{关键词}/  （SSR，含名称/评价数/链接）
- 商品详情页 https://product.suning.com/{商家}/{sku}.html （SSR，含材质参数）
- 价格/评分补全：苏宁主价格由 JS 异步渲染（纯 HTTP 只拿到模板占位，
  且页面价格以"图片"形式返回，无法用正则提取），评分/好评率依赖需登录态的
  异步评价接口。因此本解析器在纯 HTTP 下只保证 名称/款式类别/材质/评价数量
  三项可靠；价格与评分通过可选的 detail_browser.py（Playwright 真实浏览器渲染）
  补全——已装 Playwright 时 main.py 自动调用，未装则优雅留空，绝不伪造数据。

实测（2026-08）：
- 京东 PC 搜索页已改为 React SPA + 签名接口，纯 requests 无法获取列表；
  1688 搜索页需登录；淘宝/天猫/拼多多均为 JS + 登录态。
  故默认采用苏宁（无需登录、列表页服务端渲染），作为合规可采集样本源。
"""

import logging
import re
import urllib.parse
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import CrawlerConfig
from fetcher import Fetcher

log = logging.getLogger("fashion_crawler")


@dataclass
class Product:
    """单条商品记录（清洗前的原始形态）。"""
    name: str = ""
    category: str = ""                 # 款式类别（外套/毛衣/风衣…）
    material: str = ""                 # 材质成分
    price: Optional[float] = None      # 价格（元）
    rating: Optional[float] = None     # 用户综合评分（苏宁无公开数据，留空）
    comment_count: int = 0             # 评价数量
    sku: str = ""                      # 平台商品 ID（用于去重）
    url: str = ""


# ---------------------------------------------------------------------------
# 文本 → 数值 解析工具
# ---------------------------------------------------------------------------
def parse_comment_count(text: str) -> int:
    """'200万+条评价' / '1.2万评价' / '5评价' / '356' → int；解析失败返回 0。"""
    if not text:
        return 0
    m = re.search(r"([\d.]+)\s*(万)?", text.replace(",", ""))
    if not m:
        return 0
    num = float(m.group(1))
    if m.group(2) == "万":
        num *= 10000
    return int(num)


def parse_price(text: str) -> Optional[float]:
    """'¥129.00' / '38.00' → float；解析失败返回 None。"""
    if not text:
        return None
    m = re.search(r"\d+(?:\.\d+)?", text.replace(",", ""))
    return float(m.group(0)) if m else None


# ---------------------------------------------------------------------------
# 苏宁解析器
# ---------------------------------------------------------------------------
class SuningParser:
    LIST_URL_TPL = "https://search.suning.com/{kw}/"
    DETAIL_URL_TPL = "https://product.suning.com/{vendor}/{sku}.html"

    def __init__(self, fetcher: Fetcher, config: CrawlerConfig):
        self.fetcher = fetcher
        self.config = config
        self.fetcher.verify_callback = self.is_verify_page

    # ---------------- 反爬检测 ----------------
    def is_verify_page(self, resp: requests.Response) -> bool:
        """判断响应是否为验证页 / 反爬拦截页 / 异常页（验证码自动暂停的依据）。"""
        if any(k in resp.url.lower() for k in ("risk_handler", "verify", "captcha", "slider")):
            log.warning("检测到风控/验证跳转: %s", resp.url[:150])
            return True
        text = resp.text or ""
        title = re.search(r"<title>(.*?)</title>", text, re.S)
        if title and ("验证" in title.group(1) or "访问拦截" in title.group(1)
                      or "出错啦" in title.group(1) or "验证码" in title.group(1)):
            log.warning("检测到异常页/验证码，title=%s", title.group(1).strip())
            return True
        # 常见验证码特征文本（页面 body 较短且含拦截语）
        if len(text) < 1500 and ("验证码" in text or "访问验证" in text or "人机验证" in text):
            return True
        return False

    # ---------------- 列表页 ----------------
    def search(self, keyword: str, page: int) -> list:
        """抓取并解析某一关键词的某一页，返回 Product 列表。

        苏宁分页：第 1 页无参数，第 N 页使用 ?cp=N-1。
        """
        url = self.LIST_URL_TPL.format(kw=urllib.parse.quote(keyword))
        params = {"cp": page - 1} if page > 1 else None
        resp = self.fetcher.get(url, params=params, referer=self.LIST_URL_TPL.format(kw=""))

        soup = BeautifulSoup(resp.text, "html.parser")
        boxes = soup.select(".product-box")
        if not boxes:
            log.warning("关键词[%s] 第%d页 未解析到商品项（可能页面改版或触发风控），跳过",
                        keyword, page)
            return []

        products: list = []
        for box in boxes:
            name_el = box.select_one(".title-selling-point a")
            name = name_el.get_text(" ", strip=True) if name_el else ""

            vendor, sku = "", ""
            link = (name_el.get("href") or "") if name_el else ""
            m = re.search(r"product\.suning\.com/(\d+)/(\d+)\.html", link)
            if m:
                vendor, sku = m.group(1), m.group(2)

            # 过滤广告位（vendor 为 0000000000 的无真实商家商品）与无效链接
            if vendor == "0000000000" or not vendor or not sku:
                continue

            eval_el = box.select_one(".info-evaluate")
            eval_text = eval_el.get_text(strip=True) if eval_el else ""

            products.append(Product(
                name=name,
                category="",                      # 由 main 统一按搜索词回填
                sku=sku,
                comment_count=parse_comment_count(eval_text),
                url=self.DETAIL_URL_TPL.format(vendor=vendor, sku=sku),
            ))

        log.info("关键词[%s] 第%d页 解析到 %d 条商品", keyword, page, len(products))
        return products

    # ---------------- 详情页：价格 + 材质成分 ----------------
    def fetch_detail(self, product: Product) -> None:
        """抓取商品详情页，补充价格与材质成分。抓不到不报错，字段保持为空。

        价格说明：苏宁主价格区由 JS 异步渲染（SSR 只输出模板占位），
        这里仅在主价格区恰好包含服务端渲染的两位小数价格时提取，
        绝不回退到抢购区占位价（不同商品均显示 38.00，不可信）。
        """
        if not product.sku or not product.url:
            return
        try:
            resp = self.fetcher.get(product.url, referer=self.LIST_URL_TPL.format(kw=""))
        except Exception as e:
            log.warning("详情页抓取失败 %s: %s", product.url, e)
            return

        soup = BeautifulSoup(resp.text, "html.parser")

        # ---- 价格：仅接受主价格区（#mainPrice / .price-container）的 SSR 数值 ----
        mp = soup.select_one("#mainPrice") or soup.select_one(".price-container")
        if mp is not None:
            m = re.search(r"(\d+\.\d{2})", mp.get_text(" ", strip=True))
            if m:
                product.price = float(m.group(1))
                log.info("价格(SSR): %s -> %s", product.name[:20], product.price)

        # ---- 材质成分：核心参数区 li，形如 "面料主材质：蚕丝" ----
        container = soup.select_one("#kernelParmeter") or soup
        params = {}
        for li in container.select("li"):
            txt = li.get_text(" ", strip=True)
            for sep in ("：", ":"):
                if sep in txt:
                    k, v = txt.split(sep, 1)
                    params[k.strip()] = v.strip()
                    break
        main = params.get("面料主材质") or params.get("面料") or ""
        content = params.get("材质成分含量") or ""
        if main and content:
            product.material = f"{main}(含量{content})"
        else:
            product.material = main or content or ""

        log.info("详情页完成 %s | 价格=%s | 材质=%s",
                 product.name[:20], product.price or "无", product.material or "无")


# ---------------------------------------------------------------------------
# 接入其他平台（扩展指南）
# ---------------------------------------------------------------------------
# 1. 按 SuningParser 的结构新写一个 Parser 类，实现：
#      search(keyword, page) -> list[Product]    列表页解析
#      fetch_detail(product) -> None             详情页补字段（可选）
#      is_verify_page(resp)  -> bool             反爬检测
# 2. 在 main.py 中替换 parser 的实例化即可，清洗/存储/限速/日志层无需改动。
# 3. 需要登录的平台（淘宝/天猫/拼多多/京东部分页面）：
#      - 在 config.py 配置 cookies_file，登录态 Cookie 由用户自行提供；
#      - 平台页面结构随版本变化，解析选择器需按实测量测调整。
