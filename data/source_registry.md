# 品类百科数据源注册表

> **用途**: 作为每日爬取/搜索的数据源清单。分为「静态知识源」和「动态更新源」两类。
> **创建时间**: 2026-07-10  
> **维护**: 随品类扩展持续更新

---

## 一、静态知识源（低频更新，基础知识底座）

这类源内容稳定，不需要每日爬取，建议每月或每季度更新一次即可。

### 1.1 Wikipedia API（知识定义与机制）

**爬取方式**: Wikipedia REST API  
**API端点**: `https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts&explaintext=1&titles={title}&redirects=1`  
**频率**: 月度更新  
**无需处理反爬**

| 品类 | Wikipedia 文章标题 | URL |
|------|-------------------|-----|
| 电疗TENS | Transcutaneous electrical nerve stimulation | https://en.wikipedia.org/wiki/Transcutaneous_electrical_nerve_stimulation |
| 电疗TENS | TENS unit | https://en.wikipedia.org/wiki/TENS_unit |
| 电疗TENS | Electrotherapy | https://en.wikipedia.org/wiki/Electrotherapy |
| 电疗TENS | Electrical muscle stimulation | https://en.wikipedia.org/wiki/Electrical_muscle_stimulation |
| 电疗TENS | Neurostimulation | https://en.wikipedia.org/wiki/Neurostimulation |
| 电疗TENS | Gate control theory | https://en.wikipedia.org/wiki/Gate_control_theory |
| 电疗TENS | Pain management | https://en.wikipedia.org/wiki/Pain_management |
| 电疗TENS | Chronic pain | https://en.wikipedia.org/wiki/Chronic_pain |
| 电疗TENS | Arthritis | https://en.wikipedia.org/wiki/Arthritis |
| 电疗TENS | Diabetic neuropathy | https://en.wikipedia.org/wiki/Diabetic_neuropathy |
| 电疗TENS | Menstrual pain (Dysmenorrhea) | https://en.wikipedia.org/wiki/Dysmenorrhea |
| 热疗 | Heat therapy | https://en.wikipedia.org/wiki/Heat_therapy |
| 热疗 | Thermotherapy | https://en.wikipedia.org/wiki/Thermotherapy |
| 热疗 | Heating pad | https://en.wikipedia.org/wiki/Heating_pad |
| 热疗 | Infrared heater | https://en.wikipedia.org/wiki/Infrared_heater |
| 热疗 | Infrared lamp | https://en.wikipedia.org/wiki/Infrared_lamp |
| 热疗 | Hot water bottle | https://en.wikipedia.org/wiki/Hot_water_bottle |
| 热疗 | Warm compress | https://en.wikipedia.org/wiki/Warm_compress |
| 夜灯 | Nightlight | https://en.wikipedia.org/wiki/Nightlight |
| 夜灯 | Smart lighting | https://en.wikipedia.org/wiki/Smart_lighting |
| 夜灯 | Passive infrared sensor | https://en.wikipedia.org/wiki/Passive_infrared_sensor |
| 夜灯 | Circadian rhythm | https://en.wikipedia.org/wiki/Circadian_rhythm |
| 夜灯 | Melatonin | https://en.wikipedia.org/wiki/Melatonin |
| 夜灯 | Sleep hygiene | https://en.wikipedia.org/wiki/Sleep_hygiene |
| 夜灯 | Illuminance | https://en.wikipedia.org/wiki/Illuminance |
| 夜灯 | Lumen (unit) | https://en.wikipedia.org/wiki/Lumen_(unit) |
| 夜灯 | Home automation | https://en.wikipedia.org/wiki/Home_automation |
| 药盒/切药器 | Pill organizer | https://en.wikipedia.org/wiki/Pill_organizer |
| 药盒/切药器 | Pill splitter | https://en.wikipedia.org/wiki/Pill_splitter |
| 药盒/切药器 | Medication adherence | https://en.wikipedia.org/wiki/Medication_adherence |
| 药盒/切药器 | Medication management | https://en.wikipedia.org/wiki/Medication_management |
| 药盒/切药器 | Medication error | https://en.wikipedia.org/wiki/Medication_error |
| 药盒/切药器 | Polypharmacy | https://en.wikipedia.org/wiki/Polypharmacy |
| 办公坐垫 | Memory foam | https://en.wikipedia.org/wiki/Memory_foam |
| 办公坐垫 | Ergonomics | https://en.wikipedia.org/wiki/Ergonomics |
| 办公坐垫 | Cushion | https://en.wikipedia.org/wiki/Cushion |
| 办公坐垫 | Orthopedic pillow | https://en.wikipedia.org/wiki/Orthopedic_pillow |
| 办公坐垫 | Orthopedics | https://en.wikipedia.org/wiki/Orthopedics |

