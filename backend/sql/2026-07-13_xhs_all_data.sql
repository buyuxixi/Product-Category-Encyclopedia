-- 全量小红书精选数据增量更新（MySQL 8）
-- 包含当前数据库中的全部小红书内容：60 条热点链接、19 条趋势信号。
-- 依赖：先执行 2026-07-13_add_zh_label_columns.sql。
-- 可重复执行：热点链接按 URL 去重，趋势信号按品类+平台+标题去重。
-- TENS 清理仅删除 cleaned 清单中的已知非精选 URL，不影响后续新增数据。

START TRANSACTION;

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '用理疗灯是为了烤走疼痛，而不是烤来伤害', NULL, 'https://www.xiaohongshu.com/explore/69b90da9000000001a031bfe', '[小雪] | ❤ 5855 | 💬 104 | ⭐ 70 | 搜索词: 红外灯烫伤', NULL, 5855.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'FAR_INFRARED'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/69b90da9000000001a031bfe');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '理疗灯乱象', NULL, 'https://www.xiaohongshu.com/explore/6981b6d40000000028023170', '[追光闪闪] | ❤ 2712 | 💬 124 | ⭐ 2055 | 搜索词: 红外照了没用', NULL, 2712.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'FAR_INFRARED'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6981b6d40000000028023170');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '热门理疗灯二选一', NULL, 'https://www.xiaohongshu.com/explore/6a26bf1f000000001503c0ef', '[爱分享] | ❤ 2389 | 💬 23 | ⭐ 2541 | 搜索词: 红外理疗灯', NULL, 2389.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'FAR_INFRARED'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6a26bf1f000000001503c0ef');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '照红光没效果？甚至还反黑？真相在这！', NULL, 'https://www.xiaohongshu.com/explore/694ca152000000001e02a628', '[Hooyaa（修屏障版）] | ❤ 2410 | 💬 41 | ⭐ 1584 | 搜索词: 红外照了没用', NULL, 2410.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'FAR_INFRARED'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/694ca152000000001e02a628');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '痛经女孩都去照这个红外线理疗灯', NULL, 'https://www.xiaohongshu.com/explore/6a09996b0000000007012805', '[木子] | ❤ 1885 | 💬 379 | ⭐ 756 | 搜索词: 红外理疗灯', NULL, 1885.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'FAR_INFRARED'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6a09996b0000000007012805');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '安利给所有女生！红外线理疗灯yyds！', NULL, 'https://www.xiaohongshu.com/explore/62da76f2000000000d0240d8', '[躺平发发淇🌸] | ❤ 1770 | 💬 139 | ⭐ 1335 | 搜索词: 红外理疗灯', NULL, 1770.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'FAR_INFRARED'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/62da76f2000000000d0240d8');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '一篇说清楚电烤灯红外线理疗器怎么选', NULL, 'https://www.xiaohongshu.com/explore/68cbb528000000001203259c', '[儿女双全] | ❤ 1509 | 💬 304 | ⭐ 905 | 搜索词: 理疗灯辐射', NULL, 1509.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'FAR_INFRARED'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/68cbb528000000001203259c');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '理疗灯治疗妇科炎症2', NULL, 'https://www.xiaohongshu.com/explore/6232b04a0000000001025645', '[草莓来养生] | ❤ 1404 | 💬 200 | ⭐ 1108 | 搜索词: 理疗灯辐射', NULL, 1404.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'FAR_INFRARED'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6232b04a0000000001025645');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '哈！30几岁用上了远红外烤灯', NULL, 'https://www.xiaohongshu.com/explore/67e6a6750000000009015c3f', '[体子] | ❤ 894 | 💬 285 | ⭐ 671 | 搜索词: 红外灯关节', NULL, 894.0, 0, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'FAR_INFRARED'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/67e6a6750000000009015c3f');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '分享丨红外理疗灯是智商税，我为什么会买？', NULL, 'https://www.xiaohongshu.com/explore/67efab86000000001c0280fa', '[阿蕊碎碎念] | ❤ 935 | 💬 361 | ⭐ 381 | 搜索词: 红外理疗灯', NULL, 935.0, 0, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'FAR_INFRARED'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/67efab86000000001c0280fa');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '我不在你身边 希望这个小药盒照顾好你', NULL, 'https://www.xiaohongshu.com/explore/66d02674000000001d01561e', '[糕手茶茶] | ❤ 23932 | 💬 609 | ⭐ 5195 | 搜索词: 药盒便携', NULL, 23932.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'MEDICATION_MANAGEMENT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/66d02674000000001d01561e');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '分享好物～小米药盒', NULL, 'https://www.xiaohongshu.com/explore/6201e4b60000000001027ed9', '[粉粉熊和公仔面] | ❤ 4294 | 💬 97 | ⭐ 2512 | 搜索词: 药盒提醒', NULL, 4294.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'MEDICATION_MANAGEMENT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6201e4b60000000001027ed9');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '服务设计 ｜ 老年人便捷式药盒设计', NULL, 'https://www.xiaohongshu.com/explore/6672fffa000000000e033f17', '[Moon] | ❤ 3690 | 💬 70 | ⭐ 2145 | 搜索词: 智能药盒', NULL, 3690.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'MEDICATION_MANAGEMENT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6672fffa000000000e033f17');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '我的天，以后吃药也太方便了吧😭', NULL, 'https://www.xiaohongshu.com/explore/69cf834000000000230243a3', '[CreaTide创意潮汐] | ❤ 4614 | 💬 272 | ⭐ 796 | 搜索词: 药盒', NULL, 4614.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'MEDICATION_MANAGEMENT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/69cf834000000000230243a3');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '这些看似智商税，实则嘎嘎好用的吃药辅助器', NULL, 'https://www.xiaohongshu.com/explore/677b509f000000000b00c180', '[王一伯] | ❤ 2733 | 💬 196 | ⭐ 2700 | 搜索词: 切药器', NULL, 2733.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'MEDICATION_MANAGEMENT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/677b509f000000000b00c180');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '谁家的小宝宝还不好好吃药阿？', NULL, 'https://www.xiaohongshu.com/explore/64bfd63d0000000010033361', '[美念念] | ❤ 3802 | 💬 16 | ⭐ 1037 | 搜索词: 切药器儿童', NULL, 3802.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'MEDICATION_MANAGEMENT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/64bfd63d0000000010033361');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '这个设计真的会防止忘吃药！', NULL, 'https://www.xiaohongshu.com/explore/68b07c15000000001d02a59b', '[虚构远方] | ❤ 1362 | 💬 472 | ⭐ 234 | 搜索词: 药盒忘记吃药', NULL, 1362.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'MEDICATION_MANAGEMENT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/68b07c15000000001d02a59b');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '小心小心小心使用分药器！', NULL, 'https://www.xiaohongshu.com/explore/68e25c8c0000000004011810', '[水沉] | ❤ 1906 | 💬 232 | ⭐ 129 | 搜索词: 切药器', NULL, 1906.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'MEDICATION_MANAGEMENT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/68e25c8c0000000004011810');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '小华同学的随身小药盒有解酒药哈哈哈哈', NULL, 'https://www.xiaohongshu.com/explore/679774fb0000000029038259', '[老板爹和少爷叔的金刚球] | ❤ 2026 | 💬 32 | ⭐ 214 | 搜索词: 药盒便携', NULL, 2026.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'MEDICATION_MANAGEMENT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/679774fb0000000029038259');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '送给男朋友的爱心小药盒呀～', NULL, 'https://www.xiaohongshu.com/explore/67bf2b6e000000002503d868', '[小八] | ❤ 1360 | 💬 25 | ⭐ 633 | 搜索词: 药盒便携', NULL, 1360.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'MEDICATION_MANAGEMENT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/67bf2b6e000000002503d868');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '建议大家卧室都放一根便宜不占地的落地棒灯', NULL, 'https://www.xiaohongshu.com/explore/68ca5846000000001302b0ac', '[少点虚荣来点gravel] | ❤ 11863 | 💬 584 | ⭐ 8457 | 搜索词: 智能夜灯', NULL, 11863.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'NIGHT_LIGHT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/68ca5846000000001302b0ac');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '等我把星空灯的雷都踩完了  你们再来！', NULL, 'https://www.xiaohongshu.com/explore/69ef6b3a00000000200386a2', '[小陈的神经世界] | ❤ 1194 | 💬 35 | ⭐ 568 | 搜索词: 智能夜灯', NULL, 1194.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'NIGHT_LIGHT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/69ef6b3a00000000200386a2');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '啊啊啊！9r的小夜灯也太美了！', NULL, 'https://www.xiaohongshu.com/explore/6825f38c000000002300d8fd', '[猪猪小洛] | ❤ 740 | 💬 12 | ⭐ 278 | 搜索词: 智能夜灯', NULL, 740.0, 0, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'NIGHT_LIGHT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6825f38c000000002300d8fd');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '米家夜灯3', NULL, 'https://www.xiaohongshu.com/explore/678cd4dc000000001602a8c3', '[力大如5] | ❤ 612 | 💬 50 | ⭐ 208 | 搜索词: 智能夜灯', NULL, 612.0, 0, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'NIGHT_LIGHT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/678cd4dc000000001602a8c3');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '装灯带原来还有这样的坑😂', NULL, 'https://www.xiaohongshu.com/explore/68e22ef00000000005032137', '[年纪轻轻就有猫了（选软装中）] | ❤ 265 | 💬 54 | ⭐ 149 | 搜索词: 智能灯被坑', NULL, 265.0, 0, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'NIGHT_LIGHT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/68e22ef00000000005032137');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '灯带智能模块避坑', NULL, 'https://www.xiaohongshu.com/explore/664ec8af0000000014018b5b', '[Keiro] | ❤ 117 | 💬 115 | ⭐ 172 | 搜索词: 智能灯被坑', NULL, 117.0, 0, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'NIGHT_LIGHT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/664ec8af0000000014018b5b');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '避坑！欧普智能灯无法连接米家！！', NULL, 'https://www.xiaohongshu.com/explore/68948de9000000002203804a', '[momo] | ❤ 69 | 💬 84 | ⭐ 57 | 搜索词: 智能灯被坑', NULL, 69.0, 0, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'NIGHT_LIGHT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/68948de9000000002203804a');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '智能灯踩坑……', NULL, 'https://www.xiaohongshu.com/explore/62da5eb9000000001101199d', '[减肥不讲李] | ❤ 53 | 💬 71 | ⭐ 38 | 搜索词: 智能灯被坑', NULL, 53.0, 0, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'NIGHT_LIGHT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/62da5eb9000000001101199d');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '灯带的坑还没踩完！', NULL, 'https://www.xiaohongshu.com/explore/6a17c456000000003700d70a', '[装修踩坑的Mario🏠] | ❤ 10 | 💬 18 | ⭐ 2 | 搜索词: 智能灯被坑', NULL, 10.0, 0, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'NIGHT_LIGHT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6a17c456000000003700d70a');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '避雷柜子灯带触摸开关！', NULL, 'https://www.xiaohongshu.com/explore/6a50d471000000001102e05c', '[兰州智能家居王工] | ❤ 15 | 💬 0 | ⭐ 9 | 搜索词: 智能灯被坑', NULL, 15.0, 0, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'NIGHT_LIGHT'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6a50d471000000001102e05c');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '拯救屁屁❗️❗️打工人必备坐垫✨低至4R', NULL, 'https://www.xiaohongshu.com/explore/631c6d52000000001303a77f', '[郑原里美] | ❤ 25777 | 💬 209 | ⭐ 14411 | 搜索词: 坐垫推荐', NULL, 25777.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'SEAT_CUSHION'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/631c6d52000000001303a77f');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '绝了❗️这坐垫也太厚实了吧', NULL, 'https://www.xiaohongshu.com/explore/62a5e016000000002103a40f', '[麦芽] | ❤ 22793 | 💬 163 | ⭐ 12594 | 搜索词: 坐垫推荐', NULL, 22793.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'SEAT_CUSHION'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/62a5e016000000002103a40f');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '单向滑动坐垫', NULL, 'https://www.xiaohongshu.com/explore/684ad9e40000000012006372', '[轮上人] | ❤ 17400 | 💬 163 | ⭐ 2540 | 搜索词: 坐垫滑走', NULL, 17400.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'SEAT_CUSHION'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/684ad9e40000000012006372');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '海豹屁垫是什么馅儿的呢🤔', NULL, 'https://www.xiaohongshu.com/explore/6984192e000000002200bda2', '[PokiDoki的礼物] | ❤ 10901 | 💬 154 | ⭐ 1780 | 搜索词: 记忆棉坐垫', NULL, 10901.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'SEAT_CUSHION'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6984192e000000002200bda2');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '后续来了！10w人看过的13r涨价屁垫子平替！！！', NULL, 'https://www.xiaohongshu.com/explore/6835cb3200000000220259bd', '[芋头不爱吃香菜] | ❤ 8463 | 💬 304 | ⭐ 3370 | 搜索词: 办公室坐垫', NULL, 8463.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'SEAT_CUSHION'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6835cb3200000000220259bd');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '随手po！8💰久坐不塌的屁垫分享！！无广！！！', NULL, 'https://www.xiaohongshu.com/explore/683f00f900000000210187b8', '[饭团] | ❤ 6981 | 💬 220 | ⭐ 4503 | 搜索词: 坐垫哪个好', NULL, 6981.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'SEAT_CUSHION'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/683f00f900000000210187b8');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '椅子坐垫', NULL, 'https://www.xiaohongshu.com/explore/64fd93d0000000001500ac95', '[上午好] | ❤ 6359 | 💬 634 | ⭐ 3944 | 搜索词: 坐垫学生', NULL, 6359.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'SEAT_CUSHION'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/64fd93d0000000001500ac95');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '8💰！！坐了两个月不塌的屁垫反馈来啦！！', NULL, 'https://www.xiaohongshu.com/explore/6899f81e000000002303bec1', '[饭团] | ❤ 6234 | 💬 92 | ⭐ 3591 | 搜索词: 办公坐垫评测', NULL, 6234.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'SEAT_CUSHION'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6899f81e000000002303bec1');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '考研久坐平价坐垫腰靠推荐(两件不到30！)', NULL, 'https://www.xiaohongshu.com/explore/66176027000000001b00a493', '[小翘] | ❤ 5394 | 💬 293 | ⭐ 3155 | 搜索词: 坐垫推荐', NULL, 5394.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'SEAT_CUSHION'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/66176027000000001b00a493');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '久坐人需要的屁垫', NULL, 'https://www.xiaohongshu.com/explore/64e87ffe0000000010030753', '[大白玩具] | ❤ 5428 | 💬 1115 | ⭐ 1076 | 搜索词: 办公室坐垫', NULL, 5428.0, 1, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'SEAT_CUSHION'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/64e87ffe0000000010030753');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '亲测300天热敷效果！真的绝了！！！', '亲测300天热敷效果！真的绝了！！！', 'https://www.xiaohongshu.com/explore/6908c567000000000503b171', '[小都耶耶] | ❤ 10006 | 💬 55 | ⭐ 2429 | 搜索词: 肩颈热敷', '[小都耶耶] | ❤ 10006 | 💬 55 | ⭐ 2429 | 搜索词: 肩颈热敷', 10006.0, 1, '2026-07-13 09:00:41'
FROM categories c WHERE c.code = 'SHOULDER_NECK_HEAT_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6908c567000000000503b171');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '舒缓颈椎❣️低头族必看的好物分享', '舒缓颈椎❣️低头族必看的好物分享', 'https://www.xiaohongshu.com/explore/612b5b06000000000102ab52', '[Cecilia宋妍霏] | ❤ 7641 | 💬 171 | ⭐ 3600 | 搜索词: 肩颈热敷', '[Cecilia宋妍霏] | ❤ 7641 | 💬 171 | ⭐ 3600 | 搜索词: 肩颈热敷', 7641.0, 1, '2026-07-13 09:00:41'
FROM categories c WHERE c.code = 'SHOULDER_NECK_HEAT_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/612b5b06000000000102ab52');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '谁懂😭，这个29💰热敷♨️枕，绝绝子！', '谁懂😭，这个29💰热敷♨️枕，绝绝子！', 'https://www.xiaohongshu.com/explore/66792ada000000001d014d83', '[唯艾优选生活馆] | ❤ 2880 | 💬 665 | ⭐ 1469 | 搜索词: 颈椎热敷推荐', '[唯艾优选生活馆] | ❤ 2880 | 💬 665 | ⭐ 1469 | 搜索词: 颈椎热敷推荐', 2880.0, 1, '2026-07-13 09:00:41'
FROM categories c WHERE c.code = 'SHOULDER_NECK_HEAT_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/66792ada000000001d014d83');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '🆘缓解肩颈疼痛神器！最低10r，岂止一个爽字', '🆘缓解肩颈疼痛神器！最低10r，岂止一个爽字', 'https://www.xiaohongshu.com/explore/6218764a00000000010271ae', '[是JOJO啊] | ❤ 2793 | 💬 78 | ⭐ 2404 | 搜索词: 肩颈热敷', '[是JOJO啊] | ❤ 2793 | 💬 78 | ⭐ 2404 | 搜索词: 肩颈热敷', 2793.0, 1, '2026-07-13 09:00:41'
FROM categories c WHERE c.code = 'SHOULDER_NECK_HEAT_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6218764a00000000010271ae');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '200+颈椎头疗，不如19.9💰的艾草热敷枕❗️', '200+颈椎头疗，不如19.9💰的艾草热敷枕❗️', 'https://www.xiaohongshu.com/explore/674c2d67000000000800738a', '[别吃我血包] | ❤ 3424 | 💬 235 | ⭐ 1411 | 搜索词: 颈椎热敷', '[别吃我血包] | ❤ 3424 | 💬 235 | ⭐ 1411 | 搜索词: 颈椎热敷', 3424.0, 1, '2026-07-13 09:00:41'
FROM categories c WHERE c.code = 'SHOULDER_NECK_HEAT_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/674c2d67000000000800738a');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '发现了一个颈椎病热敷的好办法！', '发现了一个颈椎病热敷的好办法！', 'https://www.xiaohongshu.com/explore/6726ea59000000001b02f264', '[多多🐈开心] | ❤ 2453 | 💬 215 | ⭐ 1567 | 搜索词: 办公室肩颈热敷', '[多多🐈开心] | ❤ 2453 | 💬 215 | ⭐ 1567 | 搜索词: 办公室肩颈热敷', 2453.0, 1, '2026-07-13 09:00:41'
FROM categories c WHERE c.code = 'SHOULDER_NECK_HEAT_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6726ea59000000001b02f264');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '无聊中，来安利下各种肩颈贴贴（会更新）', '无聊中，来安利下各种肩颈贴贴（会更新）', 'https://www.xiaohongshu.com/explore/666d76c0000000000e031122', '[JiiiiiiE] | ❤ 1980 | 💬 95 | ⭐ 1247 | 搜索词: 肩颈热敷', '[JiiiiiiE] | ❤ 1980 | 💬 95 | ⭐ 1247 | 搜索词: 肩颈热敷', 1980.0, 1, '2026-07-13 09:00:41'
FROM categories c WHERE c.code = 'SHOULDER_NECK_HEAT_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/666d76c0000000000e031122');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '热敷六个小时，肩颈真的不痛了😭｜教师的体态', '热敷六个小时，肩颈真的不痛了😭｜教师的体态', 'https://www.xiaohongshu.com/explore/671a2c09000000002603662a', '[慢慢的一天] | ❤ 1351 | 💬 122 | ⭐ 600 | 搜索词: 睡前颈椎热敷', '[慢慢的一天] | ❤ 1351 | 💬 122 | ⭐ 600 | 搜索词: 睡前颈椎热敷', 1351.0, 1, '2026-07-13 09:00:41'
FROM categories c WHERE c.code = 'SHOULDER_NECK_HEAT_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/671a2c09000000002603662a');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '真的离谱！妙界热敷肩颈贴说实话！！！', '真的离谱！妙界热敷肩颈贴说实话！！！', 'https://www.xiaohongshu.com/explore/689fc053000000001d0051d8', '[小雨的肥啾] | ❤ 125 | 💬 0 | ⭐ 69 | 搜索词: 肩颈热敷智商税', '[小雨的肥啾] | ❤ 125 | 💬 0 | ⭐ 69 | 搜索词: 肩颈热敷智商税', 125.0, 0, '2026-07-13 09:00:41'
FROM categories c WHERE c.code = 'SHOULDER_NECK_HEAT_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/689fc053000000001d0051d8');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '肩痛热敷当心越敷越疼', '肩痛热敷当心越敷越疼', 'https://www.xiaohongshu.com/explore/695c7381000000001a01d31a', '[关节医生曹建刚] | ❤ 79 | 💬 3 | ⭐ 66 | 搜索词: 肩颈热敷不好用', '[关节医生曹建刚] | ❤ 79 | 💬 3 | ⭐ 66 | 搜索词: 肩颈热敷不好用', 79.0, 0, '2026-07-13 09:00:41'
FROM categories c WHERE c.code = 'SHOULDER_NECK_HEAT_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/695c7381000000001a01d31a');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'technology', 'social_post', 'xiaohongshu', '【干货】腹直肌分离Tens Care使用说明', NULL, 'https://www.xiaohongshu.com/explore/5c83c501000000000f03efbc', '[丿 、Jasmine] | ❤ 1236 | 💬 224 | ⭐ 2186 | 搜索词: tens贴片', NULL, 1236.0, 1, '2026-07-13 06:29:13'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/5c83c501000000000f03efbc');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'technology', 'social_post', 'xiaohongshu', '康复科神器-中频脉冲电', NULL, 'https://www.xiaohongshu.com/explore/67c6d473000000002602dc2f', '[仙霞康复小张] | ❤ 988 | 💬 182 | ⭐ 654 | 搜索词: 电脉冲理疗仪', NULL, 988.0, 0, '2026-07-13 06:29:13'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/67c6d473000000002602dc2f');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'technology', 'social_post', 'xiaohongshu', '针灸脉冲理疗仪', NULL, 'https://www.xiaohongshu.com/explore/65955ae9000000001200472d', '[一朵毒花🌸] | ❤ 296 | 💬 340 | ⭐ 205 | 搜索词: 电脉冲理疗仪', NULL, 296.0, 0, '2026-07-13 06:29:13'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/65955ae9000000001200472d');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'technology', 'social_post', 'xiaohongshu', '神经肌肉电刺激（NMES）贴片位置及目的', NULL, 'https://www.xiaohongshu.com/explore/69b75f06000000002301d9c1', '[康复师手记] | ❤ 419 | 💬 2 | ⭐ 431 | 搜索词: tens贴片寿命', NULL, 419.0, 0, '2026-07-13 06:29:13'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/69b75f06000000002301d9c1');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'users', 'social_post', 'xiaohongshu', '康复训练电疗之功能性电刺激的原理！', NULL, 'https://www.xiaohongshu.com/explore/677773c40000000013003fca', '[雅思Y医疗器械] | ❤ 756 | 💬 129 | ⭐ 450 | 搜索词: tens肩周炎', NULL, 756.0, 0, '2026-07-13 06:29:13'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/677773c40000000013003fca');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '偏头痛人！没招了？先去试试TENS仪器！理疗', NULL, 'https://www.xiaohongshu.com/explore/6a268e1d0000000006037b9c', '[Codie十年失眠努力自救] | ❤ 248 | 💬 77 | ⭐ 324 | 搜索词: tens仪推荐', NULL, 248.0, 0, '2026-07-13 06:29:13'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6a268e1d0000000006037b9c');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '理疗仪真的会让人有这么大反应？', NULL, 'https://www.xiaohongshu.com/explore/66bb2028000000000d031e12', '[王梓陌] | ❤ 30149 | 💬 954 | ⭐ 3917 | 搜索词: 理疗仪评测', NULL, 30149.0, 1, '2026-07-13 06:29:13'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/66bb2028000000000d031e12');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'market', 'social_post', 'xiaohongshu', '智商税之理疗仪？', NULL, 'https://www.xiaohongshu.com/explore/6694de5200000000250179b4', '[蛋仔派对北念] | ❤ 379 | 💬 123 | ⭐ 155 | 搜索词: 理疗仪评测', NULL, 379.0, 0, '2026-07-13 06:29:13'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/6694de5200000000250179b4');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'needs', 'social_post', 'xiaohongshu', '老人保健品、理疗仪防沉迷系统！一招解决~', NULL, 'https://www.xiaohongshu.com/explore/67a7ea6d000000002902a1a4', '[哏工侃智能] | ❤ 454 | 💬 87 | ⭐ 246 | 搜索词: 理疗仪骗局', NULL, 454.0, 0, '2026-07-13 06:29:13'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/67a7ea6d000000002902a1a4');

