"""全局配置：目标搜索词、请求限速、重试策略、反爬应对参数、输出路径。

说明：
- 默认目标是苏宁易购公开搜索页（服务端渲染，无需登录即可采集名称/款式/材质/评价数）；
  价格与评分苏宁仅在浏览器端渲染/需登录态，故提供可选 Playwright 详情模块补全（见 detail_browser.py）。
- 如需切换平台，在 parser.py 新增解析器并在 main.py 中替换即可，清洗/存储/限速/日志层无需改动。
- Cookie / 代理均为可选配置，按需启用，详见 README。
"""

from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# 搜索词 → 款式类别 映射（秋季服装）
# 每个关键词会被作为"款式类别"写入结果行，可自行增删
# ---------------------------------------------------------------------------
DEFAULT_KEYWORDS = {
    "秋装女外套": "外套",
    "秋季毛衣女": "毛衣",
    "风衣女秋": "风衣",
    "秋季卫衣女": "卫衣",
    "秋季针织衫女": "针织衫",
    "秋装连衣裙女": "连衣裙",
}

# 内置浏览器 UA 池（随机轮换，降低被识别为脚本的风险）
DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) "
    "Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]


@dataclass
class CrawlerConfig:
    # ---------------- 抓取范围 ----------------
    keywords: dict = field(default_factory=lambda: dict(DEFAULT_KEYWORDS))
    pages_per_keyword: int = 2          # 每个关键词抓取几页（分页遍历）
    fetch_detail: bool = True           # 是否进详情页补"材质成分"（会成倍增加请求量）
    detail_limit: int = 5               # 每个关键词最多抓详情页的商品数（控制总请求量）

    # ---------------- 请求控制（反爬核心）----------------
    min_interval: float = 1.0           # 两次请求之间的随机间隔下限（秒）——满足"1-3秒"
    max_interval: float = 3.0           # 随机间隔上限（秒）
    timeout: float = 15.0               # 单次请求超时（秒）——覆盖网络超时异常
    max_retries: int = 3                # 单次请求失败重试次数
    retry_backoff: float = 2.0          # 重试退避基数（秒，指数增长）
    anti_crawl_pause: float = 120.0     # 检测到验证码/反爬时自动暂停的冷却时长（秒）

    # ---------------- 反爬应对 ----------------
    user_agents: list = field(default_factory=lambda: list(DEFAULT_USER_AGENTS))
    cookies_file: str = ""              # 登录态 Cookie 文件路径（可选；形如 "k1=v1; k2=v2"）
    proxies: dict = field(default_factory=dict)  # 代理，如 {"http": "http://127.0.0.1:7890", ...}
    use_browser: bool = True            # 若已安装 Playwright，自动用浏览器渲染补全价格/评分

    # ---------------- 输出 ----------------
    output_file: str = "autumn_fashion_products.csv"
    csv_encoding: str = "utf-8"         # 满足"UTF-8 编码"（Excel 打开乱码时可改为 utf-8-sig）
    log_level: str = "INFO"

    # ---------------- 派生属性 ----------------
    @property
    def output_path(self) -> Path:
        return Path(__file__).resolve().parent / self.output_file
