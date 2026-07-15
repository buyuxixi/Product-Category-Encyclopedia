# 品类×关键词×数据源映射

## 品类列表（从 /api/v1/categories 获取）
- HEAT_THERAPY → 热疗
- FAR_INFRARED → 远红外热疗
- SHOULDER_NECK_HEAT_THERAPY → 肩颈热敷
- NIGHT_LIGHT → 夜灯
- PILL_ORGANIZER → 药物管理-药盒
- PILL_SPLITTER → 药物管理-切药器
- SEAT_CUSHION → 办公坐垫
- TENS_THERAPY → 电疗TENS

> 注：`MEDICATION_MANAGEMENT`（药物管理）已拆分为药盒/切药器两个独立品类，数据库保留 `inactive` 记录，列表 API / 前端均不再展示。

## 关键词映射（品类 → 搜索关键词列表）

### TENS_THERAPY (电疗TENS)
| Source | Keyword | Subreddit (Reddit) |
|--------|---------|---------------------|
| Amazon | TENS unit | — |
| Amazon | TENS unit pads | — |
| Google Trends | TENS unit | — |
| Google Trends | TENS machine | — |
| Reddit | TENS | r/ChronicPain |
| Reddit | TENS | r/Fibromyalgia |
| Reddit | TENS | r/physicaltherapy |
| Reddit | TENS neuropathy | r/diabetes |
| YouTube | TENS unit review | — |
| YouTube | TENS unit placement guide | — |
| YouTube | TENS vs EMS | — |
| Google News | TENS unit device | — |

### HEAT_THERAPY (热疗)
| Source | Keyword | Subreddit (Reddit) |
|--------|---------|---------------------|
| Amazon | heat wrap neck shoulder | — |
| Amazon | far infrared heating pad | — |
| Google Trends | heating pad | — |
| Google Trends | infrared heating pad | — |
| Reddit | heat therapy | r/ChronicPain |
| Reddit | heating pad | r/menstrual |
| YouTube | heating pad review | — |
| YouTube | infrared heating pad | — |
| Google News | heating pad heat therapy | — |

### SHOULDER_NECK_HEAT_THERAPY (肩颈热敷)
| Source | Keyword | Subreddit (Reddit) |
|--------|---------|---------------------|
| Amazon | neck heating pad | — |
| Amazon | shoulder heat wrap | — |
| Google Trends | neck heating pad | — |
| Google Trends | shoulder heating pad | — |
| Reddit | neck heating pad | r/ChronicPain |
| Reddit | shoulder heat | r/ChronicPain |
| YouTube | neck heating pad review | — |
| YouTube | shoulder heating pad | — |
| Google News | neck heating pad | — |
| Google News | shoulder heat therapy | — |

### FAR_INFRARED (远红外热疗)
| Source | Keyword | Subreddit (Reddit) |
|--------|---------|---------------------|
| Amazon | far infrared heating pad | — |
| Amazon | far infrared therapy device | — |
| Google Trends | far infrared heating pad | — |
| Google Trends | far infrared therapy | — |
| Reddit | far infrared | r/ChronicPain |
| Reddit | infrared heating pad | r/Fibromyalgia |
| YouTube | far infrared heating pad review | — |
| YouTube | infrared therapy device | — |
| Google News | far infrared heating pad | — |
| Google News | far infrared therapy | — |

### NIGHT_LIGHT (夜灯)
| Source | Keyword | Subreddit (Reddit) |
|--------|---------|---------------------|
| Amazon | night light motion sensor | — |
| Amazon | baby night light | — |
| Google Trends | night light | — |
| Google Trends | motion sensor night light | — |
| Reddit | night light | r/sleep |
| Reddit | night light baby | r/NewParents |
| Reddit | night light | r/smarthome |
| YouTube | best night light | — |
| YouTube | motion sensor night light review | — |
| Google News | night light LED | — |

### MEDICATION_MANAGEMENT (药物管理)
| Source | Keyword | Subreddit (Reddit) |
|--------|---------|---------------------|
| Amazon | pill organizer weekly | — |
| Amazon | pill splitter | — |
| Google Trends | pill organizer | — |
| Google Trends | pill splitter | — |
| Reddit | pill organizer | r/Caregiver |
| Reddit | pill organizer | r/diabetes |
| YouTube | pill organizer review | — |
| YouTube | smart pill dispenser | — |
| Google News | pill organizer medication | — |

### SEAT_CUSHION (办公坐垫)
| Source | Keyword | Subreddit (Reddit) |
|--------|---------|---------------------|
| Amazon | seat cushion office chair | — |
| Amazon | tailbone cushion | — |
| Google Trends | seat cushion | — |
| Google Trends | tailbone cushion | — |
| Reddit | seat cushion | r/Ergonomics |
| Reddit | seat cushion | r/backpain |
| Reddit | seat cushion | r/office |
| YouTube | best seat cushion review | — |
| YouTube | tailbone cushion | — |
| Google News | seat cushion ergonomic | — |

## 跳转链接模板

| Source | URL Template |
|--------|-------------|
| Amazon Search | `https://www.amazon.com/s?k={keyword}` |
| Amazon Product | `https://www.amazon.com/dp/{ASIN}` |
| Google Trends | `https://trends.google.com/trends/explore?q={keyword}` |
| Reddit Search | `https://www.reddit.com/r/{sub}/search/?q={keyword}&sort=new` |
| YouTube Search | `https://www.youtube.com/results?search_query={keyword}` |
| Google News RSS | `https://news.google.com/rss/search?q={keyword}&hl=en-US&gl=US&ceid=US:en` |
