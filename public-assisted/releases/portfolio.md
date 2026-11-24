# 还原 128,492 条候选

第 106 题 210 → 209，第 170 题 207 → 206，改进均来自 Ertuğrul Özer 的公开程序。[固定笔记本](https://www.kaggle.com/code/ozertuu/santa-2026-starter-notebook?scriptVersionId=373317540) · [逐题来源与指纹](portfolio.json) · [上一版 128,494 条候选](https://github.com/Hansen0223/Santa_2026/blob/63ff0e5/public-assisted/releases/portfolio.md)

将官方题目保存为 `data/puzzles.csv`，将以下原件放入 `archives/`。

| 文件名 | 下载来源 |
| --- | --- |
| `goodpjw2008-239.zip` | [GoodPJW 第 239 版](https://www.kaggle.com/datasets/goodpjw2008/santa-2026-dag-lns-programs/versions/239) |
| `ozertuu-373317540-submission.csv` | 下载固定版本的 `submission.csv` 后改名。[Ertuğrul Özer 第 373317540 次运行](https://www.kaggle.com/code/ozertuu/santa-2026-starter-notebook?scriptVersionId=373317540) |

在有 Git 历史的仓库根目录运行以下命令。

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出 `combined/submission.csv` 包含 1,000 道题，SHA-256 为 `ca84df2b9f8c14d6c1b6ffa3b3fe7593e5717eea1354b09194e20c9d2c3531d6`。等长时保留清单中较早的来源。[仓库逐题署名](../origins.csv)
