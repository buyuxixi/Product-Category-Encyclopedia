# 小红书热度统一为 0–100 分段封顶

## 背景

小红书曾用绝对互动量（赞+藏+评×2，可达数万）作 `hotness_score`，与 Amazon / Reddit / YouTube（约 0–60）不可比，同屏排序被小红书压过。

## 方案（MVP）

仅归一化小红书入库热度；Amazon 等暂不改（已在同量级）。

```
hotness_score = min(赞/100, 40) + min(藏/80, 30) + min(评/10, 20)   # 满分 90
is_hot        = hotness_score >= 50
```

- 选帖排序仍用原始 `engagement = 赞 + 藏 + 评×2`
- 赞评藏继续写在 description，卡片可看原始互动

## 示例

| 帖子 | 赞/评/藏 | 归一化热度 |
|---|---|---|
| 坐垫爆帖 | 25777 / 209 / 14411 | **90** |
| 中等帖 | 1200 / 30 / 80 | **16** |

库内回刷后量级：小红书 max **90** / avg **49**，Amazon max 59 — 同屏可粗比。

## 使用

```bash
cd backend
DATABASE_URL=mysql+pymysql://encyclopedia:encyclopedia_dev@127.0.0.1:3308/category_encyclopedia?charset=utf8mb4 \
  python3 scripts/backfill_xhs_hotness.py --apply
```

## 后续（未做）

把 Amazon / Reddit / YouTube 接到同一 `calculate_hotness` helper，真正全平台 0–100。
