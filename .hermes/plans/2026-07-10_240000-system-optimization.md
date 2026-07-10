# 品类百科系统优化方案

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 从内容、数据、界面、用户体验、可用性五个维度全面优化品类百科系统

**Architecture:** 不改动后端 API 和数据库结构，重点优化：前端渲染体验、爬取数据质量、market section 内容时效性、飞书通知内容

---

## 一、审查发现的问题

### 内容层面

| # | 问题 | 严重度 | 影响范围 |
|---|------|--------|---------|
| C1 | 所有品类的 market section 顶部还写着"数据状态: 初稿（静态整理，需每日爬取最新热点）" | 🔴 高 | 6 个品类 |
| C2 | market section 的静态表格（6.1-6.4）是手写的，不会随爬取数据更新 | 🔴 高 | 内容与数据脱节 |
| C3 | PILL_ORGANIZER 品类不在 DB 中（被命名为 MEDICATION_MANAGEMENT），爬取脚本推 10 条数据被跳过 | 🟡 中 | 数据丢失 |
| C4 | FAR_INFRARED 和 SHOULDER_NECK 子品类内容过短（400-500 chars/section），远低于一级品类的 1000-2000 chars | 🟡 中 | 内容质量 |
| C5 | "新兴趋势" section 内容很短（287-760 chars），缺乏实质趋势分析 | 🟡 中 | 内容深度 |

### 数据层面

| # | 问题 | 严重度 | 影响范围 |
|---|------|--------|---------|
| D1 | 21/29 条 hot_links 来自 Google News（72%），平台来源过于单一 | 🟡 中 | 数据多样性 |
| D2 | 20/29 条 hot_links 没有 hotness_score（news 类无热度指标） | 🟡 中 | 热点筛选失效 |
| D3 | trend_signals 有重复（同一关键词出现 2 条相同的 Google News 数据） | 🟡 中 | 数据冗余 |
| D4 | listing_count = 0，没有 Amazon 商品快照数据 | 🔴 高 | 缺少核心数据 |
| D5 | Reddit 爬取因 429 限速几乎拿不到数据 | 🟡 中 | 数据源缺失 |

### 界面/UX 层面

| # | 问题 | 严重度 | 影响范围 |
|---|------|--------|---------|
| U1 | market section 的静态表格和动态 hot_links 卡片是割裂的，用户看到两张"皮" | 🔴 高 | 体验不一致 |
| U2 | 热点链接卡片没有按热度排序（API 返回按 is_hot + hotness_score + collected_at 排序，但 news 无 hotness_score 全部排在后面） | 🟡 中 | 排序不合理 |
| U3 | 前端没有"最后更新时间"的全局提示 | 🟡 中 | 时效性感知 |
| U4 | 缺少品类间趋势对比视图（如各品类 Google Trends 搜索兴趣对比） | 🟢 低 | 功能增强 |
| U5 | hot_links 卡片标题过长时用 -webkit-line-clamp 截断 2 行，但部分标题被截断后信息丢失 | 🟢 低 | 细节体验 |

### 可用性层面

| # | 问题 | 严重度 | 影响范围 |
|---|------|--------|---------|
| A1 | 爬取脚本中品类 code 与 DB 不一致（PILL_ORGANIZER vs MEDICATION_MANAGEMENT） | 🔴 高 | 数据丢失 |
| A2 | 推送脚本硬编码 admin 密码 | 🟡 中 | 安全性 |
| A3 | 飞书通知中"查看品类百科"按钮指向 localhost:4180，外网无法访问 | 🟢 低 | 仅本地使用 |
| A4 | 没有"手动触发爬取"的前端按钮 | 🟡 中 | 操作便捷性 |

---

## 二、优化任务

### Task 1: 修复品类 code 不一致（A1 + C3）

**Objective:** 爬取脚本中的 PILL_ORGANIZER 改为 DB 中的 MEDICATION_MANAGEMENT

**Files:**
- Modify: `~/.hermes/skills/productivity/hot-topic-crawler/scripts/crawl_google_news.py`
- Modify: `~/.hermes/skills/productivity/hot-topic-crawler/scripts/crawl_reddit.py`
- Modify: `~/.hermes/skills/productivity/hot-topic-crawler/scripts/crawl_youtube.py`
- Modify: `~/.hermes/skills/productivity/hot-topic-crawler/scripts/crawl_google_trends.py`
- Modify: `~/.hermes/skills/productivity/hot-topic-crawler/scripts/crawl_amazon.py`
- Modify: `~/.hermes/skills/productivity/hot-topic-crawler/references/source-mapping.md`

