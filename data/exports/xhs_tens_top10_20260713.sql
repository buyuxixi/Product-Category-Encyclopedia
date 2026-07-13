-- TENS 小红书热门内容增量导入（MySQL 8.0）
-- 生成日期: 2026-07-13
-- 内容: TENS_THERAPY hot_links=10
-- 每条记录已结合标题、搜索上下文、互动数据、评论语境和研究报告补充标签与内容摘要。
-- 已有 URL 更新标签和摘要；不存在的 URL 才新增。
-- 执行前请先完成 Alembic 数据库迁移。

SET NAMES utf8mb4;
START TRANSACTION;

SELECT COUNT(*) AS matched_categories FROM categories WHERE code = 'TENS_THERAPY';
-- matched_categories 应为 1；否则请回滚并先初始化品类数据。

CREATE TEMPORARY TABLE tmp_xhs_tens_top10 (
    category_code VARCHAR(80) NOT NULL,
    title VARCHAR(500) NOT NULL,
    url VARCHAR(500) NOT NULL PRIMARY KEY,
    description TEXT NOT NULL,
    hotness_score DOUBLE NOT NULL,
    is_hot TINYINT(1) NOT NULL
) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

INSERT INTO tmp_xhs_tens_top10
    (category_code, title, url, description, hotness_score, is_hot)
