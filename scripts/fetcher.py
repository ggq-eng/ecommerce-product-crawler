"""HTTP 请求层：Session 复用、随机 UA、请求间隔限速、指数退避重试、代理、Cookie 注入。

合规说明（务必阅读）：
- 本模块只做"合规请求"：限速、随机 UA、重试、以及用户自行提供的登录态 Cookie。
- 不包含任何验证码破解、签名伪造、协议逆向等绕过手段。
- 请遵守目标网站 robots.txt 与用户协议，控制抓取频率，勿用于商业牟利。
"""

import logging
import os
import random
import time
from typing import Callable, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import CrawlerConfig
from logger import setup_logger

log = setup_logger()


class AntiCrawlDetected(Exception):
    """检测到验证页 / 被反爬拦截时抛出，提示人工介入。"""


class CrawlError(Exception):
    """请求层通用异常（网络错误、HTTP 错误等）。"""


class Fetcher:
    def __init__(self, config: CrawlerConfig, verify_callback: Optional[Callable[[requests.Response], bool]] = None):
        self.config = config
        # 回调由解析层提供：返回 True 表示响应内容疑似验证页/反爬拦截页
        self.verify_callback = verify_callback

        self.session = requests.Session()
        # 连接池级网络重试：429 及 5xx 自动重试
        retry = Retry(
            total=config.max_retries,
            connect=config.max_retries,
            read=config.max_retries,
            backoff_factor=config.retry_backoff,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=5, pool_maxsize=5)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        if config.proxies:
            self.session.proxies.update(config.proxies)
            log.info("已启用代理: %s", config.proxies)

        self._load_cookies(config.cookies_file)
        self._last_request_at = 0.0

    # ------------------------------------------------------------------
    # Cookie 注入：优先读配置文件，其次环境变量 JD_COOKIE
    # ------------------------------------------------------------------
    def _load_cookies(self, cookies_file: str) -> None:
        cookie_str = ""
        if cookies_file and os.path.exists(cookies_file):
            with open(cookies_file, encoding="utf-8") as f:
                cookie_str = f.read().strip()
            log.info("已从文件加载 Cookie: %s", cookies_file)
        elif os.environ.get("JD_COOKIE"):
            cookie_str = os.environ["JD_COOKIE"].strip()
            log.info("已从环境变量 JD_COOKIE 加载 Cookie")
        if not cookie_str:
            return
        for kv in cookie_str.split(";"):
            kv = kv.strip()
            if "=" in kv:
                k, v = kv.split("=", 1)
                self.session.cookies.set(k.strip(), v.strip())
        log.info("Cookie 注入完成，共 %d 个键值对", len(cookie_str.split(";")))

    # ------------------------------------------------------------------
    # 限速与请求
    # ------------------------------------------------------------------
    def _throttle(self) -> None:
        """请求间隔控制：保证相邻两次请求至少间隔 [min_interval, max_interval] 秒。"""
        wait = random.uniform(self.config.min_interval, self.config.max_interval)
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < wait:
            time.sleep(wait - elapsed)

    def _random_headers(self, referer: str = "") -> dict:
        headers = {
            "User-Agent": random.choice(self.config.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def get(self, url: str, *, params: Optional[dict] = None,
            referer: str = "", headers: Optional[dict] = None) -> requests.Response:
        """带限速 / 重试 / 验证页检测的 GET 请求。

        抛出异常：
        - AntiCrawlDetected：检测到反爬拦截页（需人工配置 Cookie 或降低频率）
        - CrawlError：重试耗尽仍失败
        """
        req_headers = self._random_headers(referer)
        if headers:
            req_headers.update(headers)

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.config.max_retries + 1):
            self._throttle()
            try:
                resp = self.session.get(url, params=params, headers=req_headers,
                                        timeout=self.config.timeout)
                resp.raise_for_status()
                self._last_request_at = time.monotonic()

                if self.verify_callback and self.verify_callback(resp):
                    raise AntiCrawlDetected(
                        f"疑似触发反爬（URL: {resp.url}）。"
                        "应对措施：① 在 config.py 配置 cookies_file（登录态 Cookie）；"
                        "② 调大请求间隔；③ 配置代理；④ 降低抓取页数。"
                    )
                return resp

            except AntiCrawlDetected:
                raise                                   # 反爬拦截不需要重试，直接抛出
            except requests.RequestException as e:
                last_exc = e
                log.warning("请求失败(第%d/%d次) %s -> %s",
                            attempt, self.config.max_retries, url, e)
                if attempt < self.config.max_retries:
                    backoff = self.config.retry_backoff ** attempt + random.random()
                    log.info("等待 %.1f 秒后重试", backoff)
                    time.sleep(backoff)

        raise CrawlError(f"请求最终失败 {url}: {last_exc}")
