# 话题扫描：趋势/讨论模式（无选品数据）

## 背景

话题如「运动水杯」不在百科品类库中时，旧逻辑仍把全库 Amazon（药盒等）喂给模型，校验又只认「URL 是否真实」，导致水杯文案挂药盒链接。

## 方案

采用「方案 2」：

1. 话题模式**不再注入**其他品类 Amazon/YouTube/Reddit 商品
2. 库内无选品数据时，轻量拉取 **Bing News RSS + Google Suggest**
3. 进入 `insight_mode=trends_discussion`，强制只能引用公开新闻 URL
4. UI / report 给出友好提示：暂无选品推荐，现阶段为趋势与讨论

## 用户可见文案

> 暂无「{topic}」的选品推荐数据（库内无对应商品/ASIN）。现阶段仅提供趋势与公开讨论/新闻参考，选品链路将在后续完善。

## 无链接卡片补链

校验阶段 `_validate_and_fix_links` 在 `trends_discussion` 下：

1. 只保留本次 `live_news` / `topic_links` 中的真实 URL（禁止 Amazon `/dp/`）
2. 卡片无链接时，按关键词与新闻标题做宽松匹配补新闻链
3. 仍无匹配时，补可点击的 **Google 搜索** / **Bing 新闻搜索** 入口（不是假商品页）

`data_snapshot` 会持久化 `live_news` / `topic_links`，便于事后审计与补链。

## 风险说明

- 未同步爬 Amazon，封 IP 风险低
- 公开源可能为空（网络/限流），此时 LLM 应承认证据不足
- 搜索入口是「可继续调研」链接，不是已验证的商品购买页
