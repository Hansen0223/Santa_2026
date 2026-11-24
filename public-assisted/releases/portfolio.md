# 还原 128,500 条候选

本轮 1 道题共省 1 条。[逐题来源与指纹](portfolio.json) · [上一版 128,501 条候选](https://github.com/Hansen0223/Santa_2026/blob/37d94f2/public-assisted/releases/portfolio.md)

| 题号（节选） | 步数 | 改进来源 |
| --- | --- | --- |
| 363 | 150 → 149 | GoodPJW (DAG-LNS), also credited in Ishan Karnick v66 sources.csv |

将官方题目保存为 `data/puzzles.csv`，将以下原件放入 `archives/`。

| 文件名 | 下载来源 |
| --- | --- |
| `goodpjw2008-373296333-submission.csv` | [goodpjw2008-373296333-submission.csv](https://www.kaggle.com/code/goodpjw2008/santa-2026-fresh-program-re-search-lb-128-500?scriptVersionId=373296333) |

在有 Git 历史的仓库根目录运行以下命令。

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出 `combined/submission.csv` 包含 1,000 道题，SHA-256 为 `c00261d394fcd8c1955dadfcb8ee7c1fae6d2e587256541d95ebef64aaac8c99`。等长时保留清单中较早的来源。[仓库逐题署名](../origins.csv)
