"""CSV 保存：默认 UTF-8 编码（满足"使用 UTF-8 编码"要求）。

如需在 Excel/WPS 中直接打开不乱码，可将 config.csv_encoding 改为 "utf-8-sig"（带 BOM）。
"""

import csv
from pathlib import Path

from parser import Product

HEADERS = ["商品名称", "款式类别", "材质成分", "价格", "用户综合评分", "评价数量", "商品链接"]


def save_products(products: list, path: Path, mode: str = "w",
                  encoding: str = "utf-8") -> None:
    """写入 CSV。mode='w' 覆盖（写表头），mode='a' 追加（不写表头，用于增量采集）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, mode=mode, newline="", encoding=encoding) as f:
        writer = csv.writer(f)
        if mode == "w":
            writer.writerow(HEADERS)
        for p in products:
            writer.writerow([
                p.name,
                p.category,
                p.material,
                p.price if p.price is not None else "",
                p.rating if p.rating is not None else "",
                p.comment_count,
                p.url,
            ])
    log = __import__("logging").getLogger("fashion_crawler")
    log.info("已写入 %d 条记录 -> %s (编码=%s)", len(products), path, encoding)