INSERT INTO hot_links (category_id, section_key, link_type, platform, title, title_zh, url, description, description_zh, hotness_score, is_hot, collected_at)
SELECT c.id, 'needs', 'social_post', 'xiaohongshu', '🌟电疗干货一篇搞定｜作用禁忌+操作指南💡', NULL, 'https://www.xiaohongshu.com/explore/68f610fc0000000004017437', '[庄庄-要-安康] | ❤ 842 | 💬 26 | ⭐ 594 | 搜索词: tens副作用', NULL, 842.0, 0, '2026-07-13 06:29:13'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (SELECT 1 FROM hot_links h WHERE h.url = 'https://www.xiaohongshu.com/explore/68f610fc0000000004017437');

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'market', 'user_pain_point', 'xiaohongshu', '红外理疗灯', '腰椎间盘突出，腰痛压迫坐骨神经腿麻，还有点脊柱侧弯，应该选哪个？', NULL, 4.0, 'likes', 'stable', '小红书笔记《理疗灯内行实话》热评（4赞）：腰椎间盘突出，腰痛压迫坐骨神经腿麻，还有点脊柱侧弯，应该选哪个？。原文链接: https://www.xiaohongshu.com/explore/6911baa00000000003023d64', NULL, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'FAR_INFRARED'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = '腰椎间盘突出，腰痛压迫坐骨神经腿麻，还有点脊柱侧弯，应该选哪个？'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'market', 'user_pain_point', 'xiaohongshu', '红外理疗灯', '你好，盆腔积液，医生让买这个烤怎么选，选高的还是矮的', NULL, 4.0, 'likes', 'stable', '小红书笔记《理疗灯内行实话》热评（4赞）：你好，盆腔积液，医生让买这个烤怎么选，选高的还是矮的。原文链接: https://www.xiaohongshu.com/explore/6911baa00000000003023d64', NULL, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'FAR_INFRARED'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = '你好，盆腔积液，医生让买这个烤怎么选，选高的还是矮的'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'market', 'user_pain_point', 'xiaohongshu', '药盒便携', '不是说实话，减小了他真的好抠出来吗[doge]', NULL, 5188.0, 'likes', 'up', '小红书笔记《我不在你身边 希望这个小药盒照顾好你》热评（5188赞）：不是说实话，减小了他真的好抠出来吗[doge]。原文链接: https://www.xiaohongshu.com/explore/66d02674000000001d01561e', NULL, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'MEDICATION_MANAGEMENT'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = '不是说实话，减小了他真的好抠出来吗[doge]'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'market', 'user_pain_point', 'xiaohongshu', '药盒便携', '廉价的自我感动而已，放不了多少还不知道保质期，反正我觉得制作药盒在恋爱中挺低智的[笑哭R][笑哭R][笑哭R]', NULL, 3162.0, 'likes', 'up', '小红书笔记《我不在你身边 希望这个小药盒照顾好你》热评（3162赞）：廉价的自我感动而已，放不了多少还不知道保质期，反正我觉得制作药盒在恋爱中挺低智的[笑哭R][笑哭R][笑哭R]。原文链接: https://www.xiaohongshu.com/explore/66d02674000000001d01561e', NULL, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'MEDICATION_MANAGEMENT'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = '廉价的自我感动而已，放不了多少还不知道保质期，反正我觉得制作药盒在恋爱中挺低智的[笑哭R][笑哭R][笑哭R]'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'market', 'user_pain_point', 'xiaohongshu', '坐垫推荐', '我刚刚去看已经卖到74.9了[笑哭R]可能是买的人多了一些就大涨价了，好下头[笑哭R]', NULL, 240.0, 'likes', 'up', '小红书笔记《绝了❗️这坐垫也太厚实了吧》热评（240赞）：我刚刚去看已经卖到74.9了[笑哭R]可能是买的人多了一些就大涨价了，好下头[笑哭R]。原文链接: https://www.xiaohongshu.com/explore/62a5e016000000002103a40f', NULL, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'SEAT_CUSHION'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = '我刚刚去看已经卖到74.9了[笑哭R]可能是买的人多了一些就大涨价了，好下头[笑哭R]'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'market', 'user_pain_point', 'xiaohongshu', '坐垫推荐', '久坐人很需要这个耶', NULL, 97.0, 'likes', 'up', '小红书笔记《拯救屁屁❗️❗️打工人必备坐垫✨低至4R》热评（97赞）：久坐人很需要这个耶。原文链接: https://www.xiaohongshu.com/explore/631c6d52000000001303a77f', NULL, '2026-07-13 08:36:37'
FROM categories c WHERE c.code = 'SEAT_CUSHION'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = '久坐人很需要这个耶'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'market', 'user_pain_point', 'xiaohongshu', '肩颈热敷', '闺蜜前几天还跟我吐槽带娃肩颈疼[暗中观察R]赶紧下单送给她', '闺蜜前几天还跟我吐槽带娃肩颈疼[暗中观察R]赶紧下单送给她', 17.0, 'likes', 'up', '小红书笔记《亲测300天热敷效果！真的绝了！！！》热评（17赞）：闺蜜前几天还跟我吐槽带娃肩颈疼[暗中观察R]赶紧下单送给她。原文链接: https://www.xiaohongshu.com/explore/6908c567000000000503b171', '小红书笔记《亲测300天热敷效果！真的绝了！！！》热评（17赞）：闺蜜前几天还跟我吐槽带娃肩颈疼[暗中观察R]赶紧下单送给她。原文链接: https://www.xiaohongshu.com/explore/6908c567000000000503b171', '2026-07-13 09:00:41'
FROM categories c WHERE c.code = 'SHOULDER_NECK_HEAT_THERAPY'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = '闺蜜前几天还跟我吐槽带娃肩颈疼[暗中观察R]赶紧下单送给她'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'market', 'review_sentiment', 'xiaohongshu', '肩颈热敷', '没想到和姐姐拥有同款颈椎枕真的太好用了[偷笑R][偷笑R]', '没想到和姐姐拥有同款颈椎枕真的太好用了[偷笑R][偷笑R]', 9.0, 'likes', 'positive', '小红书笔记《舒缓颈椎❣️低头族必看的好物分享》热评（9赞）：没想到和姐姐拥有同款颈椎枕真的太好用了[偷笑R][偷笑R]。原文链接: https://www.xiaohongshu.com/explore/612b5b06000000000102ab52', '小红书笔记《舒缓颈椎❣️低头族必看的好物分享》热评（9赞）：没想到和姐姐拥有同款颈椎枕真的太好用了[偷笑R][偷笑R]。原文链接: https://www.xiaohongshu.com/explore/612b5b06000000000102ab52', '2026-07-13 09:00:41'
FROM categories c WHERE c.code = 'SHOULDER_NECK_HEAT_THERAPY'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = '没想到和姐姐拥有同款颈椎枕真的太好用了[偷笑R][偷笑R]'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'needs', 'social_mention', 'xiaohongshu', 'tens皮肤灼伤', 'XHS搜索: tens皮肤灼伤', NULL, 21.0, 'notes', 'stable', '小红书搜索关键词"tens皮肤灼伤"返回21篇笔记。搜索链接: https://www.xiaohongshu.com/search_result?keyword=tens%E7%9A%AE%E8%82%A4%E7%81%BC%E4%BC%A4', NULL, '2026-07-13 06:29:44'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = 'XHS搜索: tens皮肤灼伤'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'definition', 'social_mention', 'xiaohongshu', 'TENS理疗仪', 'XHS搜索: TENS理疗仪', NULL, 21.0, 'notes', 'stable', '小红书搜索关键词"TENS理疗仪"返回21篇笔记。搜索链接: https://www.xiaohongshu.com/search_result?keyword=TENS%E7%90%86%E7%96%97%E4%BB%AA', NULL, '2026-07-13 06:29:44'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = 'XHS搜索: TENS理疗仪'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'technology', 'social_mention', 'xiaohongshu', '电脉冲理疗仪', 'XHS搜索: 电脉冲理疗仪', NULL, 21.0, 'notes', 'stable', '小红书搜索关键词"电脉冲理疗仪"返回21篇笔记。搜索链接: https://www.xiaohongshu.com/search_result?keyword=%E7%94%B5%E8%84%89%E5%86%B2%E7%90%86%E7%96%97%E4%BB%AA', NULL, '2026-07-13 06:29:44'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = 'XHS搜索: 电脉冲理疗仪'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'technology', 'social_mention', 'xiaohongshu', 'tens贴片不粘', 'XHS搜索: tens贴片不粘', NULL, 20.0, 'notes', 'stable', '小红书搜索关键词"tens贴片不粘"返回20篇笔记。搜索链接: https://www.xiaohongshu.com/search_result?keyword=tens%E8%B4%B4%E7%89%87%E4%B8%8D%E7%B2%98', NULL, '2026-07-13 06:29:44'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = 'XHS搜索: tens贴片不粘'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'users', 'social_mention', 'xiaohongshu', 'tens腰痛', 'XHS搜索: tens腰痛', NULL, 20.0, 'notes', 'stable', '小红书搜索关键词"tens腰痛"返回20篇笔记。搜索链接: https://www.xiaohongshu.com/search_result?keyword=tens%E8%85%B0%E7%97%9B', NULL, '2026-07-13 06:29:44'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = 'XHS搜索: tens腰痛'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'needs', 'social_mention', 'xiaohongshu', '理疗仪没效果', 'XHS搜索: 理疗仪没效果', NULL, 19.0, 'notes', 'stable', '小红书搜索关键词"理疗仪没效果"返回19篇笔记。搜索链接: https://www.xiaohongshu.com/search_result?keyword=%E7%90%86%E7%96%97%E4%BB%AA%E6%B2%A1%E6%95%88%E6%9E%9C', NULL, '2026-07-13 06:29:44'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = 'XHS搜索: 理疗仪没效果'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'needs', 'social_mention', 'xiaohongshu', '理疗仪骗局', 'XHS搜索: 理疗仪骗局', NULL, 19.0, 'notes', 'stable', '小红书搜索关键词"理疗仪骗局"返回19篇笔记。搜索链接: https://www.xiaohongshu.com/search_result?keyword=%E7%90%86%E7%96%97%E4%BB%AA%E9%AA%97%E5%B1%80', NULL, '2026-07-13 06:29:44'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = 'XHS搜索: 理疗仪骗局'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'technology', 'social_mention', 'xiaohongshu', 'tens贴片', 'XHS搜索: tens贴片', NULL, 18.0, 'notes', 'stable', '小红书搜索关键词"tens贴片"返回18篇笔记。搜索链接: https://www.xiaohongshu.com/search_result?keyword=tens%E8%B4%B4%E7%89%87', NULL, '2026-07-13 06:29:44'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = 'XHS搜索: tens贴片'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'users', 'social_mention', 'xiaohongshu', 'tens颈椎', 'XHS搜索: tens颈椎', NULL, 18.0, 'notes', 'stable', '小红书搜索关键词"tens颈椎"返回18篇笔记。搜索链接: https://www.xiaohongshu.com/search_result?keyword=tens%E9%A2%88%E6%A4%8E', NULL, '2026-07-13 06:29:44'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = 'XHS搜索: tens颈椎'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'users', 'social_mention', 'xiaohongshu', '理疗仪家用', 'XHS搜索: 理疗仪家用', NULL, 17.0, 'notes', 'stable', '小红书搜索关键词"理疗仪家用"返回17篇笔记。搜索链接: https://www.xiaohongshu.com/search_result?keyword=%E7%90%86%E7%96%97%E4%BB%AA%E5%AE%B6%E7%94%A8', NULL, '2026-07-13 06:29:44'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = 'XHS搜索: 理疗仪家用'
  );

