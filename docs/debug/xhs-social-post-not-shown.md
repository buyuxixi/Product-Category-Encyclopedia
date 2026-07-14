# 小红书 hot_links 入库后界面不显示

## 问题描述

执行同事提供的小红书增量 SQL 后，库中已有 60 条 `platform=xiaohongshu` 的 `hot_links`，但百科「舆情与市场趋势」界面看不到。

## 排查过程

1. 确认 DB 有数据：`SELECT COUNT(*) FROM hot_links WHERE platform='xiaohongshu'` → 60
2. 确认 API 返回：`GET /categories/FAR_INFRARED/hot-links?days=7` 含 10 条小红书
3. 核对前端 `EncyclopediaView.vue` market tabs 渲染条件

## 根因

写入数据的 `link_type = social_post`，而前端「社区讨论」Tab 只渲染 `groupedHotLinks['discussion']`（Reddit），未包含 `social_post`。

## 修复方案

将 `social_post` 并入「社区讨论」Tab（与 Reddit 一起展示），平台标签按 `platform` 动态显示（含「小红书」）。

## 验证结果

- 讨论 Tab 使用 `discussionHotLinks = discussion + social_post`
- 总览「热门讨论」同步纳入小红书
- 前端镜像重建后生效
