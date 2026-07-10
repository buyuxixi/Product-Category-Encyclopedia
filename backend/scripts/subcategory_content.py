"""Populate FAR_INFRARED and SHOULDER_NECK_HEAT_THERAPY sub-category sections."""

SECTIONS = {}

# ── 远红外热疗 (FAR_INFRARED) ──
SECTIONS["FAR_INFRARED"] = {
    "definition": """### 1.1 品类名称与定义
**品类名称**: 远红外热疗（Far-infrared Therapy）
**定义**: 热疗下以远红外材料、辐射或相关作用机制为核心卖点的子品类。远红外辐射（波长4-1000μm）可直接穿透皮肤至深层组织（可达3-5cm深度），直接加热血管毛细血管和神经末梢所在区域，比接触式热传导更高效。

### 1.2 产品类型
| 类型 | 描述 | 远红外机制 | 典型温度 |
|------|------|-----------|----------|
| 远红外加热垫 | 含远红外材料（石墨烯/生物陶瓷）的加热垫 | 远红外辐射 | 40-50°C |
| 石墨烯热敷带 | 石墨烯发热膜，超薄柔性 | 石墨烯远红外发射 | 40-55°C |
| 远红外热疗灯 | 台灯式远红外照射设备 | 远红外光源 | 可调 |
| 远红外暖宫带 | 腹部专用远红外热敷 | 生物陶瓷/石墨烯 | 40-50°C |

### 1.3 产品边界
**包含**: 带远红外材料或远红外发热声明的热疗产品（含石墨烯、生物陶瓷等远红外发射材料）
**排除**: 仅普通电阻发热且无远红外材料/机制的产品、桑拿设备/远红外桑拿房（非便携消费级）""",

    "users": """### 2.1 用户画像
1. **深层组织疼痛患者**
   - 特征: 慢性肌肉/关节深层疼痛，普通热敷无法触及深层
   - 行为: 寻求"穿透更深"的远红外产品
   - 需求: 可验证的远红外发射效果
2. **高端健康消费者**
   - 特征: 追求材料升级（石墨烯等新材料），愿为远红外概念付费
   - 行为: 关注产品材料参数和远红外发射率
   - 需求: 品质感、科技感、品牌背书
3. **关节炎患者**
   - 特征: 骨关节炎/类风湿性关节炎，需要深层热疗缓解关节僵硬
   - 行为: 晨起关节僵硬时使用远红外加热垫
   - 需求: 针对关节形状设计、深层穿透

### 2.2 品类使用场景
| 场景 | 描述 | 典型产品 |
|------|------|----------|
| 居家深层热疗 | 躺在沙发/床上使用远红外加热垫进行深层热疗 | 远红外加热垫 |
| 办公期间关节热敷 | 在工位上使用远红外热敷wrap缓解关节僵硬 | 石墨烯热敷带 |
| 经期腹部深层热敷 | 穿戴远红外暖宫带进行深层热敷 | 远红外暖宫带 |""",

    "needs": """### 3.1 用户基本需求
**功能需求**:
- 远红外深层穿透效果（宣称3-5cm深度）
- 温度可调，均匀加热
- 远红外发射率可验证
**场景需求**: 居家固定使用 + 便携穿戴
**社会需求**: 高端健康投资、科技材料追求
**潜在需求**: 远红外发射率检测认证、可信赖的科普教育

### 3.2 消费者购买决策路径
| 阶段 | 行为特征 | 关键触点 |
|------|----------|----------|
| 需求认知 | 深层疼痛/关节僵硬，寻求远红外概念产品 | 社交媒体科普、医生建议 |
| 信息搜索 | "far infrared heating pad" / "graphene heating pad" | Amazon、Google、YouTube |
| 方案评估 | 对比远红外材料（石墨烯vs生物陶瓷）、温度档位、价格 | Amazon评论、YouTube测评 |
| 购买决策 | $80-$200（远红外/智能定位） | Amazon Prime |
| 购后行为 | 远红外效果验证需求强烈 | Amazon评论、社交媒体分享 |

### 3.3 用户使用旅程
| 阶段 | 行为 | 痛点/需求点 |
|------|------|-------------|
| 拆包 | 打开包装，检查远红外材料声明 | 包装宣传与实际效果差距 |
| 安装 | 充电/插电，阅读使用说明 | 充电时间长 |
| 试用 | 选择温度档位，体验远红外热感 | **远红外功效难以验证（核心痛点）**；加热效果与普通产品差异不明显 |
| 长时间使用 | 每日使用20-40分钟 | 远红外效果无法自测；材料耐久性不确定 |
| 维护 | 清洁、收纳 | 远红外材料层清洁不便 |

### 3.4 品类痛点
1. **"far infrared heating pad does it work / real vs fake"** — 🔴 远红外功效难以验证，消费者质疑真伪
2. **"graphene heating pad worth it"** — 石墨烯材料溢价是否值得
3. **"infrared heating pad vs regular heating pad"** — 与普通加热垫的区别不明显""",

    "technology": """### 4.1 品类核心技术与作用机制
**远红外热疗机制**:
- 远红外辐射（波长4-1000μm）直接穿透皮肤至深层组织（可达3-5cm深度）
- 比接触式热传导更高效（不需要通过皮肤外层逐层传导）
- 在相同安全温度上限（约42°C）下，深层组织可达到更高温度
- 直接加热血管毛细血管和神经末梢所在区域

### 4.2 材料科学
**远红外材料**:
| 材料 | 特点 | 远红外发射率 |
|------|------|-------------|
| 石墨烯 | 薄膜状，升温快（3-5秒），柔性好 | >0.90 |
| 生物陶瓷粉 | 混入织物中，吸收体温后发射远红外 | 0.80-0.85 |
| 电气石（Tourmaline） | 天然矿物，需体温触发 | 0.75-0.80 |

**发热材料**: 碳纤维发热布（面状发热，均匀性好）、石墨烯发热膜（超薄、快升温、远红外发射率高）""",

    "trends": """### 5.1 技术发展趋势
1. **石墨烯热疗**: 升温快（3-5秒），远红外发射率高，超薄柔性设计
2. **远红外+红光组合**: 结合远红外热疗和LED红光治疗，双重治疗效应
3. **远红外发射率可视化**: 可穿戴检测传感器，实时显示远红外强度

### 5.2 消费者偏好趋势
- **材料升级**: 远红外/石墨烯成为高端卖点
- **功效验证需求**: 消费者越来越需要可验证的远红外效果

### 5.3 新兴子品类
- **石墨烯热敷系列**: 高端远红外定位
- **远红外暖宫带**: 女性市场细分
- **远红外+红光组合设备**: 双重治疗""",

    "market": """### 6.1 行业与消费者术语对比
| 行业/技术术语 | 消费者用语 | 差异说明 |
|---------------|-----------|----------|
| Far-infrared (FIR) | "infrared heating pad" / "graphene" | 消费者常混淆远红外和红外 |
| Graphene | "graphene" (直接使用) | 已成为营销关键词 |
| Emissivity | "does it really emit FIR" | 消费者关注是否真有效果 |
| Wavelength 4-1000μm | "deep heat" / "penetrating heat" | 消费者用效果描述 |

### 6.2 高频关键词/话题
| 关键词 | 搜索趋势 | 备注 |
|--------|----------|------|
| "far infrared heating pad" | 新兴增长 | 高端定位 |
| "graphene heating pad" | 快速增长 | 新材料 |
| "infrared heating pad benefits" | 稳定需求 | 功效科普 |

> 📊 [Google Trends: infrared heating pad](https://trends.google.com/trends/explore?q=infrared%20heating%20pad) · [Amazon: far infrared heating pad](https://www.amazon.com/s?k=far+infrared+heating+pad)

### 6.3 社区讨论总结
| 平台 | 社区/频道 | 讨论方向 |
|------|----------|----------|
| Reddit | r/ChronicPain | 远红外热疗 vs 普通加热垫效果对比 |
| YouTube | "infrared heating pad review" | 远红外产品测评 |
| YouTube | "graphene heating pad" | 石墨烯热敷测评 |
| TikTok | "graphene heating pad" | 石墨烯热敷趋势 |

> 🔗 [YouTube: infrared heating pad](https://www.youtube.com/results?search_query=infrared+heating+pad) · [TikTok: graphene heating pad](https://www.tiktok.com/search?q=graphene+heating+pad)

### 6.4 专业媒体评估
| 媒体来源 | 评估内容 |
|---------|----------|
| Wikipedia | 远红外辐射可直接加热深层组织，比接触式传导更高效 |
| Harvard Health | 认可热疗对肌肉疼痛和关节僵硬的效果 |

> 📰 [Google News: infrared heating pad](https://news.google.com/rss/search?q=infrared+heating+pad&hl=en-US&gl=US&ceid=US:en)

> 来源: [Wikipedia - Infrared heater](https://en.wikipedia.org/wiki/Infrared_heater) · [Arthritis Foundation](https://www.arthritis.org)""",
}