INSERT INTO trend_signals (category_id, section_key, signal_type, platform, keyword, title, title_zh, metric_value, metric_unit, trend_direction, summary, summary_zh, collected_at)
SELECT c.id, 'users', 'social_mention', 'xiaohongshu', '理疗仪真的会让人有这么大反应', 'XHS爆款: 理疗仪真的会让人有这么大反应？(30149赞/954评论)', NULL, 30149.0, 'likes', 'viral', '博主@王梓陌发布使用理疗仪搞笑视频, 30149赞/954评论。评论区核心: ①新手不知道从低档位开始(3621赞最高评论)②"像被电的感觉"③个体敏感度差异大④设备被视为"玩具"有娱乐价值。原文链接: https://www.xiaohongshu.com/explore/66bb2028000000000d031e12。搜索链接: https://www.xiaohongshu.com/search_result?keyword=%E7%90%86%E7%96%97%E4%BB%AA%E7%9C%9F%E7%9A%84%E4%BC%9A%E8%AE%A9%E4%BA%BA%E6%9C%89%E8%BF%99%E4%B9%88%E5%A4%A7%E5%8F%8D%E5%BA%94', NULL, '2026-07-13 06:29:44'
FROM categories c WHERE c.code = 'TENS_THERAPY'
  AND NOT EXISTS (
    SELECT 1 FROM trend_signals t
    WHERE t.category_id = c.id AND t.platform = 'xiaohongshu' AND t.title = 'XHS爆款: 理疗仪真的会让人有这么大反应？(30149赞/954评论)'
  );

