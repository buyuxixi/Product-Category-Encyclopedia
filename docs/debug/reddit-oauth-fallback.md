# Reddit OAuth 与 RSS 回退修复

## 问题描述

药物管理品类的 Reddit 讨论数据为空。单品类和定时爬取仅调用 RSS，容易被 Reddit 限流；RSS 返回空内容的 429 响应还会被错误记录为 HTTP 0，无法执行既有的退避逻辑。

## 根因

- `crawl_reddit_single.py` 重复实现 RSS 爬取流程，绕过了 `crawl_reddit.py` 中已有的 OAuth 优先逻辑。
- RSS 输出以空正文加状态码形式返回时，调用 `strip()` 丢失了状态码前的换行，导致 429 无法解析。

## 修复方案

- 单品类入口改为调用共享的 `crawl_reddit()`，使 API 触发和 Cron 都按 OAuth → RSS 的顺序执行。
- 保留 curl 输出的状态码分隔换行，并增加 `-L` 跟随重定向，保证空正文的 429 能触发退避。
- 在依赖清单中声明 `praw`，并在爬虫 README 记录 OAuth 配置方式。

## 验证结果

- 单元测试验证空正文的 429 被正确识别。
- 单元测试验证单品类入口复用共享爬虫。
- 实际 OAuth 调用需在运行环境配置 `REDDIT_CLIENT_ID`、`REDDIT_CLIENT_SECRET` 和 `REDDIT_USER_AGENT` 后执行。
