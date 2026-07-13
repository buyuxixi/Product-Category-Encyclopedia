from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, EncyclopediaSection


SECTION_DEFINITIONS = [
    ("definition", "品类定义与边界"),
    ("users", "用户画像与使用场景"),
    ("needs", "用户需求与品类痛点"),
    ("technology", "技术、材料与设计原则"),
    ("trends", "新兴趋势"),
    ("market", "舆情与市场趋势"),
]


CATEGORY_SEEDS = [
    {
        "code": "HEAT_THERAPY",
        "name": "热疗",
        "aliases": ["Heat Therapy", "热敷"],
        "included_items": ["远红外热疗", "肩颈热敷"],
        "excluded_items": ["TENS 电疗", "普通非加热护具"],
        "description": "通过热能作用服务于保暖、放松或舒适体验的产品一级品类。",
        "parent_code": None,
    },
    {
        "code": "FAR_INFRARED",
        "name": "远红外热疗",
        "aliases": ["Far-infrared", "FAR_INFRARED", "远红外热敷"],
        "included_items": ["带远红外材料或远红外发热声明的热疗产品"],
        "excluded_items": ["仅普通电阻发热且无远红外材料/机制的产品"],
        "description": "热疗下以远红外材料、辐射或相关作用机制为核心卖点的子品类。",
        "parent_code": "HEAT_THERAPY",
    },
    {
        "code": "SHOULDER_NECK_HEAT_THERAPY",
        "name": "肩颈热敷",
        "aliases": [
            "SUB_SHOULDER_NECK_HEAT_THERAPY",
            "Neck Heat Therapy-Back Heat Therapy",
            "肩颈加热",
        ],
        "included_items": ["肩部、颈部或上背部定向加热产品"],
        "excluded_items": ["不带加热能力的普通颈枕或按摩器"],
        "description": "热疗下针对肩部、颈部和上背部使用场景的加热产品子品类。",
        "parent_code": "HEAT_THERAPY",
    },
    {
        "code": "TENS_THERAPY",
        "name": "电疗 TENS",
        "aliases": ["TENS", "TENS unit", "Transcutaneous Electrical Nerve Stimulation", "经皮神经电刺激"],
        "included_items": ["便携式 TENS 设备", "TENS 电极贴片", "可穿戴 TENS 设备"],
        "excluded_items": ["EMS 电肌肉刺激设备", "微电流治疗设备", "植入式神经刺激器", "普通按摩仪"],
        "description": "通过皮肤表面电极输送微弱电流刺激神经以达到镇痛目的的消费级电子设备品类。",
        "parent_code": None,
    },
    {
        "code": "NIGHT_LIGHT",
        "name": "夜间照明-夜灯",
        "aliases": [
            "Night Light",
            "Nightlight",
            "LED Night Light",
            "Plug-in Night Light",
            "Motion Sensor Night Light",
        ],
        "included_items": [
            "插墙式LED夜灯（含光感/PIR感应）",
            "电池/充电式便携小夜灯",
            "婴儿房专用夜灯",
            "智能夜灯（App/语音控制）",
            "楼梯/走廊感应灯条",
            "磁吸式柜内感应灯",
            "变色/RGB装饰夜灯",
            "投影式夜灯（以夜间辅助照明为主功能）",
            "儿童造型硅胶触摸灯（以夜灯为主功能）",
        ],
        "excluded_items": [
            "普通台灯/落地灯",
            "氛围灯/装饰灯带",
            "庭院灯/太阳能户外灯",
            "小夜灯时钟（以时钟为主功能）",
            "壁灯/吸顶灯",
            "手电筒",
            "灯串（Fairy Lights）",
        ],
        "description": "低功率小型辅助照明设备，以LED为主、插墙/电池/USB供电，用于室内夜间导航、安全防跌倒与安抚陪伴，而非空间主照明。",
        "parent_code": None,
    },
    {
        "code": "MEDICATION_MANAGEMENT",
        "name": "药物管理",
        "aliases": ["Pill Organizer", "Pill Box", "Pill Splitter", "药盒", "切药器"],
        "included_items": [
            "单日便携迷你药盒（1–6格）",
            "7天分格药盒（7–28格）",
            "月度大容量药盒（28–31格）",
            "智能电子药盒",
            "组合款：药盒+切药器二合一",
            "V型/安全/多分切药器",
            "药片碾碎器（Pill Crusher）",
        ],
        "excluded_items": [
            "药品原包装/药瓶",
            "电动研磨器/大功率电动粉碎机",
            "药品注射器/分装工具",
            "管制药品切割工具",
        ],
        "description": "用于按计划存储和分割口服药物剂量的管理工具品类；药盒与切药器为两个独立子品类，同时含收纳仓+刀片的归入组合款。",
        "parent_code": None,
    },
    {
        "code": "SEAT_CUSHION",
        "name": "坐垫健康-办公坐垫",
        "aliases": ["Seat Cushion", "Ergonomic Cushion", "Orthopedic Seat Cushion", "Tailbone Cushion", "办公坐垫"],
        "included_items": ["记忆棉坐垫", "凝胶坐垫", "尾骨减压坐垫", "楔形坐姿纠正垫"],
        "excluded_items": ["普通装饰坐垫", "冥想坐垫", "婴儿座椅垫", "户外坐垫/野餐垫"],
        "description": "通过人体工学设计和缓冲材料分散坐骨压力、改善坐姿、缓解久坐疼痛的健康坐垫品类。",
        "parent_code": None,
    },
]


def seed_database(db: Session) -> None:
    categories: dict[str, Category] = {
        item.code: item for item in db.scalars(select(Category)).all()
    }
    for seed in CATEGORY_SEEDS:
        category = categories.get(seed["code"])
        if category is None:
            category = Category(
                code=seed["code"],
                name=seed["name"],
                aliases=seed["aliases"],
                included_items=seed["included_items"],
                excluded_items=seed["excluded_items"],
                description=seed["description"],
            )
            db.add(category)
            db.flush()
            categories[category.code] = category
        parent_code = seed["parent_code"]
        if parent_code:
            category.parent_id = categories[parent_code].id

        existing_keys = set(
            db.scalars(
                select(EncyclopediaSection.section_key).where(
                    EncyclopediaSection.category_id == category.id
                )
            ).all()
        )
        for section_key, title in SECTION_DEFINITIONS:
            if section_key not in existing_keys:
                db.add(
                    EncyclopediaSection(
                        category_id=category.id,
                        section_key=section_key,
                        title=title,
                    )
                )
    db.commit()

