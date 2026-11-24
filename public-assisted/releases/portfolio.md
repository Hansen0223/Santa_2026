# 还原 128,494 条候选

本轮 6 道题共省 6 条。[逐题来源与指纹](portfolio.json) · [上一版 128,500 条候选](https://github.com/Hansen0223/Santa_2026/blob/267be19/public-assisted/releases/portfolio.md)

| 题号（节选） | 步数 | 改进来源 |
| --- | --- | --- |
| 88 | 192 → 191 | Ertuğrul Özer (ozertuu), notebook 373304666; identical row mirrored by GoodPJW v239 |
| 251 | 197 → 196 | Ertuğrul Özer (ozertuu), notebook 373304666; identical row mirrored by GoodPJW v239 |
| 342 | 201 → 200 | Ertuğrul Özer (ozertuu), notebook 373304666; identical row mirrored by GoodPJW v239 |
| 374 | 199 → 198 | Ertuğrul Özer (ozertuu), notebook 373304666; identical row mirrored by GoodPJW v239 |
| 375 | 194 → 193 | Ertuğrul Özer (ozertuu), notebook 373304666; identical row mirrored by GoodPJW v239 |
| 831 | 86 → 85 | Ertuğrul Özer (ozertuu), notebook 373304666; identical row mirrored by GoodPJW v239 |

将官方题目保存为 `data/puzzles.csv`，将以下原件放入 `archives/`。

| 文件名 | 下载来源 |
| --- | --- |
| `goodpjw2008-239.zip` | [goodpjw2008-239](https://www.kaggle.com/datasets/goodpjw2008/santa-2026-dag-lns-programs/versions/239) |

在有 Git 历史的仓库根目录运行以下命令。

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出 `combined/submission.csv` 包含 1,000 道题，SHA-256 为 `71023d53f8e62affbc136088528de25f8378ced84c697be5ba65b132b43e313e`。等长时保留清单中较早的来源。[仓库逐题署名](../origins.csv)