### 1.2 权威医疗/健康网站（专业背书）

**爬取方式**: HTTP GET + HTML解析  
**频率**: 季度更新  
**注意**: 部分站点可能有反爬，需设置合理User-Agent

| 来源 | 品类 | URL |
|------|------|-----|
| Harvard Health Publishing | 电疗TENS | https://www.health.harvard.edu/pain/transcutaneous-electrical-nerve-stimulation-tens-for-pain-management |
| Harvard Health Publishing | 热疗 | https://www.health.harvard.edu/pain/heat-and-cold-for-pain-relief |
| Harvard Health Publishing | 夜灯(蓝光) | https://www.health.harvard.edu/staying-healthy/blue-light-has-a-dark-side |
| Johns Hopkins Medicine | 电疗TENS | https://www.hopkinsmedicine.org/health/treatment-tests-and-therapies/transcutaneous-electrical-nerve-stimulation |
| Arthritis Foundation | 热疗 | https://www.arthritis.org/health-wellness/healthy-living/managing-arthritis/daily-living/easy-stuff/best-heat-cold-pain-relief |
| Sleep Foundation | 夜灯 | https://www.sleepfoundation.org/bedroom-environment/night-lights |
| NIA (National Institute on Aging) | 药盒 | https://www.nia.nih.gov/health/medicines-and-medication-management |
| CDC NIOSH | 办公坐垫(人体工学) | https://www.cdc.gov/niosh/topics/ergonomics/ |
| Spine-Health | 办公坐垫 | https://www.spine-health.com/wellness/ergonomics/ergonomic-seat-cushions |

---

## 二、动态更新源（高频更新，舆情/热点/爆品）

这类源需要每日爬取/搜索，用于更新「第六章 舆情与市场趋势」。

### 2.1 Amazon（爆品/竞品监控）

**爬取方式**: 浏览器自动化 或 第三方API  
**频率**: 每日  
**数据用途**: 爆品发现、价格变动、新品上架、评论主题变化

| 搜索关键词 | 用途 | Amazon搜索URL（跳转链接） |
|------------|------|--------------------------|
| TENS unit | 爆品监控 | https://www.amazon.com/s?k=TENS+unit |
| TENS unit pads | 耗材/复购品 | https://www.amazon.com/s?k=TENS+unit+pads |
| heat wrap neck shoulder | 肩颈热敷爆品 | https://www.amazon.com/s?k=heat+wrap+neck+shoulder |
| far infrared heating pad | 远红外热疗爆品 | https://www.amazon.com/s?k=far+infrared+heating+pad |
| night light motion sensor | 感应夜灯爆品 | https://www.amazon.com/s?k=night+light+motion+sensor |
| baby night light | 婴儿夜灯爆品 | https://www.amazon.com/s?k=baby+night+light |
| pill organizer weekly | 药盒爆品 | https://www.amazon.com/s?k=pill+organizer+weekly |
| pill splitter | 切药器爆品 | https://www.amazon.com/s?k=pill+splitter |
| seat cushion office chair | 办公坐垫爆品 | https://www.amazon.com/s?k=seat+cushion+office+chair |
| tailbone cushion | 尾骨坐垫爆品 | https://www.amazon.com/s?k=tailbone+cushion |

**Amazon Best Sellers 页面（类目排名）**:

| 品类 | Best Sellers URL |
|------|-----------------|
| TENS | https://www.amazon.com/Best-Sellers-Health-Household-TENS-Units/zgbs/hpc/3777861 |
| 热敷垫 | https://www.amazon.com/Best-Sellers-Health-Household-Heating-Pads/zgbs/hpc/3777951 |
| 夜灯 | https://www.amazon.com/Best-Sellers-Tools-Home-Improvement-Night-Lights/zgbs/hi/502860 |
| 药盒 | https://www.amazon.com/Best-Sellers-Health-Household-Pill-Organizers/zgbs/hpc/3778151 |
| 坐垫 | https://www.amazon.com/Best-Sellers-Home-Kitchen-Cushions/zgbs/kitchen/3733141 |

### 2.2 Google Trends（搜索趋势/关键词趋势）

**爬取方式**: 非官方API（pytrends库）或浏览器自动化  
**频率**: 每日  
**数据用途**: 搜索量趋势、关键词热度变化、季节性分析

