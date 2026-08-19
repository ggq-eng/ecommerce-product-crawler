"""日志配置：控制台 + 滚动文件双输出。

日志文件位于 logs/crawler.log，单文件 5MB 上限，保留 3 个备份，
避免长时间运行把磁盘写满。
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent / "logs"
_LOG_FILE = _LOG_DIR / "crawler.log"


def setup_logger(name: str = "fashion_crawler", level: str = "INFO") -> logging.Logger:
    """初始化（或复用）全局 logger。重复调用不会产生重复 handler。"""
    logger = logging.getLogger(name)
    if logger.handlers:                     # 已初始化过，直接返回
        return logger

    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(log_level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(log_level)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