# ── 肩颈热敷 (SHOULDER_NECK_HEAT_THERAPY) ──
SECTIONS["SHOULDER_NECK_HEAT_THERAPY"] = {
    "definition": """### 1.1 品类名称与定义
**品类名称**: 肩颈热敷（Shoulder & Neck Heat Therapy）
**定义**: 热疗下针对肩部、颈部和上背部使用场景的加热产品子品类。以定向加热、人体工学包裹为设计核心，通过热敷缓解颈肩部位肌肉紧张和疼痛。

### 1.2 产品类型
| 类型 | 描述 | 供热方式 | 典型温度 |
|------|------|----------|----------|
| 肩颈热敷wrap | 穿戴式包裹，覆盖肩颈区域 | 碳纤维/电阻丝 | 40-55°C |
| 颈部加热护具 | U型颈枕式加热 | 电阻丝 | 40-50°C |
| 肩部加热披肩 | 披肩式覆盖整个肩部 | 碳纤维面发热 | 40-55°C |
| 可充电颈贴 | 小型贴片式颈部加热 | 锂电池+发热片 | 40-45°C |

### 1.3 产品边界
**包含**: 肩部、颈部或上背部定向加热产品
**排除**: 不带加热能力的普通颈枕或按摩器""",

    "users": """### 2.1 用户画像
1. **久坐颈肩疼痛办公族**
   - 特征: 每天坐8小时以上，颈肩僵硬酸痛
   - 行为: 在办公期间穿戴肩颈热敷wrap，不干扰工作
   - 需求: 便携、可充电、静音、外观低调
2. **颈椎病患者**
   - 特征: 颈椎间盘突出/退行性病变，颈部活动受限伴疼痛
   - 行为: 遵医嘱进行颈部热敷缓解
   - 需求: 颈部贴合设计、温度可控、医疗级安全
3. **家务劳动者**
   - 特征: 长期做家务导致肩部劳损疼痛
   - 行为: 休息时使用肩部加热披肩
   - 需求: 大面积覆盖、舒适包裹

### 2.2 品类使用场景
| 场景 | 描述 | 典型产品 |
|------|------|----------|
| 办公期间颈肩热敷 | 在工位上穿戴wrap，不影响工作 | 肩颈热敷wrap |
| 居家休息肩部热疗 | 沙发上使用披肩式加热 | 肩部加热披肩 |
| 睡前颈部放松 | 床上使用颈枕式加热 | 颈部加热护具 |
| 旅行途中颈肩缓解 | 使用便携充电颈贴 | 可充电颈贴 |""",

    "needs": """### 3.1 用户基本需求
**功能需求**:
- 精准覆盖肩颈区域（人体工学设计）
- 温度可调，多档位
- 快速升温，均匀加热
- 可穿戴，活动不受限
**场景需求**: 办公/居家/旅行多场景便携
**社会需求**: 自我健康管理、关爱长辈礼物
**潜在需求**: 热敷+按摩组合、App控温

### 3.2 消费者购买决策路径
| 阶段 | 行为特征 | 关键触点 |
|------|----------|----------|
| 需求认知 | 颈肩疼痛发作；季节转换导致僵硬加剧 | 自我感知、社交媒体推荐 |
| 信息搜索 | "neck heat wrap" / "shoulder heating pad" | Amazon、Google、YouTube |
| 方案评估 | 对比包裹面积、温度档位、续航、材质、价格 | Amazon评论、YouTube对比 |
| 购买决策 | $15-$60（普通）到$80-$150（智能/远红外） | Amazon Prime |
| 购后行为 | 体验包裹贴合度和加热效果 | Amazon评论、送礼场景 |

### 3.3 用户使用旅程
| 阶段 | 行为 | 痛点/需求点 |
|------|------|-------------|
| 拆包 | 打开包装，检查wrap和配件 | 包装气味（新塑料/橡胶味） |
| 安装 | 充电/插电，穿戴到肩颈部位 | 充电时间长；穿戴方式不直观 |
| 试用 | 选择温度档位，体验热感和包裹感 | **wrap尺寸不贴合不同体型（核心痛点）**；温度过高/过低不可调；加热不均匀 |
| 长时间使用 | 每日使用20-40分钟 | **电池续航不足**；魔术贴粘性下降；加热速度变慢 |
| 维护 | 清洁wrap表面，充电收纳 | 清洁不便（不可水洗内机）；线缆缠绕 |

### 3.4 品类痛点
1. **"neck shoulder heat wrap sizing / fit"** — 🔴 wrap尺寸不合适不同体型用户
2. **"rechargeable heat wrap battery life"** — 🔴 可充电产品续航不足
3. **"heating pad auto shut off / safety"** — 过热、烫伤、忘关
4. **"neck heat wrap too tight / too loose"** — 包裹不舒适""",

    "technology": """### 4.1 品类核心技术与作用机制
**热疗机制（通用）**:
1. **血管扩张**: 热量引起局部血管扩张，增加血流量，输送氧气和营养
2. **肌肉痉挛缓解**: 热量降低肌肉张力，缓解痉挛和紧张性疼痛
3. **胶原组织延展性增加**: 减少关节僵硬
4. **疼痛门控**: 热刺激竞争性抑制疼痛信号

**肩颈专用设计**:
- 人体工学包裹：U型颈部贴合+肩部覆盖面积设计
- 可调节松紧度：魔术贴/卡扣适应不同体型
- 定向加热：发热区域集中在颈肩肌肉群

### 4.2 材料科学
| 部件 | 材料 | 说明 |
|------|------|------|
| 发热体 | 碳纤维发热布 | 面状均匀发热，可弯曲 |
| 外层面料 | 摇粒绒/珊瑚绒 | 保暖舒适 |
| 内层 | Neoprene/棉+氨纶 | 弹性好，包裹性强 |
| 防滑 | 硅胶防滑点 | 底面防滑 |
| 电池 | 锂电池 3.7-7.4V | 可充电""",

    "trends": """### 5.1 技术发展趋势
1. **智能肩颈热敷**: App蓝牙控温、多档预设、使用数据记录
2. **快充和长续航**: Type-C快充、大容量电池支持60分钟+
3. **热敷+按摩组合**: 热疗配合振动按摩
4. **热敷+TENS组合**: 同时提供热疗和电刺激

### 5.2 消费者偏好趋势
- **便携化**: 从插电式向可充电穿戴式转变
- **美观化**: 从医疗外观向时尚配件转变
- **分场景专用化**: 颈/肩/腰/膝专用设计
- **送礼属性**: 节日送礼需求明显（Q4旺季）

### 5.3 新兴子品类
- **暖宫带专用腹部热敷**: 女性市场细分
- **热敷+按摩组合**: 热疗+振动
- **可水洗热敷wrap**: 模块化设计""",

    "market": """### 6.1 行业与消费者术语对比
| 行业/技术术语 | 消费者用语 | 差异说明 |
|---------------|-----------|----------|
| Heat wrap | "neck wrap" / "shoulder pad" | 消费者用部位描述 |
| Carbon fiber heating | "even heating" / "no hot spots" | 消费者关注结果 |
| Neoprene | "soft material" / "comfortable fit" | 消费者用感受描述 |

### 6.2 高频关键词/话题
| 关键词 | 搜索趋势 | 备注 |
|--------|----------|------|
| "neck and shoulder heating pad" | 稳定增长 | 部位专用 |
| "heat wrap neck shoulder" | 持续高搜索 | 核心词 |
| "rechargeable neck heat wrap" | 快速增长 | 便携需求 |
| "heating pad for neck pain" | 稳定需求 | 疼痛相关 |

> 📊 [Google Trends: neck heat wrap](https://trends.google.com/trends/explore?q=neck%20heat%20wrap) · [Amazon: heat wrap neck shoulder](https://www.amazon.com/s?k=heat+wrap+neck+shoulder)

### 6.3 社区讨论总结
| 平台 | 社区/频道 | 讨论方向 |
|------|----------|----------|
| Reddit | r/ChronicPain | 颈肩热敷作为日常疼痛管理 |
| Reddit | r/ergonomics | 办公颈肩热敷方案 |
| YouTube | "neck heat wrap review" | 颈部热敷wrap测评 |
| TikTok | "heating pad period" | 经期热敷趋势 |

> 🔗 [Reddit r/ChronicPain: heat therapy](https://www.reddit.com/r/ChronicPain/search/?q=heat+therapy&sort=new) · [YouTube: neck heat wrap review](https://www.youtube.com/results?search_query=neck+heat+wrap+review)

### 6.4 专业媒体评估
| 媒体来源 | 评估内容 |
|---------|----------|
| Harvard Health | 认可热疗对肌肉疼痛和关节僵硬的效果 |
| Arthritis Foundation | 推荐热疗作为关节炎自我管理方案 |

> 📰 [Google News: neck shoulder heat wrap](https://news.google.com/rss/search?q=neck+shoulder+heat+wrap&hl=en-US&gl=US&ceid=US:en)

> 来源: [Arthritis Foundation](https://www.arthritis.org) · [Wikipedia - Heat therapy](https://en.wikipedia.org/wiki/Heat_therapy)""",
}