**操作：** 将所有脚本中的 `"PILL_ORGANIZER"` 替换为 `"MEDICATION_MANAGEMENT"`

**验证：** 重新运行爬取，确认 MEDICATION_MANAGEMENT 品类不再返回 404

---

### Task 2: 更新 market section 内容 — 去掉静态占位符（C1 + C2）

**Objective:** 将 market section 顶部的"数据状态: 初稿（静态整理，需每日爬取最新热点）"更新为动态时间戳

**方案：** 在推送脚本 `push_to_encyclopedia.py` 的 `push_all()` 之后增加一个 `update_market_section()` 函数，自动更新 market section 顶部的 blockquote：

```python
def update_market_section(cookies, category_code):
    """更新 market section 顶部的数据采集时间戳。"""
    # 读取当前 market section 内容
    # 替换第一行 blockquote 为最新的采集时间
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    new_header = f"> ⏰ **数据采集时间**: {today} | **数据状态**: 爬取Agent已自动更新 ✅"
    # PUT /categories/{code}/sections/market
```

**验证：** 刷新前端，market section 顶部显示当日日期 + "已自动更新"

---

### Task 3: hot_links 增加默认 hotness_score（D2）

**Objective:** Google News 的 hot_links 没有热度指标，给它们一个基于"新鲜度"的默认分数

**修改 `crawl_google_news.py`：**

```python
# News 爬取后，基于发布时间给一个 0-30 的默认热度分
from datetime import datetime, UTC

def news_hotness(pub_date_str):
    """越新越高分，24h 内 = 30, 7 天内 = 15, 30 天内 = 5"""
    # 简单计算
    return min(30, max(5, 30 - days_old))
```

**验证：** 爬取后 hot_links 中 news 类有条目有 hotness_score

---

### Task 4: trend_signals 去重（D3）

**Objective:** 在 dedup_and_score.py 的 `merge_results()` 中增加 trend_signals 去重

**逻辑：** 按 `category_code + keyword + platform + collected_at(日期)` 去重，同一天同一关键词同一平台只保留一条

**修改 `dedup_and_score.py`：**

```python
def deduplicate_trend_signals(items: list[dict]) -> list[dict]:
    """按品类+关键词+平台+日期去重 trend_signals。"""
    seen = set()
    result = []
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    for item in items:
        key = f"{item.get('category_code')}|{item.get('keyword')}|{item.get('platform')}|{today}"
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
```

**验证：** 推送后同一品类同一关键词不出现重复 trend_signal

---

### Task 5: 前端增加"最后更新"全局提示（U3）

**Objective:** 在 EncyclopediaView 顶部 summary-strip 旁边显示"舆情数据最后更新时间"

**修改 `EncyclopediaView.vue`：**

在 `loadCategory()` 中加载 hot_links 后，取 `collected_at` 的最大值作为最后更新时间，在 summary-strip 中显示：

```html
<div>
  <strong>{{ hotLinks.length }}</strong>
  <span>热点链接</span>
</div>
<div v-if="lastHotLinkUpdate">
  <strong>{{ formatRelativeTime(lastHotLinkUpdate) }}</strong>
  <span>舆情最后更新</span>
</div>
```

**验证：** 前端显示"舆情最后更新: X 小时前"

---

### Task 6: 前端 hot_links 按类型分组渲染（U1 + U2）

**Objective:** hot_links 卡片不再平铺，而是按 link_type 分组（爆品/讨论/视频/新闻/趋势），每组有标题

**修改 `EncyclopediaView.vue`：**

```typescript
const groupedHotLinks = computed(() => {
  const groups: Record<string, HotLink[]> = {}
  for (const link of sectionHotLinks.value) {
    const type = link.link_type
    if (!groups[type]) groups[type] = []
    groups[type].push(link)
  }
  return groups
})
```

模板改为按分组渲染，每组有中文标题：
- product → 🔥 爆品监控
- discussion → 💬 社区讨论
- video → 📺 视频测评
- news → 📰 新闻动态
- trend → 📈 搜索趋势

**验证：** hot_links 区域按类型分组显示，视觉层次更清晰

