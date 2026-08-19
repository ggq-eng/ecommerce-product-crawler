"""秋季服装商品数据采集 - 入口程序。

流程：配置 → 逐关键词分页抓列表页 → （可选）详情页补材质 → （可选）浏览器补价格/评分
      → 清洗去重 → 保存 CSV → 输出统计

用法示例：
    python main.py                        # 使用 config.py 默认配置
    python main.py --pages 1              # 每个关键词只抓 1 页
    python main.py --no-detail            # 不进详情页（材质留空，速度快）
    python main.py --no-browser           # 不用浏览器补全价格/评分（纯 HTTP）
    python main.py --interval 1 3         # 自定义请求间隔 1~3 秒
    python main.py --cookies cookie.txt   # 目标平台需要登录时注入登录态 Cookie
    python main.py --proxy http://127.0.0.1:7890
    python main.py --output result.csv
    python main.py --append               # 追加到已有 CSV（增量采集）
    python main.py --keyword 风衣女秋      # 只抓单个关键词

合规提示：仅用于学习研究，请遵守目标网站 robots.txt 与用户协议，控制频率。
"""

import argparse
import logging
import sys
import time
from pathlib import Path

from config import CrawlerConfig
from cleaner import clean_products
from fetcher import AntiCrawlDetected, CrawlError, Fetcher
from logger import setup_logger
from parser import SuningParser
from saver import save_products

log = logging.getLogger("fashion_crawler")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="秋季服装商品数据采集（默认目标：苏宁易购公开搜索页）")
    p.add_argument("--pages", type=int, default=None, help="每个关键词抓取页数（覆盖 config）")
    p.add_argument("--no-detail", action="store_true", help="不抓详情页（材质留空，速度快）")
    p.add_argument("--no-browser", action="store_true", help="不用浏览器补全价格/评分（纯 HTTP）")
    p.add_argument("--detail-limit", type=int, default=None, help="每关键词最多抓详情页的商品数")
    p.add_argument("--interval", nargs=2, type=float, metavar=("MIN", "MAX"), default=None,
                   help="请求随机间隔（秒），如 --interval 1 3")
    p.add_argument("--pause", type=float, default=None, help="检测到验证码后的自动暂停秒数")
    p.add_argument("--cookies", default=None, help="登录态 Cookie 文件路径（可选）")
    p.add_argument("--proxy", default=None, help="代理地址，如 http://127.0.0.1:7890")
    p.add_argument("--output", default=None, help="CSV 输出文件名")
    p.add_argument("--append", action="store_true", help="追加写入而非覆盖")
    p.add_argument("--keyword", default=None, help="只抓单个关键词（如 --keyword 风衣女秋）")
    return p.parse_args()


def build_config(args: argparse.Namespace) -> CrawlerConfig:
    cfg = CrawlerConfig()
    if args.pages is not None:
        cfg.pages_per_keyword = args.pages
    if args.no_detail:
        cfg.fetch_detail = False
    if args.no_browser:
        cfg.use_browser = False
    if args.detail_limit is not None:
        cfg.detail_limit = args.detail_limit
    if args.interval:
        cfg.min_interval, cfg.max_interval = sorted(args.interval)
    if args.pause is not None:
        cfg.anti_crawl_pause = args.pause
    if args.cookies:
        cfg.cookies_file = args.cookies
    if args.proxy:
        cfg.proxies = {"http": args.proxy, "https": args.proxy}
    if args.output:
        cfg.output_file = args.output
    if args.keyword:
        cfg.keywords = {args.keyword: cfg.keywords.get(args.keyword, args.keyword)}
    return cfg


