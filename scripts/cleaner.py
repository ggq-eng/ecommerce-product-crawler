"""数据清洗与去重。

清洗规则：
1. 名称：合并连续空白、去除首尾空白；
2. 过滤：无名称或无有效链接的记录视为无效丢弃；
   价格为 None 的记录保留（部分平台价格由 JS 异步渲染，列表页拿不到，
   不应因单字段缺失而丢弃整行有效信息）；价格为 0/负数视为错误值丢弃；
3. 去重：优先按平台 SKU 去重；无 SKU 时按「名称+价格」去重；
4. 材质：保留原始文本；评分为 None 的条目保留（CSV 中为空）。
"""

import re
from typing import Tuple

log = __import__("logging").getLogger("fashion_crawler")


def clean_products(products: list) -> Tuple[list, dict]:
    """清洗 + 去重，返回 (有效列表, 统计信息)。"""
    stats = {"raw": len(products), "invalid": 0, "dup": 0, "kept": 0}
    cleaned: list = []
    seen: set = set()

    for p in products:
        # --- 名称清洗 ---
        p.name = re.sub(r"\s+", " ", p.name or "").strip()

        # --- 无效数据过滤 ---
        if not p.name or not p.url:
            stats["invalid"] += 1
            log.debug("丢弃无效记录: 名称=%r url=%r", p.name, p.url)
            continue
        if p.price is not None and p.price <= 0:
            stats["invalid"] += 1
            log.debug("丢弃错误价格记录: %r price=%r", p.name, p.price)
            continue

        # --- 去重 ---
        key = p.sku or f"{p.name}|{p.price:.2f}"
        if key in seen:
            stats["dup"] += 1
            continue
        seen.add(key)

        # --- 数值规整 ---
        if p.price is not None:
            p.price = round(p.price, 2)
        if p.rating is not None:
            p.rating = round(p.rating, 1)

        cleaned.append(p)

    stats["kept"] = len(cleaned)
    log.info("清洗结果: 原始 %d 条 | 无效 %d | 重复 %d | 保留 %d",
             stats["raw"], stats["invalid"], stats["dup"], stats["kept"])
    return cleaned, stats