---

### Task 7: 前端增加"手动刷新热点"按钮（A4）

**Objective：** 在 market section 添加一个"手动爬取热点"按钮，点击后触发后端爬取

**方案：** 不需要后端改 API，按钮直接调用爬取脚本（通过终端工具）。但前端无法直接执行 Python 脚本，所以需要一个后端触发 API。

**轻量方案：** 在后端添加一个 `POST /api/v1/crawl/trigger` 端点，调用爬取脚本。

**修改 `backend/app/api.py`：**

```python
@router.post("/crawl/trigger")
def trigger_crawl(db: Db, actor: WriteActor):
    ensure_role(actor, "admin", "data", "researcher")
    import subprocess
    result = subprocess.run(
        ["python3", os.path.expanduser("~/.hermes/skills/productivity/hot-topic-crawler/scripts/crawl_all_and_push.py")],
        capture_output=True, text=True, timeout=300
    )
    return {"stdout": result.stdout[-2000:], "stderr": result.stderr[-500:], "returncode": result.returncode}
```

**前端：** 在 market section header 添加按钮

**验证：** 点击按钮，前端显示 loading，完成后刷新数据

---

### Task 8: 飞书通知增加 Top 3 热点标题（内容优化）

**Objective:** 飞书通知不只显示数字，还展示 Top 3 最热链接的标题

**修改 `push_to_encyclopedia.py` 的 `send_feishu_notification()`：**

```python
# 取 Top 3 最热链接
top_hot = sorted(
    [l for l in crawl_result.get("hot_links", []) if l.get("is_hot")],
    key=lambda x: x.get("hotness_score") or 0,
    reverse=True
)[:3]

top_lines = "\n".join(
    f"  🔥 [{l.get('platform','').upper()}] {l.get('title','')[:40]}"
    for l in top_hot
)
```

在卡片中增加"今日 Top 3 热点"区块

**验证：** 飞书通知包含具体的热点标题

---

### Task 9: 充实子品类内容（C4 + C5）

**Objective:** FAR_INFRARED 和 SHOULDER_NECK 子品类的内容太短，需要扩充

**方案：** 用 AI 生成草稿 + 已有数据补充。这是内容层面的工作，建议：
1. 调用 `POST /categories/{code}/drafts` 生成 AI 草稿
2. 人工审核修改

**验证：** 子品类各 section 内容 >= 800 chars

---

### Task 10: 安全优化 — 推送脚本密码不硬编码（A2）

**Objective:** 推送脚本中的 admin 密码改为环境变量

**修改 `push_to_encyclopedia.py`：**

```python
CRAWLER_USERNAME = os.getenv("CRAWLER_USERNAME", "admin")
CRAWLER_PASSWORD = os.getenv("CRAWLER_PASSWORD", "")

def login():
    if not CRAWLER_PASSWORD:
        print("[ERROR] CRAWLER_PASSWORD not set", file=sys.stderr)
        return None
    # ...
```

**验证：** 不设 CRAWLER_PASSWORD 时脚本报错提示

---

## 三、优先级排序

| 优先级 | Task | 工作量 |
|--------|------|--------|
| P0 | Task 1: 修复品类 code 不一致 | 5 min |
| P0 | Task 2: 更新 market section 静态占位符 | 15 min |
| P0 | Task 3: hot_links 增加默认 hotness_score | 10 min |
| P1 | Task 4: trend_signals 去重 | 10 min |
| P1 | Task 6: 前端 hot_links 按类型分组 | 20 min |
| P1 | Task 8: 飞书通知增加 Top 3 标题 | 10 min |
| P2 | Task 5: 前端"最后更新"提示 | 15 min |
| P2 | Task 7: 前端"手动刷新"按钮 | 30 min |
| P2 | Task 10: 密码环境变量化 | 5 min |
| P3 | Task 9: 充实子品类内容 | 需人工 |

---

## 四、验证清单

- [ ] MEDICATION_MANAGEMENT 品类不再 404
- [ ] market section 顶部不再显示"静态整理"字样
- [ ] news 类 hot_links 有 hotness_score
- [ ] trend_signals 不出现同日同关键词重复
- [ ] 前端 hot_links 按类型分组显示
- [ ] 飞书通知包含 Top 3 热点标题
- [ ] 前端显示"舆情最后更新"时间
