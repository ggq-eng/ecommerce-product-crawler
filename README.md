# ecommerce-product-crawler

> 来源分类：**原创/AI打磨** ｜ 导出批次：published

Build compliant e-commerce product crawlers that extract structured item data (name, category, material, price, rating, review count) with pagination, rate limiting (random 1-3s intervals), User-Agent rotation, login Cookie injection, captcha auto-pause, retry/timeout handling, cleaning and dedup, and UTF-8 CSV export with file+console logging. Use this skill when a user asks to 采集电商商品数据, 写个爬虫抓商品, 爬取某平台的商品信息, or needs a robust anti-ban-aware scraper template. It bundles a working Suning-based example and a platform-diagnostic methodology for adapting to other sites without cracking signatures or bypassing CAPTCHAs.

## 安装

把本文件夹整体复制到 WorkBuddy 技能目录：

```bash
cp -r . ~/.workbuddy/skills/ecommerce-product-crawler        # 用户级
# 或
cp -r . <项目>/.workbuddy/skills/ecommerce-product-crawler   # 项目级
```

重启/刷新 WorkBuddy 后即可在对话中触发。

## 说明

- 本技能从本地 WorkBuddy 环境导出，**所有真实密钥已脱敏为占位符**，使用前请配置你自己的 API Key。
- 若来自技能市场（文件夹名以 `__skillhub` 结尾），版权归原作者，请遵守其许可证。
