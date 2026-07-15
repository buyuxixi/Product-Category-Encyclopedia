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
        "status": "active",
    },
    {
        "code": "MEDICATION_MANAGEMENT",
        "name": "药物管理",
        "aliases": ["Medication Management", "药物管理", "药盒与切药器", "药物管理（药盒，分药器）"],
        "included_items": ["药盒", "切药器/分药器"],
        "excluded_items": [],
        "description": "药物管理一级目录（仅导航分组，不作为独立百科页）；下含药盒与切药器两个可进入子品类。",
        "parent_code": None,
        "status": "group",
    },
    {
        "code": "FAR_INFRARED",
        "name": "远红外热疗",
        "aliases": [
            "Far Infrared",
            "Far-infrared",
            "Far Infrared Therapy",
            "FAR_INFRARED",
            "远红外热疗",
            "远红外热敷",
        ],
        "included_items": [
            "含碳纤维/石墨烯发热元件的电热垫，Listing 标题或 Bullet Point 中声明\"Far Infrared\"或\"Infrared Heat\"",
            "嵌入天然玉石（Jade）、电气石（Tourmaline）等远红外发射材料的加热垫/加热垫",
            "石墨烯发热膜制成的柔性热敷带/热敷贴",
            "远红外加热全身包裹垫（Body Wrap Mat），尺寸 ≥ 24\"×30\"",
            "加重型远红外加热垫（Weighted Far Infrared Heating Pad）",
            "含远红外声明的暖宫/腹部专用加热垫",
        ],
        "excluded_items": [
            "普通电阻丝加热垫：仅使用传统电阻丝发热、无远红外材料或远红外声明的产品（如 Sunbeam、Comfytemp 普通款）",
            "微波加热垫：需微波炉加热的凝胶/谷物垫（Microwaveable Heating Pad）",
            "远红外桑拿房/桑拿毯：非便携消费级设备，价格 > $500，归入 Sauna 类目",
            "红外理疗灯：近红外（Near Infrared）LED/灯泡式设备，归入 Light Therapy 类目",
            "暖贴/暖宝宝：一次性化学发热贴（Heat Patches），虽同属 Hot & Cold Therapies 但完全不同子类目",
            "EMS/TENS 设备：电脉冲刺激设备，即使带热敷功能也不属于远红外热疗",
        ],
        "description": "热疗下以远红外材料、辐射或相关作用机制为核心卖点的子品类，区别于普通电阻加热垫与近红外光疗。",
        "parent_code": "HEAT_THERAPY",
        "status": "active",
    },
    {
        "code": "SHOULDER_NECK_HEAT_THERAPY",
        "name": "肩颈热敷",
        "aliases": [
            "Shoulder & Neck Heat Therapy",
            "Neck and Shoulder Heating Pad",
            "Neck Heating Wrap",
            "Heated Neck Wrap",
            "肩颈热敷",
            "肩颈加热",
        ],
        "included_items": [
            "肩颈加热 Wrap（电动加重款，含石墨烯/远红外技术）",
            "颈部加热护具（U型颈枕式）",
            "微波加热肩颈垫（天然填料、香薰、冷热两用）",
            "可充电颈贴 / 无线穿戴款（含带按摩功能）",
            "远红外 / 红光治疗垫（660nm/850nm）",
        ],
        "excluded_items": [
            "不带加热能力的普通颈枕或按摩器",
            "针对腰部、腹部、足部等非肩颈部位的加热垫",
            "暖手宝、热水袋等通用取暖产品",
            "电热毯/电热床垫",
            "纯红外理疗灯（非穿戴/包裹式）",
        ],
        "description": "热疗下针对肩部、颈部和上背部使用场景的加热产品子品类，以定向加热与人体工学包裹为核心。",
        "parent_code": "HEAT_THERAPY",
        "status": "active",
    },
    {
        "code": "TENS_THERAPY",
        "name": "电疗 TENS",
        "aliases": [
            "TENS",
            "TENS unit",
            "Transcutaneous Electrical Nerve Stimulation",
            "经皮神经电刺激",
            "电疗",
        ],
        "included_items": [
            "便携式 TENS 设备（电池供电 / USB 充电）",
            "TENS 电极贴片（导电凝胶垫）",
            "TENS 专用导线/线缆",
            "可穿戴 TENS 设备（无线款、蓝牙款、贴片式）",
            "混合型 TENS+EMS 设备（以 TENS 为主功能）",
            "TENS+EMS+按摩 多功能组合设备",
            "经期/分娩专用 TENS 设备",
            "EMS 肌肉刺激设备（与 TENS 共享类目）",
            "导电凝胶（增强导电性）",
        ],
        "excluded_items": [
            "微电流治疗（Microcurrent）设备——使用极低电流（μA 级别），机制不同，亚马逊归入美容仪器",
            "IFC（干扰电流疗法）设备——使用两路中频电流交叉产生低频效果，属专业医疗设备",
            "植入式神经刺激器（如脊髓刺激器 SCS）——需手术植入，非消费品",
            "普通按摩仪/按摩枪——使用机械振动而非电刺激，亚马逊归入 Massagers 类目",
            "射频美容仪（RF）——射频能量加热皮肤，非低频电刺激，归入美容仪器",
            "纯 EMS 腹肌训练带/贴片——以减肥/塑形为主要卖点时归入 Sports 类目",
        ],
        "description": "通过皮肤表面电极输送微弱电流刺激神经以达到镇痛目的的消费级电子设备品类；亚马逊类目常与 EMS 共用，以 TENS 为主功能及混合型设备纳入本品类。",
        "parent_code": None,
        "status": "active",
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
        "status": "active",
    },
    {
        "code": "PILL_ORGANIZER",
        "name": "药盒",
        "aliases": [
            "Pill Organizer",
            "Pill Box",
            "Dosette Box",
            "Pillbox",
            "药盒",
            "药物管理-药盒",
            "Medication Management - Pill Organizer",
        ],
        "included_items": [
            "单日便携迷你药盒（1–6格，无星期标识）",
            "7天分格药盒（7–28格，有星期标识，无电子无刀片）",
            "月度大容量药盒（28–31格，月度日期，纯机械开合）",
            "智能电子药盒（含电子元器件，归入FDA Class-I医疗器械）",
            "组合款：药盒+切药器二合一（含收纳仓+刀片，合规条件叠加）",
        ],
        "excluded_items": [
            "独立切药器（无收纳仓）——单独品类，归入切药器类目",
            "药品原包装/药瓶——非管理工具",
            "电动研磨器——判定为医疗器械",
            "药品注射器/分装工具——非口服药物管理",
        ],
        "description": "多分格依从性辅助工具，按天/时段分类存储固体口服药物；含收纳仓+刀片的二合一归入本类组合款。",
        "parent_code": "MEDICATION_MANAGEMENT",
        "status": "active",
    },
    {
        "code": "PILL_SPLITTER",
        "name": "分药器",
        "aliases": [
            "Pill Splitter",
            "Pill Cutter",
            "Pill Crusher",
            "切药器",
            "分药器",
            "药片碾碎器",
            "药物管理-切药器",
            "Medication Management - Pill Splitter",
        ],
        "included_items": [
            "V型切割器、安全切割器、多分切割器",
            "药片碾碎器（Pill Crusher，研磨而非切割）",
        ],
        "excluded_items": [
            "药盒——单独品类，归入药盒类目",
            "带收纳仓的切药器——归入组合款（药盒品类）",
            "大功率电动粉碎机——判定为医疗器械",
            "管制药品切割工具——亚马逊禁售",
        ],
        "description": "将药片精确分割为等分剂量或碾成粉末的手动工具品类，不含药品收纳仓。",
        "parent_code": "MEDICATION_MANAGEMENT",
        "status": "active",
    },
    {
        "code": "SEAT_CUSHION",
        "name": "坐垫健康-办公坐垫",
        "aliases": [
            "Seat Cushion",
            "Ergonomic Seat Cushion",
            "Orthopedic Seat Cushion",
            "Tailbone Cushion",
            "Coccyx Cushion",
            "Memory Foam Seat Cushion",
            "Gel Seat Cushion",
            "办公坐垫",
        ],
        "included_items": [
            "人体工学记忆棉/凝胶坐垫（面向办公/医疗用途）",
            "尾骨减压坐垫（U型设计）",
            "楔形坐姿纠正垫",
            "可充气康复坐垫",
        ],
        "excluded_items": [
            "普通装饰坐垫/抱枕",
            "汽车专用坐垫",
            "户外坐垫/野餐垫",
            "冥想坐垫（Zafu/Zabuton）",
            "婴儿座椅垫",
        ],
        "description": "坐垫健康-办公坐垫是以办公室久坐健康场景为核心的功能性细分品类，通过U型切口、楔形与缓冲材料实现压力再分布，缓解腰背/尾骨/坐骨神经痛。",
        "parent_code": None,
        "status": "active",
    },
]


def seed_database(db: Session) -> None:
    categories: dict[str, Category] = {
        item.code: item for item in db.scalars(select(Category)).all()
    }
    # 先创建/更新全部品类元数据，再挂 parent（避免父节点尚未入库）
    for seed in CATEGORY_SEEDS:
        category = categories.get(seed["code"])
        if category is None:
            category = Category(code=seed["code"])
            db.add(category)
            db.flush()
            categories[category.code] = category
        category.name = seed["name"]
        category.aliases = seed["aliases"]
        category.included_items = seed["included_items"]
        category.excluded_items = seed["excluded_items"]
        category.description = seed["description"]
        category.status = seed.get("status", "active")

    for seed in CATEGORY_SEEDS:
        category = categories[seed["code"]]
        parent_code = seed["parent_code"]
        category.parent_id = categories[parent_code].id if parent_code else None

    for seed in CATEGORY_SEEDS:
        category = categories[seed["code"]]
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

