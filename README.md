# ecommerce-product-crawler

> ecommerce-product-crawler：Build compliant e-commerce product crawlers that extract structured item data (n…

## 📖 项目简介

**ecommerce-product-crawler** 是一个基于 `Python` 的仓库，主要用途：ecommerce-product-crawler：Build compliant e-commerce product crawlers that extract structured item data (n…。 仓库共包含 15 个文件，主要目录：`references`, `scripts`。 本文档由自动化流水线基于仓库实际文件结构生成，涵盖功能特性、目录结构与文件说明、快速开始与配置方式。

## ✨ 功能特性

- 清洗 + 去重，返回 (有效列表, 统计信息)。
- Crawlerconfig
- 渲染详情页，返回 (price: float|None, rating: float|None)。
- 检测到验证页 / 被反爬拦截时抛出，提示人工介入。
- 请求层通用异常（网络错误、HTTP 错误等）。
- Fetcher
- 初始化（或复用）全局 logger。重复调用不会产生重复 handler。
- Parse Args
- Build Config
- Main
- 单条商品记录（清洗前的原始形态）。
- '200万+条评价' / '1.2万评价' / '5评价' / '356' → int；解析失败返回 0。
- '¥129.00' / '38.00' → float；解析失败返回 None。
- Suningparser

## 📂 项目结构

```text
ecommerce-product-crawler/
├── references/
│   └── platform-diagnostics.md
├── scripts/
│   ├── README.md
│   ├── cleaner.py
│   ├── config.py
│   ├── detail_browser.py
│   ├── fetcher.py
│   ├── logger.py
│   ├── main.py
│   ├── parser.py
│   ├── requirements.txt
│   └── saver.py
├── .gitignore
├── LICENSE
├── README.md
└── SKILL.md
```

### 📄 文件说明

| 文件 / 目录 | 说明 |
| --- | --- |
| `.gitignore` | 资源/其他文件 |
| `LICENSE` | 资源/其他文件 |
| `README.md` | Markdown 文档 |
| `SKILL.md` | Markdown 文档 |
| `references/platform-diagnostics.md` | Markdown 文档 |
| `scripts/README.md` | Markdown 文档 |
| `scripts/cleaner.py` | 数据清洗与去重。 |
| `scripts/config.py` | 全局配置：目标搜索词、请求限速、重试策略、反爬应对参数、输出路径。 |
| `scripts/detail_browser.py` | 可选模块：用 Playwright 真实浏览器渲染苏宁详情页，补全「价格 / 用户综合评分」。 |
| `scripts/fetcher.py` | HTTP 请求层：Session 复用、随机 UA、请求间隔限速、指数退避重试、代理、Cookie 注入。 |
| `scripts/logger.py` | 日志配置：控制台 + 滚动文件双输出。 |
| `scripts/main.py` | 秋季服装商品数据采集 - 入口程序。 |
| `scripts/parser.py` | 解析层：苏宁易购公开搜索页实现（服务端渲染，纯 HTTP 即可采集）。 |
| `scripts/requirements.txt` | 文本文件 |
| `scripts/saver.py` | CSV 保存：默认 UTF-8 编码（满足"使用 UTF-8 编码"要求）。 |

## 🚀 快速开始

```bash
# Python 环境
pip install -r requirements.txt
```

> 具体运行入口请参考上述「文件说明」中的主脚本/入口文件；部分仓库含示例与说明文档，建议先阅读对应模块注释。

## ⚙️ 配置

本仓库涉及以下配置文件，使用前请按需调整：

- `scripts/config.py`

## 📄 许可证

本项目许可证见仓库根目录 `LICENSE` 文件，使用请遵循其条款。

## 🏷️ 标签

`ai-crafted` `automation` `ecommerce` `python` `skill` `workbuddy`

---

*本文档由 WorkBuddy 自动化流水线于 2026-09-24 基于仓库实际结构生成。*