def main() -> int:
    args = parse_args()
    cfg = build_config(args)
    setup_logger(level=cfg.log_level)

    # 浏览器模块可用性探测（不强制，未安装则降级为纯 HTTP）
    browser_ready = False
    if cfg.use_browser:
        try:
            from detail_browser import PLAYWRIGHT_AVAILABLE, fetch_price_rating
            browser_ready = PLAYWRIGHT_AVAILABLE
        except ImportError:
            browser_ready = False
        if not browser_ready:
            log.warning("未安装 Playwright，价格/评分将以纯 HTTP 方式采集（苏宁不暴露，将留空）。"
                        " 如需补全，请执行: pip install playwright && playwright install chromium")

    log.info("=" * 64)
    log.info("秋季服装商品数据采集启动")
    log.info("关键词(%d): %s", len(cfg.keywords), list(cfg.keywords))
    log.info("每关键词页数=%d, 详情页=%s, 详情限制=%d/关键词",
             cfg.pages_per_keyword, cfg.fetch_detail, cfg.detail_limit)
    log.info("请求间隔: %.1f~%.1f 秒, 超时 %.1f 秒, 重试 %d 次, 验证码暂停 %.0f 秒",
             cfg.min_interval, cfg.max_interval, cfg.timeout, cfg.max_retries, cfg.anti_crawl_pause)
    log.info("CSV 编码=%s, 浏览器补全价格/评分=%s", cfg.csv_encoding, "开" if browser_ready else "关")
    log.info("=" * 64)

    fetcher = Fetcher(cfg)
    parser = SuningParser(fetcher, cfg)

    all_products = []
    detail_stats = {"attempted": 0, "material_found": 0,
                    "price_found": 0, "rating_found": 0, "browser_used": 0}

    for keyword, category in cfg.keywords.items():
        log.info(">>> 开始抓取: %s (款式类别=%s)", keyword, category)
        detail_taken = 0
        for page in range(1, cfg.pages_per_keyword + 1):
            # ---------- 列表页（分页遍历）----------
            try:
                products = parser.search(keyword, page)
            except AntiCrawlDetected as e:
                log.error("⚠ %s", e)
                log.error("检测到验证码/反爬，自动暂停 %.0f 秒后跳过本关键词剩余页…",
                          cfg.anti_crawl_pause)
                time.sleep(cfg.anti_crawl_pause)   # 自动暂停
                break                              # 跳过当前关键词，继续下一个
            except CrawlError as e:
                log.error("抓取失败，跳过当前页: %s", e)
                continue                            # 单页失败不中断整体流程

            # ---------- 详情页补字段 ----------
            for pr in products:
                pr.category = category
                if cfg.fetch_detail and detail_taken < cfg.detail_limit and pr.sku:
                    try:
                        parser.fetch_detail(pr)
                    except AntiCrawlDetected:
                        log.error("详情页触发反爬，自动暂停 %.0f 秒并停止详情抓取",
                                  cfg.anti_crawl_pause)
                        time.sleep(cfg.anti_crawl_pause)
                        cfg.fetch_detail = False
                        break
                    except CrawlError as e:
                        log.warning("详情页失败: %s", e)
                    detail_stats["attempted"] += 1
                    if pr.material:
                        detail_stats["material_found"] += 1
                    detail_taken += 1

                    # ---------- 浏览器补全价格/评分 ----------
                    if browser_ready and (pr.price is None or pr.rating is None):
                        try:
                            from detail_browser import fetch_price_rating
                            bp, br = fetch_price_rating(pr.url,
                                                       timeout_ms=int(cfg.timeout * 1000) + 5000)
                            if bp is not None:
                                pr.price = bp
                            if br is not None:
                                pr.rating = br
                            detail_stats["browser_used"] += 1
                        except Exception as e:
                            log.warning("浏览器补全异常: %s", e)
                    if pr.price is not None:
                        detail_stats["price_found"] += 1
                    if pr.rating is not None:
                        detail_stats["rating_found"] += 1

            all_products.extend(products)
        log.info("<<< 关键词[%s] 完成，累计抓取 %d 条", keyword, len(all_products))

    if not all_products:
        log.error("未抓到任何商品，请检查网络/反爬设置后重试（详见 logs/crawler.log）")
        return 1

    # ---------- 清洗去重 ----------
    cleaned, stats = clean_products(all_products)

    # ---------- 保存 CSV ----------
    mode = "a" if args.append else "w"
    save_products(cleaned, cfg.output_path, mode=mode, encoding=cfg.csv_encoding)

    # ---------- 最终统计 ----------
    log.info("=" * 64)
    log.info("采集完成汇总")
    log.info("  原始抓取: %d 条", stats["raw"])
    log.info("  无效剔除: %d 条 | 重复剔除: %d 条", stats["invalid"], stats["dup"])
    log.info("  最终保存: %d 条 -> %s", stats["kept"], cfg.output_path)
    log.info("  字段命中: 材质 %d | 价格 %d | 评分 %d",
             detail_stats["material_found"], detail_stats["price_found"], detail_stats["rating_found"])
    if browser_ready:
        log.info("  浏览器渲染调用: %d 次", detail_stats["browser_used"])
    log.info("  日志文件: logs/crawler.log")
    log.info("=" * 64)

    print(f"\n✅ 采集完成：共保存 {stats['kept']} 条有效数据到 {cfg.output_path}")
    print(f"   清洗: 原始 {stats['raw']} → 无效剔除 {stats['invalid']} → 重复剔除 {stats['dup']} "
          f"→ 保留 {stats['kept']}")
    print(f"   字段命中: 材质 {detail_stats['material_found']} | 价格 {detail_stats['price_found']} "
          f"| 评分 {detail_stats['rating_found']}"
          + (f" | 浏览器渲染 {detail_stats['browser_used']} 次" if browser_ready else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
