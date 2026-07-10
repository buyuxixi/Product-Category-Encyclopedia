from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Category, ListingSnapshot, SourceMaterial


@dataclass(frozen=True)
class DraftSuggestion:
    section_key: str
    title: str
    content: str
    evidence_listing_ids: list[int]
    evidence_source_ids: list[int]
    missing_evidence: bool = False


def _latest_unique_listings(
    db: Session, category_id: int, limit: int, listing_ids: list[int] | None = None
) -> list[ListingSnapshot]:
    if listing_ids:
        return db.scalars(
            select(ListingSnapshot)
            .where(
                ListingSnapshot.category_id == category_id,
                ListingSnapshot.id.in_(set(listing_ids)),
            )
            .order_by(desc(ListingSnapshot.scraped_at), ListingSnapshot.asin)
            .limit(limit)
        ).all()
    rows = db.scalars(
        select(ListingSnapshot)
        .where(ListingSnapshot.category_id == category_id)
        .order_by(desc(ListingSnapshot.scraped_at), ListingSnapshot.asin)
        .limit(limit * 3)
    ).all()
    unique: dict[str, ListingSnapshot] = {}
    for row in rows:
        unique.setdefault(row.asin, row)
        if len(unique) >= limit:
            break
    return list(unique.values())


def _topic_counts(listings: list[ListingSnapshot]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for listing in listings:
        topics = listing.customers_say.get("topics", []) if listing.customers_say else []
        if not isinstance(topics, list):
            continue
        for topic in topics:
            if not isinstance(topic, dict):
                continue
            name = str(topic.get("name") or "").strip()
            mentions = topic.get("mention_count") or 0
            if name:
                try:
                    counter[name] += int(mentions)
                except (TypeError, ValueError):
                    counter[name] += 1
    return counter


def _format_items(items: list[str]) -> str:
    return "、".join(items) if items else "暂无"


def generate_draft(
    db: Session,
    category: Category,
    limit: int = 100,
    listing_ids: list[int] | None = None,
    source_material_ids: list[int] | None = None,
) -> dict[str, Any]:
    listings = _latest_unique_listings(db, category.id, limit, listing_ids)
    requested_source_ids = set(source_material_ids or [])
    sources = db.scalars(
        select(SourceMaterial)
        .where(
            SourceMaterial.category_id == category.id,
            SourceMaterial.id.in_(requested_source_ids),
        )
    ).all() if requested_source_ids else []
    if len(sources) != len(requested_source_ids):
        raise ValueError("Selected source materials must belong to the selected category")
    evidence_ids = [item.id for item in listings[:20]]
    evidence_source_ids = [item.id for item in sources]
    if not listings:
        missing = [
            DraftSuggestion(
                section_key=key,
                title=title,
                content="暂无可用 Listing 数据，请先导入或补充来源材料。",
                evidence_listing_ids=[],
                evidence_source_ids=evidence_source_ids,
                missing_evidence=True,
            )
            for key, title in [
                ("definition", "品类定义与边界"),
                ("users", "用户画像与使用场景"),
                ("needs", "用户需求与品类痛点"),
                ("technology", "技术、材料与设计原则"),
                ("trends", "新兴趋势"),
                ("market", "舆情与市场趋势"),
            ]
        ]
        return {"listing_count": 0, "suggestions": [asdict(item) for item in missing]}

    brands = Counter(item.brand for item in listings if item.brand)
    prices = [item.current_price for item in listings if item.current_price is not None]
    ratings = [item.rating_value for item in listings if item.rating_value is not None]
    topics = _topic_counts(listings)
    latest_date = max(item.scraped_at for item in listings).date().isoformat()
    top_brands = [name for name, _ in brands.most_common(5)]
    top_topics = [name for name, _ in topics.most_common(8)]

    material_terms: Counter[str] = Counter()
    feature_terms: Counter[str] = Counter()
    for listing in listings:
        combined = {**(listing.product_info or {}), **(listing.attributes or {})}
        for key, value in combined.items():
            key_lower = str(key).lower()
            if "material" in key_lower or "fabric" in key_lower:
                material_terms[str(value)] += 1
            if "feature" in key_lower or "use" in key_lower:
                feature_terms[str(value)] += 1

    price_text = (
        f"样本价格范围为 {min(prices):.2f}-{max(prices):.2f} USD"
        if prices
        else "样本暂缺稳定价格"
    )
    rating_text = f"平均评分约 {mean(ratings):.1f}" if ratings else "评分数据不足"

    suggestions = [
        DraftSuggestion(
            section_key="definition",
            title="品类定义与边界",
            content=(
                f"{category.name}属于{category.parent.name + '品类' if category.parent else '独立一级品类'}。"
                f"当前业务定义为：{category.description}\n\n"
                f"包含：{_format_items(category.included_items)}。\n"
            f"排除：{_format_items(category.excluded_items)}。"
            ),
            evidence_listing_ids=evidence_ids,
            evidence_source_ids=evidence_source_ids,
        ),
        DraftSuggestion(
            section_key="users",
            title="用户画像与使用场景",
            content=(
                "### 用户画像\n"
                f"- **消费能力推断**：{price_text}，{rating_text}。"
                "价格分布可间接反映用户的消费能力区间，但不应等同于精确收入画像。\n"
                f"- **品牌偏好**：Top 5 品牌为 {_format_items(top_brands)}，"
                "品牌集中度可反映用户对品牌的认知和信任倾向。\n"
                f"- **关注焦点**：评论高频主题包括 {_format_items(top_topics[:5])}，"
                "可间接推断用户群体的核心关注点，但需结合用户访谈验证。\n"
                "- **人口画像**：Amazon 数据无法直接提取年龄/性别信息，"
                "不应使用\"老年人、青年人、女性\"等过于宽泛的群体描述。"
                "建议通过社媒聆听和用户调研补充精确画像。\n\n"
                "### 品类使用场景\n"
                f"- **可识别场景**：从 Listing 标题和卖点可初步提取的使用场景包括 {_format_items([k for k, _ in feature_terms.most_common(5)])}。\n"
                "- **场景细化**：不应使用\"室内、室外\"等过于宽泛的场景描述。"
                "需结合 bullet points 和 Q&A 进一步提取具体使用场景。\n"
                "- **场景验证**：以上场景基于 Amazon 数据推断，需通过用户访谈和社媒讨论验证。"
            ),
            evidence_listing_ids=evidence_ids,
            evidence_source_ids=evidence_source_ids,
            missing_evidence=True,
        ),
        DraftSuggestion(
            section_key="needs",
            title="用户需求与品类痛点",
            content=(
                "### 用户基本需求\n"
                f"- **功能需求**：从 Listing 标题和卖点可初步识别的核心功能包括 {_format_items(top_topics[:4])}。\n"
                "- **场景需求**：现有数据不足以精确提取场景需求，需结合用户访谈验证。\n"
                "- **社会需求**：Amazon 评论中暂无可直接提取的社会认同类需求，需社媒数据补充。\n"
                "- **潜在需求**：评论主题中的低频长尾话题可能反映潜在需求，需进一步定性分析。\n\n"
                "### 消费者购买决策路径\n"
                f"- **需求认知**：用户搜索关键词中可观察到 {_format_items(top_topics[:3])} 等关注点。\n"
                "- **信息搜索**：Amazon BSR 排名和评论数可反映搜索阶段的热度分布。\n"
                "- **方案评估**：Top 品牌集中度可间接反映评估阶段的选择范围，"
                f"当前样本 Top 5 品牌为 {_format_items(top_brands)}。\n"
                "- **购买决策**：价格区间和评分分布是影响最终决策的关键指标，"
                f"当前 {price_text}，{rating_text}。\n"
                "- **购后行为**：评论主题和退货率数据可反映购后行为，需后续补充。\n\n"
                "### 用户使用旅程\n"
                "- **拆包与安装**：Amazon Q&A 中可能有安装类问题，需后续提取分析。\n"
                "- **试用**：初期评论中的体验反馈可参考，但样本不足以形成结论。\n"
                "- **长时间使用**：长周期耐用性数据暂缺，需多期快照对比。\n"
                "- **用后维护与管理**：维护类需求暂无数据支撑。\n\n"
                "### 品类痛点与常见问题\n"
                f"评论主题聚合中较高频的关注点包括：{_format_items(top_topics)}。\n"
                "这些主题可作为需求假设和后续原始 Review 抽样方向，不应直接等同于完整用户结论。"
                "建议结合搜索趋势数据（如\"tens 贴片如何延长寿命\"类长尾搜索词）进一步识别用户痛点。"
            ),
            evidence_listing_ids=evidence_ids,
            evidence_source_ids=evidence_source_ids,
            missing_evidence=not bool(top_topics),
        ),
        DraftSuggestion(
            section_key="technology",
            title="技术、材料与设计原则",
            content=(
                "### 品类核心技术与作用机制\n"
                f"- 样本中可提取的功能/技术关键词包括：{_format_items([k for k, _ in feature_terms.most_common(5)])}。\n"
                "- 核心技术的作用机制和医疗健康表述仍需专业来源与人工审核，"
                "不应直接从 Listing 卖点词推断技术原理。\n\n"
                "### 材料科学\n"
                f"- 样本中可提取的材料信息包括：{_format_items([k for k, _ in material_terms.most_common(5)])}。\n"
                "- 材料的安全性和性能声明需参考权威来源（如 NIOSH、FDA 等），"
                "不应仅凭 Amazon 商品信息得出材料科学结论。"
            ),
            evidence_listing_ids=evidence_ids,
            evidence_source_ids=evidence_source_ids,
            missing_evidence=not bool(material_terms or feature_terms),
        ),
        DraftSuggestion(
            section_key="trends",
            title="新兴趋势",
            content=(
                "### 技术发展趋势\n"
                "- 当前只有单次 Amazon Listing 快照，不能据此判断技术演进趋势。\n"
                "- 建议后续补充多期快照对比，观察材料、功能关键词的变化。\n\n"
                "### 消费者偏好趋势\n"
                f"- 当前评论高频主题包括：{_format_items(top_topics[:5])}。\n"
                "- 单次快照无法反映偏好变化方向，需多期数据对比才能识别上升/下降趋势。\n\n"
                "### 新兴子品类\n"
                "- 需结合 Google Trends 搜索量变化、Amazon 新品上架数据综合判断。\n"
                "- 当前数据不足以识别新兴子品类，标注为待补充。"
            ),
            evidence_listing_ids=evidence_ids,
            evidence_source_ids=evidence_source_ids,
            missing_evidence=True,
        ),
        DraftSuggestion(
            section_key="market",
            title="舆情与市场趋势",
            content=(
                "### 行业与消费者术语\n"
                "- 需对比品类内部的技术用语与消费者用语，当前数据不足以完成术语对比。\n"
                "- 可从 Listing bullet points 提取技术用语，从评论主题提取消费者用语，需人工标注。\n\n"
                "### 高频关键词/话题\n"
                f"- Amazon 评论高频主题：{_format_items(top_topics)}。\n"
                "- 谷歌搜索趋势、谷歌关键词趋势、谷歌问题趋势数据尚未接入，标注为待补充。\n\n"
                "### 社区讨论总结\n"
                "- 尚未接入 Reddit、Facebook、X、TikTok、YouTube 等社媒数据。\n"
                "- 当前不输出跨平台舆情结论。\n\n"
                "### 专业媒体评估\n"
                "- 尚未接入 Press Release、VS Article 等权威媒体或高 DR 外链文章。\n"
                + (f"- 已选择的补充材料：{_format_items([item.title for item in sources])}。\n" if sources else "- 暂无补充来源材料。\n")
            ),
            evidence_listing_ids=evidence_ids,
            evidence_source_ids=evidence_source_ids,
            missing_evidence=True,
        ),
    ]
    return {"listing_count": len(listings), "suggestions": [asdict(item) for item in suggestions]}
