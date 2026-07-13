export type Category = {
  slug: string;
  index: string;
  name: string;
  english: string;
  descriptor: string;
  summary: string;
  status: string;
  statusTone: "mint" | "amber" | "coral" | "blue";
  tags: string[];
  metrics: { label: string; value: string }[];
  definition: string;
  scenarios: string[];
  questions: string[];
  sources: string[];
};

export const categories: Category[] = [
  {
    slug: "heat-therapy",
    index: "01",
    name: "热敷理疗",
    english: "RECOVERY",
    descriptor: "温感、压力与缓释节奏",
    summary: "先理解热量如何到达，再决定哪种形态适合日常恢复。",
    status: "重点研究",
    statusTone: "coral",
    tags: ["温度管理", "慢性疼痛", "家庭使用"],
    metrics: [
      { label: "核心变量", value: "温度 / 覆盖" },
      { label: "典型形态", value: "热敷垫 / 热水袋" },
      { label: "研究条目", value: "18 条" },
    ],
    definition:
      "热敷理疗产品通过热能传递、覆盖面积与使用时长，帮助用户建立可控的温感体验。品类比较时，安全边界、控温方式与身体贴合度比单一的最高温度更值得关注。",
    scenarios: ["久坐后的局部放松", "运动后的日常恢复", "需要可调节温度的家庭护理"],
    questions: ["是否支持分区或定时控温？", "热源是否均匀，边缘会不会过热？", "覆盖面积与收纳方式是否匹配使用频率？"],
    sources: ["Heating pad / 热敷垫", "Thermotherapy / 热疗", "Warm compress / 热敷"],
  },
  {
    slug: "electrical-stimulation",
    index: "02",
    name: "电刺激设备",
    english: "STIMULATION",
    descriptor: "脉冲、贴合与强度控制",
    summary: "分清 TENS 与 EMS，理解电流、强度和适用边界。",
    status: "已整理",
    statusTone: "blue",
    tags: ["TENS", "EMS", "贴片"],
    metrics: [
      { label: "核心变量", value: "频率 / 波形" },
      { label: "典型形态", value: "主机 / 贴片" },
      { label: "研究条目", value: "14 条" },
    ],
    definition:
      "电刺激设备用低电流脉冲作用于皮肤或肌肉，产品体验由波形、频率、强度调节、贴片面积和操作反馈共同决定。教育内容应清楚区分不同使用目的，避免把参数简单等同于效果。",
    scenarios: ["需要细分强度的个人护理", "便携式日常训练辅助", "关注贴片耗材与复购成本"],
    questions: ["TENS、EMS 的定位是否写清楚？", "强度调节是否足够细，是否有过载保护？", "贴片寿命、替换成本与清洁方式如何？"],
    sources: ["TENS device / TENS 设备", "Neurostimulation / 神经刺激", "Electrical stimulation / 电刺激"],
  },
  {
    slug: "sleep-lighting",
    index: "03",
    name: "助眠照明",
    english: "NIGHT CARE",
    descriptor: "色温、时序与入睡环境",
    summary: "从色温与亮度出发，建立更接近真实夜间使用的判断框架。",
    status: "持续更新",
    statusTone: "mint",
    tags: ["色温", "昼夜节律", "智能灯光"],
    metrics: [
      { label: "核心变量", value: "照度 / 色温" },
      { label: "典型形态", value: "夜灯 / 智能灯" },
      { label: "研究条目", value: "16 条" },
    ],
    definition:
      "助眠照明关注夜间环境中的光谱、亮度、照射时间和使用距离。好的品类研究会把参数翻译为可感知的场景：起夜、阅读、入睡前和清晨唤醒。",
    scenarios: ["起夜时需要低干扰照明", "睡前阅读与放松", "希望把灯光纳入家庭自动化"],
    questions: ["最低亮度是否真的足够低？", "色温变化与定时策略是否容易理解？", "传感器、连接协议和断网体验如何？"],
    sources: ["Night light / 夜灯", "Smart lighting / 智能照明", "Circadian rhythm / 昼夜节律"],
  },
  {
    slug: "medication-management",
    index: "04",
    name: "药品管理",
    english: "MEDICATION",
    descriptor: "提醒、分类与用药安全",
    summary: "把提醒、分类和存放，变成不容易出错的日常习惯。",
    status: "持续更新",
    statusTone: "amber",
    tags: ["提醒", "分类", "家庭秩序"],
    metrics: [
      { label: "核心变量", value: "提醒 / 可见性" },
      { label: "典型形态", value: "分药盒 / 提醒器" },
      { label: "研究条目", value: "12 条" },
    ],
    definition:
      "药品管理品类围绕分装、标识、提醒与记录展开。判断一个产品是否有用，不只看容量和格数，也要看视认性、误拿风险、清洁方式以及家人协作的可操作性。",
    scenarios: ["多时间段用药提醒", "照护者与家庭成员协作", "旅行中的便携分类与核对"],
    questions: ["不同日期、时段是否容易混淆？", "打开和确认动作是否有清晰反馈？", "是否明确提示遵从医嘱与储存要求？"],
    sources: ["Medication organizer / 分药盒", "Medication adherence / 用药依从", "Medication error / 用药错误"],
  },
  {
    slug: "posture-health",
    index: "05",
    name: "坐姿健康",
    english: "POSTURE",
    descriptor: "支撑、角度与视线高度",
    summary: "从支撑点与视线高度出发，理解坐垫、靠垫的真实差异。",
    status: "已整理",
    statusTone: "mint",
    tags: ["人体工学", "支撑", "久坐"],
    metrics: [
      { label: "核心变量", value: "角度 / 支撑" },
      { label: "典型形态", value: "坐垫 / 腰靠" },
      { label: "研究条目", value: "11 条" },
    ],
    definition:
      "坐姿健康产品通过改变受力分布、支撑位置与视线关系，帮助用户构建更舒适的工作或休息姿势。研究时应把产品尺寸、座椅高度和使用时长放在一起看。",
    scenarios: ["居家办公的长时间坐姿", "需要减轻局部压力的座椅", "桌面与屏幕高度不易调整"],
    questions: ["支撑是否会把身体推到不自然的角度？", "尺寸是否匹配不同椅型与身高？", "久坐后是否方便调整或移动？"],
    sources: ["Seat cushion / 坐垫", "Orthopedic cushion / 矫形坐垫", "Ergonomics / 人体工学"],
  },
];

export const glossary = [
  { term: "色温", note: "光线的冷暖感，常以 K 表示" },
  { term: "照度", note: "落在表面上的光通量，单位为 lux" },
  { term: "TENS", note: "经皮神经电刺激的缩写" },
  { term: "EMS", note: "肌肉电刺激的缩写" },
  { term: "昼夜节律", note: "与光照和时间有关的生理节奏" },
  { term: "人体工学", note: "让工具与环境更贴合人的工作方式" },
  { term: "热疗", note: "利用热量进行局部护理的方式" },
  { term: "用药依从", note: "按约定方式、剂量和时间使用药物" },
];
