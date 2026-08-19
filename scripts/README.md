# 爬虫模板使用说明（scripts/）

这是一个**可直接运行**的电商商品数据采集模板（默认目标：苏宁易购公开搜索页，
无需登录即可采集「商品名称 / 款式类别 / 材质成分 / 评价数量」）。

## 快速开始

```bash
# 1. 准备隔离环境
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt

# 2. 运行（纯 HTTP，快速验证）
.venv/Scripts/python main.py --pages 1 --detail-limit 4 --no-browser --interval 1 3 --output demo.csv

# 3. 如需补全价格/评分（浏览器渲染，可选）
.venv/Scripts/python -m pip install playwright
.venv/Scripts/python -m playwright install chromium
.venv/Scripts/python main.py --pages 1
```

## 文件职责

| 文件 | 作用 |
|---|---|
| `config.py` | 全部可调参数：关键词→类别映射、请求间隔、UA 池、Cookie、代理、编码 |
| `fetcher.py` | 请求层：Session 复用、限速、指数退避重试、UA 轮换、Cookie/代理注入、验证页检测 |
| `parser.py` | `Product` 数据类 + `SuningParser`（列表页 / 详情页 / `is_verify_page`） |
| `cleaner.py` | 清洗去重：按 SKU/名称去重、过滤无效、归一化价格/评分 |
| `saver.py` | UTF-8 CSV 写入（覆盖/追加） |
| `logger.py` | 控制台 + 滚动文件日志 |
| `detail_browser.py` | 可选 Playwright 模块，补全 JS 渲染的价格/评分（未装则降级留空） |
| `main.py` | CLI 入口，串起全流程并输出统计 |

## 切换到其他平台

只需在 `parser.py` 仿照 `SuningParser` 新写一个解析器类，实现
`search` / `fetch_detail` / `is_verify_page` 三个方法，再在 `main.py` 中替换
`SuningParser` 的实例化即可——清洗 / 存储 / 限速 / 日志层无需改动。
切换前请先按 `references/platform-diagnostics.md` 评估目标平台是否合规可采集。

## 合规声明

仅含限速、随机 UA、重试、用户自行提供的登录态 Cookie；**不含任何签名破解 /
验证码绕过 / 协议逆向**。请遵守目标网站 robots.txt 与用户协议，控制抓取频率。
无法合规获取的价格/评分字段如实留空，绝不伪造数据。