| 品类 | 关键词 | Google Trends URL（跳转链接） |
|------|--------|------------------------------|
| 电疗TENS | TENS unit | https://trends.google.com/trends/explore?q=TENS%20unit |
| 电疗TENS | TENS machine | https://trends.google.com/trends/explore?q=TENS%20machine |
| 热疗 | heating pad | https://trends.google.com/trends/explore?q=heating%20pad |
| 热疗 | infrared heating pad | https://trends.google.com/trends/explore?q=infrared%20heating%20pad |
| 夜灯 | night light | https://trends.google.com/trends/explore?q=night%20light |
| 夜灯 | motion sensor night light | https://trends.google.com/trends/explore?q=motion%20sensor%20night%20light |
| 药盒 | pill organizer | https://trends.google.com/trends/explore?q=pill%20organizer |
| 药盒 | pill splitter | https://trends.google.com/trends/explore?q=pill%20splitter |
| 坐垫 | seat cushion | https://trends.google.com/trends/explore?q=seat%20cushion |
| 坐垫 | tailbone cushion | https://trends.google.com/trends/explore?q=tailbone%20cushion |

### 2.3 Reddit（社区讨论/真实用户反馈）

**爬取方式**: Reddit JSON API (https://www.reddit.com/r/{sub}/search.json) 或 PRAW库  
**频率**: 每日  
**注意**: Reddit API 需注册应用获取 client_id/secret；本机网络可能需要代理  
**数据用途**: 真实用户讨论、痛点发现、口碑监测

| 品类 | Subreddit | 搜索关键词 | URL（跳转链接） |
|------|-----------|-----------|----------------|
| 电疗TENS | r/ChronicPain | TENS | https://www.reddit.com/r/ChronicPain/search/?q=TENS&sort=new |
| 电疗TENS | r/Fibromyalgia | TENS | https://www.reddit.com/r/Fibromyalgia/search/?q=TENS&sort=new |
| 电疗TENS | r/physicaltherapy | TENS | https://www.reddit.com/r/physicaltherapy/search/?q=TENS&sort=new |
| 电疗TENS | r/diabetes | TENS neuropathy | https://www.reddit.com/r/diabetes/search/?q=TENS+neuropathy&sort=new |
| 热疗 | r/ChronicPain | heat therapy | https://www.reddit.com/r/ChronicPain/search/?q=heat+therapy&sort=new |
| 热疗 | r/menstrual | heating pad | https://www.reddit.com/r/menstrual/search/?q=heating+pad&sort=new |
| 夜灯 | r/sleep | night light | https://www.reddit.com/r/sleep/search/?q=night+light&sort=new |
| 夜灯 | r/NewParents | night light baby | https://www.reddit.com/r/NewParents/search/?q=night+light&sort=new |
| 夜灯 | r/smarthome | night light | https://www.reddit.com/r/smarthome/search/?q=night+light&sort=new |
| 药盒 | r/Caregiver | pill organizer | https://www.reddit.com/r/Caregiver/search/?q=pill+organizer&sort=new |
| 药盒 | r/diabetes | pill organizer | https://www.reddit.com/r/diabetes/search/?q=pill+organizer&sort=new |
| 坐垫 | r/Ergonomics | seat cushion | https://www.reddit.com/r/Ergonomics/search/?q=seat+cushion&sort=new |
| 坐垫 | r/backpain | seat cushion | https://www.reddit.com/r/backpain/search/?q=seat+cushion&sort=new |
| 坐垫 | r/office | seat cushion | https://www.reddit.com/r/office/search/?q=seat+cushion&sort=new |

### 2.4 YouTube（KOL测评/开箱/教程）

**爬取方式**: YouTube Data API v3 或 搜索页解析  
**频率**: 每日  
**数据用途**: KOL测评视频、开箱视频、教程类视频热度

| 品类 | 搜索关键词 | URL（跳转链接） |
|------|-----------|----------------|
| 电疗TENS | TENS unit review | https://www.youtube.com/results?search_query=TENS+unit+review |
| 电疗TENS | TENS unit placement guide | https://www.youtube.com/results?search_query=TENS+unit+placement+guide |
| 电疗TENS | TENS vs EMS | https://www.youtube.com/results?search_query=TENS+vs+EMS |
| 热疗 | heating pad review | https://www.youtube.com/results?search_query=heating+pad+review |
| 热疗 | infrared heating pad | https://www.youtube.com/results?search_query=infrared+heating+pad |
| 夜灯 | best night light | https://www.youtube.com/results?search_query=best+night+light |
| 夜灯 | motion sensor night light review | https://www.youtube.com/results?search_query=motion+sensor+night+light+review |
| 药盒 | pill organizer review | https://www.youtube.com/results?search_query=pill+organizer+review |
| 药盒 | smart pill dispenser | https://www.youtube.com/results?search_query=smart+pill+dispenser |
| 坐垫 | best seat cushion review | https://www.youtube.com/results?search_query=best+seat+cushion+review |
| 坐垫 | tailbone cushion | https://www.youtube.com/results?search_query=tailbone+cushion |

### 2.5 TikTok（短视频趋势/爆品发现）

**爬取方式**: TikTok Research API 或 搜索页浏览器自动化  
**频率**: 每日  
**数据用途**: 爆品发现、病毒传播趋势、年轻消费者偏好

| 品类 | 搜索关键词 | URL（跳转链接） |
|------|-----------|----------------|
| 电疗TENS | tens unit | https://www.tiktok.com/search?q=tens+unit |
| 电疗TENS | tens machine period | https://www.tiktok.com/search?q=tens+machine+period |
| 热疗 | heating pad period | https://www.tiktok.com/search?q=heating+pad+period |
| 热疗 | graphene heating pad | https://www.tiktok.com/search?q=graphene+heating+pad |
| 夜灯 | night light | https://www.tiktok.com/search?q=night+light |
| 夜灯 | motion sensor light | https://www.tiktok.com/search?q=motion+sensor+light |
| 药盒 | pill organizer | https://www.tiktok.com/search?q=pill+organizer |
| 坐垫 | seat cushion | https://www.tiktok.com/search?q=seat+cushion |
| 坐垫 | ergonomic cushion | https://www.tiktok.com/search?q=ergonomic+cushion |

### 2.6 X/Twitter（实时讨论/舆情）

**爬取方式**: X API v2 (需付费) 或 浏览器自动化  
**频率**: 每日  
**数据用途**: 实时舆情、品牌提及、用户投诉

| 品类 | 搜索关键词 | URL（跳转链接） |
|------|-----------|----------------|
| 电疗TENS | "TENS unit" | https://twitter.com/search?q=%22TENS%20unit%22&f=live |
| 热疗 | "heating pad" OR "heat wrap" | https://twitter.com/search?q=%22heating%20pad%22&f=live |
| 夜灯 | "night light" | https://twitter.com/search?q=%22night%20light%22&f=live |
| 药盒 | "pill organizer" OR "pill box" | https://twitter.com/search?q=%22pill%20organizer%22&f=live |
| 坐垫 | "seat cushion" OR "tailbone cushion" | https://twitter.com/search?q=%22seat%20cushion%22&f=live |

### 2.7 Facebook Groups & Marketplace

**爬取方式**: Facebook Graph API（受限）或 浏览器自动化  
**频率**: 每日  
**数据用途**: 社群讨论、二手市场热度

| 品类 | 搜索关键词 | URL |
|------|-----------|-----|
| 全品类 | TENS / heating pad / night light / pill organizer / seat cushion | https://www.facebook.com/search/posts/?q={keyword} |

### 2.8 Google Search（高频搜索问题发现）

**爬取方式**: 搜索结果页解析 或 "People Also Ask" API  
**频率**: 每日  
**数据用途**: 发现用户新的搜索问题、痛点变化

| 品类 | 搜索模板 | URL |
|------|---------|-----|
| 电疗TENS | "how to" TENS unit | https://www.google.com/search?q=how+to+TENS+unit |
| 电疗TENS | TENS unit best | https://www.google.com/search?q=TENS+unit+best |
| 热疗 | heating pad for | https://www.google.com/search?q=heating+pad+for |
| 夜灯 | night light for | https://www.google.com/search?q=night+light+for |
| 药盒 | pill organizer | https://www.google.com/search?q=pill+organizer |
| 坐垫 | seat cushion for | https://www.google.com/search?q=seat+cushion+for |

### 2.9 市场研究报告（行业数据）

**爬取方式**: 页面解析（需处理反爬）  
**频率**: 季度  
**数据用途**: 市场规模、增长率、趋势分析

| 来源 | 品类 | URL |
|------|------|-----|
| Grand View Research | TENS设备 | https://www.grandviewresearch.com/industry-analysis/tens-device-market |
| Grand View Research | 热疗产品 | https://www.grandviewresearch.com/industry-analysis/hot-compress-market |
| Grand View Research | 坐垫 | https://www.grandviewresearch.com/industry-analysis/seat-cushion-market |
| Future Market Insights | 夜灯 | https://www.futuremarketinsights.com/reports/night-light-market |
| Future Market Insights | 药盒 | https://www.futuremarketinsights.com/reports/pill-organizer-market |
| Verified Market Research | 夜灯 | https://www.verifiedmarketresearch.com/product/night-light-market/ |

### 2.10 新闻/Press Release（专业媒体评估）

**爬取方式**: Google News RSS 或 News API  
**频率**: 每日  
**数据用途**: 行业新闻、新品发布、权威媒体报道

| 品类 | Google News RSS URL |
|------|---------------------|
| 电疗TENS | https://news.google.com/rss/search?q=TENS+unit+device&hl=en-US&gl=US&ceid=US:en |
| 热疗 | https://news.google.com/rss/search?q=heating+pad+heat+therapy&hl=en-US&gl=US&ceid=US:en |
| 夜灯 | https://news.google.com/rss/search?q=night+light+LED&hl=en-US&gl=US&ceid=US:en |
| 药盒 | https://news.google.com/rss/search?q=pill+organizer+medication&hl=en-US&gl=US&ceid=US:en |
| 坐垫 | https://news.google.com/rss/search?q=seat+cushion+ergonomic&hl=en-US&gl=US&ceid=US:en |

---

## 三、爬取架构建议（供后续设计参考）

### 3.1 优先级分层

| 优先级 | 数据源类型 | 更新频率 | 说明 |
|--------|-----------|----------|------|
| P0 | Amazon搜索/Best Sellers | 每日 | 爆品发现、价格监控、新品上架 |
| P0 | Google Trends | 每日 | 搜索趋势变化 |
| P1 | Reddit搜索 | 每日 | 真实用户讨论、痛点发现 |
| P1 | Google News RSS | 每日 | 新闻/Press Release |
| P2 | YouTube搜索 | 每日 | KOL测评视频热度 |
| P2 | TikTok搜索 | 每日 | 短视频爆品趋势 |
| P2 | X/Twitter搜索 | 每日 | 实时舆情 |
| P3 | 市场研究报告 | 季度 | 行业数据 |
| P4 | Wikipedia | 月度 | 基础知识更新 |
| P4 | 权威医疗网站 | 季度 | 专业背书更新 |

### 3.2 跳转链接需求（业务同事需求）

当发现热点或爆品时，需要提供直接跳转链接。以下是每种源的跳转链接格式：

| 来源 | 跳转链接模板 | 示例 |
|------|-------------|------|
| Amazon搜索 | `https://www.amazon.com/s?k={keyword}` | https://www.amazon.com/s?k=TENS+unit |
| Amazon商品 | `https://www.amazon.com/dp/{ASIN}` | https://www.amazon.com/dp/B0XXXXX |
| Google Trends | `https://trends.google.com/trends/explore?q={keyword}` | https://trends.google.com/trends/explore?q=TENS%20unit |
| Reddit搜索 | `https://www.reddit.com/r/{sub}/search/?q={keyword}&sort=new` | https://www.reddit.com/r/ChronicPain/search/?q=TENS&sort=new |
| YouTube搜索 | `https://www.youtube.com/results?search_query={keyword}` | https://www.youtube.com/results?search_query=TENS+unit+review |
| TikTok搜索 | `https://www.tiktok.com/search?q={keyword}` | https://www.tiktok.com/search?q=tens+unit |
| X/Twitter | `https://twitter.com/search?q={keyword}&f=live` | https://twitter.com/search?q=%22TENS%20unit%22&f=live |
| Google News | `https://news.google.com/rss/search?q={keyword}&hl=en-US&gl=US&ceid=US:en` | — |

### 3.3 技术注意事项

1. **Amazon反爬**: Amazon有较强的反爬机制，建议使用浏览器自动化（Playwright/Puppeteer）或第三方API（如Rainforest API、Keepa API）
2. **Reddit API**: 需注册 https://www.reddit.com/prefs/apps 获取OAuth凭证，使用PRAW库
3. **Google Trends**: 非官方API，使用pytrends库，注意频率限制
4. **YouTube**: 需注册Google Cloud获取YouTube Data API v3密钥
5. **TikTok**: 官方Research API需申请，或使用浏览器自动化
6. **X/Twitter**: API v2需付费，免费版极其有限
7. **Google News RSS**: 免费可用，无需认证
8. **Wikipedia API**: 完全免费，无需认证，无频率限制