-- 将 TENS 小红书热点链接收敛到确认保留的 10 条；仅删除 cleaned 清单中的已知旧 URL。
DELETE h FROM hot_links h
JOIN categories c ON c.id = h.category_id
WHERE c.code = 'TENS_THERAPY' AND h.platform = 'xiaohongshu'
  AND h.url IN (
    'https://www.xiaohongshu.com/explore/5f5a3adc000000000100a3ff',
    'https://www.xiaohongshu.com/explore/6054c8bd0000000001026e25',
    'https://www.xiaohongshu.com/explore/620e19ac000000002103e864',
    'https://www.xiaohongshu.com/explore/62184ae20000000021038c36',
    'https://www.xiaohongshu.com/explore/62769902000000002103e67c',
    'https://www.xiaohongshu.com/explore/643954f00000000013009c09',
    'https://www.xiaohongshu.com/explore/645905cd00000000130072f4',
    'https://www.xiaohongshu.com/explore/64f15e1f000000001e020e9d',
    'https://www.xiaohongshu.com/explore/652cecd3000000001d01626a',
    'https://www.xiaohongshu.com/explore/65f3a89e0000000014004533',
    'https://www.xiaohongshu.com/explore/6605125b0000000012021e8a',
    'https://www.xiaohongshu.com/explore/6636f926000000001e02197f',
    'https://www.xiaohongshu.com/explore/66976af90000000003025960',
    'https://www.xiaohongshu.com/explore/6698c6220000000025014808',
    'https://www.xiaohongshu.com/explore/669fafb5000000000600dbd2',
    'https://www.xiaohongshu.com/explore/66a31a1e000000000a005c90',
    'https://www.xiaohongshu.com/explore/66a639c4000000000d030198',
    'https://www.xiaohongshu.com/explore/66a736e3000000000d030687',
    'https://www.xiaohongshu.com/explore/66cdad29000000001d0148ad',
    'https://www.xiaohongshu.com/explore/66d910e0000000001e019a99',
    'https://www.xiaohongshu.com/explore/66d9c2bc0000000027000009',
    'https://www.xiaohongshu.com/explore/66de9229000000002603c2c3',
    'https://www.xiaohongshu.com/explore/66e15b9500000000270030c2',
    'https://www.xiaohongshu.com/explore/66eb997400000000260329ad',
    'https://www.xiaohongshu.com/explore/6700eab6000000002c02e1eb',
    'https://www.xiaohongshu.com/explore/6713be61000000002100ae14',
    'https://www.xiaohongshu.com/explore/6730cc81000000001a034f50',
    'https://www.xiaohongshu.com/explore/6772adaf000000000b014238',
    'https://www.xiaohongshu.com/explore/6797aeaf0000000018007244',
    'https://www.xiaohongshu.com/explore/67a35f6d0000000029024e5b',
    'https://www.xiaohongshu.com/explore/67a6e180000000001703925a',
    'https://www.xiaohongshu.com/explore/67b2855e0000000029028704',
    'https://www.xiaohongshu.com/explore/67c671ca0000000009039058',
    'https://www.xiaohongshu.com/explore/67d0101b000000000900d630',
    'https://www.xiaohongshu.com/explore/67d792ab000000001a007819',
    'https://www.xiaohongshu.com/explore/67e0e72e000000000903be25',
    'https://www.xiaohongshu.com/explore/67e1244c000000001c001a15',
    'https://www.xiaohongshu.com/explore/67e267e1000000001c006a7c',
    'https://www.xiaohongshu.com/explore/67ee9fc9000000000b01c2ee',
    'https://www.xiaohongshu.com/explore/67f92f49000000001c0150fa',
    'https://www.xiaohongshu.com/explore/67facccd000000001d01fe77',
    'https://www.xiaohongshu.com/explore/6801d0c1000000001a007cc1',
    'https://www.xiaohongshu.com/explore/68117a43000000002001d932',
    'https://www.xiaohongshu.com/explore/68120fa9000000002102c047',
    'https://www.xiaohongshu.com/explore/68121fb100000000210008a7',
    'https://www.xiaohongshu.com/explore/6838ebd80000000023017b9b',
    'https://www.xiaohongshu.com/explore/683d072b000000002101878e',
    'https://www.xiaohongshu.com/explore/683e9cfa0000000020029389',
    'https://www.xiaohongshu.com/explore/683fbb37000000002300e166',
    'https://www.xiaohongshu.com/explore/684671cc0000000023017d3c',
    'https://www.xiaohongshu.com/explore/68789d15000000002203caed',
    'https://www.xiaohongshu.com/explore/6879c300000000002201dfd6',
    'https://www.xiaohongshu.com/explore/6880465f00000000170332d0',
    'https://www.xiaohongshu.com/explore/688c4b16000000002502b252',
    'https://www.xiaohongshu.com/explore/6890765c000000000500ad28',
    'https://www.xiaohongshu.com/explore/68a5e9b1000000001c009194',
    'https://www.xiaohongshu.com/explore/68a6e645000000001d023652',
    'https://www.xiaohongshu.com/explore/68a6f979000000001c00f895',
    'https://www.xiaohongshu.com/explore/68be3dc0000000001b03f80c',
    'https://www.xiaohongshu.com/explore/68c23088000000001c009b51',
    'https://www.xiaohongshu.com/explore/68d3af33000000000b03c2a1',
    'https://www.xiaohongshu.com/explore/68da2fbe0000000013007106',
    'https://www.xiaohongshu.com/explore/68e8d63600000000050300e8',
    'https://www.xiaohongshu.com/explore/68e9bbc30000000005012680',
    'https://www.xiaohongshu.com/explore/68f745bb000000000300e10d',
    'https://www.xiaohongshu.com/explore/691d74ef000000000d039bec',
    'https://www.xiaohongshu.com/explore/69212b11000000001e00c3f3',
    'https://www.xiaohongshu.com/explore/6926dfd8000000001e007b4a',
    'https://www.xiaohongshu.com/explore/69328303000000000d0355f4',
    'https://www.xiaohongshu.com/explore/694217bf000000001e03b1e1',
    'https://www.xiaohongshu.com/explore/69527bbe000000001e03b445',
    'https://www.xiaohongshu.com/explore/695cb6870000000021029d18',
    'https://www.xiaohongshu.com/explore/695dbffd000000001a0260d1',
    'https://www.xiaohongshu.com/explore/6966fd24000000002202fafb',
    'https://www.xiaohongshu.com/explore/696f1dd7000000002102b28d',
    'https://www.xiaohongshu.com/explore/69993ce2000000001a01c0d9',
    'https://www.xiaohongshu.com/explore/69a5ad530000000015031d1d',
    'https://www.xiaohongshu.com/explore/69b3d7c50000000023022b4e',
    'https://www.xiaohongshu.com/explore/69bb9b4e000000001a032a0e',
    'https://www.xiaohongshu.com/explore/69bbc4d10000000022025aab',
    'https://www.xiaohongshu.com/explore/69df7e0a000000001a02db39',
    'https://www.xiaohongshu.com/explore/69e2e8c8000000001a0313b1',
    'https://www.xiaohongshu.com/explore/6a17f42900000000350303aa',
    'https://www.xiaohongshu.com/explore/6a3b85d9000000000f02b46e',
    'https://www.xiaohongshu.com/explore/6a3cc6ab0000000020039a8b',
    'https://www.xiaohongshu.com/explore/6a446da2000000001101e280',
    'https://www.xiaohongshu.com/explore/6a49fb30000000002201a248',
    'https://www.xiaohongshu.com/explore/6a4b2443000000000803d2ca',
    'https://www.xiaohongshu.com/explore/6a4b5b900000000008024538',
    'https://www.xiaohongshu.com/explore/6a4e2bc0000000001603fe47',
    'https://www.xiaohongshu.com/explore/6a4e353000000000070246c5',
    'https://www.xiaohongshu.com/explore/6a4f4a58000000001603d722',
    'https://www.xiaohongshu.com/explore/6a505acc0000000008000e8f'
  );

COMMIT;

-- 校验：预期 60 条小红书热点链接、19 条小红书趋势信号。
SELECT COUNT(*) AS xhs_links FROM hot_links WHERE platform = 'xiaohongshu';
SELECT COUNT(*) AS xhs_signals FROM trend_signals WHERE platform = 'xiaohongshu';
SELECT c.code, COUNT(*) AS xhs_links FROM hot_links h JOIN categories c ON c.id = h.category_id WHERE h.platform = 'xiaohongshu' GROUP BY c.code ORDER BY c.code;
SELECT c.code, COUNT(*) AS xhs_signals FROM trend_signals t JOIN categories c ON c.id = t.category_id WHERE t.platform = 'xiaohongshu' GROUP BY c.code ORDER BY c.code;
SELECT url, COUNT(*) AS duplicate_count FROM hot_links WHERE platform = 'xiaohongshu' GROUP BY url HAVING COUNT(*) > 1;