VALUES
    ('TENS_THERAPY', '理疗仪真的会让人有这么大反应？', 'https://www.xiaohongshu.com/explore/66bb2028000000000d031e12', '标签: TENS使用安全 / 档位误用 / 新手体验 / 电击感 / 娱乐传播 | 内容理解: 家庭娱乐短视频：使用者一开始开到高档位，引发强烈身体反应。评论讨论集中在应从低档开始、不同人敏感度差异和类似被电的体感；不是疗效评测。 | 作者: 王梓陌 | ❤ 30149 | 💬 954 | ⭐ 3917 | 原搜索词: 理疗仪评测', 30149, 1),
    ('TENS_THERAPY', '【干货】腹直肌分离Tens Care使用说明', 'https://www.xiaohongshu.com/explore/5c83c501000000000f03efbc', '标签: TENS / 腹直肌分离 / 产后康复 / 电极贴片 / 操作指南 | 内容理解: 面向产后腹直肌分离人群的 TensCare 使用说明，核心是康复场景、贴片使用与训练配合，属于具体人群的操作经验。 | 作者: 丿 、Jasmine | ❤ 1236 | 💬 224 | ⭐ 2186 | 原搜索词: tens贴片', 1236, 1),
    ('TENS_THERAPY', '康复科神器-中频脉冲电', 'https://www.xiaohongshu.com/explore/67c6d473000000002602dc2f', '标签: 中频电疗 / 康复科 / 临床理疗 / 专业操作 / 医疗场景 | 内容理解: 介绍康复科使用的中频脉冲电疗及其临床应用，由专业康复场景提供背书；属于电刺激相邻技术，不应直接等同于家用 TENS。 | 作者: 仙霞康复小张 | ❤ 988 | 💬 182 | ⭐ 654 | 原搜索词: 电脉冲理疗仪', 988, 0),
    ('TENS_THERAPY', '🌟电疗干货一篇搞定｜作用禁忌+操作指南💡', 'https://www.xiaohongshu.com/explore/68f610fc0000000004017437', '标签: 电疗科普 / 作用机制 / 禁忌人群 / 操作指南 / 副作用与安全 | 内容理解: 综合型电疗科普，重点解释作用、禁忌和操作注意事项，回应用户对副作用、使用档位和安全边界的需求。 | 作者: 庄庄-要-安康 | ❤ 842 | 💬 26 | ⭐ 594 | 原搜索词: tens副作用', 842, 0),
    ('TENS_THERAPY', '康复训练电疗之功能性电刺激的原理！', 'https://www.xiaohongshu.com/explore/677773c40000000013003fca', '标签: FES / 功能性电刺激 / 康复训练 / 肌肉激活 / 技术原理 | 内容理解: 讲解功能性电刺激在康复训练中的原理和肌肉激活目的；属于 FES 专业科普，与 TENS 的镇痛定位不同。 | 作者: 雅思Y医疗器械 | ❤ 756 | 💬 129 | ⭐ 450 | 原搜索词: tens肩周炎', 756, 0),
    ('TENS_THERAPY', '针灸脉冲理疗仪', 'https://www.xiaohongshu.com/explore/65955ae9000000001200472d', '标签: 针灸脉冲 / 电脉冲理疗仪 / 家用电疗 / 使用体验 / 高讨论 | 内容理解: 围绕针灸脉冲理疗仪的使用或体验展开，互动讨论较高；现有数据未提供正文，具体功效主张和设备技术类型仍需查看原文确认。 | 作者: 一朵毒花🌸 | ❤ 296 | 💬 340 | ⭐ 205 | 原搜索词: 电脉冲理疗仪', 296, 0),
    ('TENS_THERAPY', '老人保健品、理疗仪防沉迷系统！一招解决~', 'https://www.xiaohongshu.com/explore/67a7ea6d000000002902a1a4', '标签: 老年人 / 理疗仪营销 / 防沉迷 / 家庭干预 / 防骗 | 内容理解: 讨论老人购买保健品和理疗仪的沉迷式消费，以及子女如何干预、防范体验店或推销场景；属于消费风险舆情，不是产品疗效内容。 | 作者: 哏工侃智能 | ❤ 454 | 💬 87 | ⭐ 246 | 原搜索词: 理疗仪骗局', 454, 0),
    ('TENS_THERAPY', '神经肌肉电刺激（NMES）贴片位置及目的', 'https://www.xiaohongshu.com/explore/69b75f06000000002301d9c1', '标签: NMES / 神经肌肉电刺激 / 电极位置 / 康复目的 / 专业指南 | 内容理解: 说明 NMES 电极贴片的位置与对应康复目的，侧重神经肌肉激活和专业贴法；属于 NMES，不应与 TENS 镇痛贴法混同。 | 作者: 康复师手记 | ❤ 419 | 💬 2 | ⭐ 431 | 原搜索词: tens贴片寿命', 419, 0),
    ('TENS_THERAPY', '智商税之理疗仪？', 'https://www.xiaohongshu.com/explore/6694de5200000000250179b4', '标签: 理疗仪评测 / 智商税 / 疗效争议 / 消费决策 / 避坑 | 内容理解: 从“智商税”角度讨论理疗仪的实际价值和购买合理性，反映消费者对疗效、价格与营销宣传的质疑。 | 作者: 蛋仔派对北念 | ❤ 379 | 💬 123 | ⭐ 155 | 原搜索词: 理疗仪评测', 379, 0),
    ('TENS_THERAPY', '偏头痛人！没招了？先去试试TENS仪器！理疗', 'https://www.xiaohongshu.com/explore/6a268e1d0000000006037b9c', '标签: TENS / 偏头痛 / 非药物镇痛 / 用户体验 / 设备推荐 | 内容理解: 偏头痛长期困扰者分享尝试 TENS 的经历，关注非药物镇痛和设备选择；属于个人体验，不能替代医疗建议或普遍疗效结论。 | 作者: Codie十年失眠努力自救 | ❤ 248 | 💬 77 | ⭐ 324 | 原搜索词: tens仪推荐', 248, 0);

UPDATE hot_links AS h
JOIN tmp_xhs_tens_top10 AS t ON t.url = h.url
JOIN categories AS c ON c.id = h.category_id AND c.code = t.category_code
SET h.section_key = 'market',
    h.link_type = 'social_post',
    h.platform = 'xiaohongshu',
    h.title = t.title,
    h.description = t.description,
    h.hotness_score = t.hotness_score,
    h.is_hot = t.is_hot,
    h.updated_at = NOW();
SET @updated_hot_links = ROW_COUNT();

INSERT INTO hot_links
    (category_id, section_key, link_type, platform, title, url, description, hotness_score, is_hot, collected_at)
SELECT
    c.id, 'market', 'social_post', 'xiaohongshu', t.title, t.url, t.description,
    t.hotness_score, t.is_hot, NOW()
FROM tmp_xhs_tens_top10 AS t
JOIN categories AS c ON c.code = t.category_code
WHERE NOT EXISTS (SELECT 1 FROM hot_links AS h WHERE h.url = t.url);
SET @inserted_hot_links = ROW_COUNT();

DROP TEMPORARY TABLE tmp_xhs_tens_top10;
COMMIT;

SELECT @updated_hot_links AS updated_hot_links, @inserted_hot_links AS inserted_hot_links;
