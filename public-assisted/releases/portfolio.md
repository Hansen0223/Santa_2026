# 还原 128,491 条候选

第 93 题由 99 步降至 98 步。Asterios Panoras 第 373 版将该程序署名为 Ertuğrul Özer。[归档来源](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/373) · [逐题来源与指纹](portfolio.json) · [上一版 128,492 条候选](https://github.com/Hansen0223/Santa_2026/blob/0838a24/public-assisted/releases/portfolio.md)

将官方题目保存为 `data/puzzles.csv`，将以下原件放入 `archives/`。

| 文件名 | 下载来源 |
| --- | --- |
| `goodpjw2008-239.zip` | [GoodPJW 第 239 版](https://www.kaggle.com/datasets/goodpjw2008/santa-2026-dag-lns-programs/versions/239) |
| `ozertuu-373317540-submission.csv` | 下载固定版本的 `submission.csv` 后改名。[Ertuğrul Özer 第 373317540 次运行](https://www.kaggle.com/code/ozertuu/santa-2026-starter-notebook?scriptVersionId=373317540) |
| `asteriospanoras-373.zip` | [Asterios Panoras 第 373 版](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/373) |

在有 Git 历史的仓库根目录运行以下命令。

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出 `combined/submission.csv` 包含 1,000 道题，SHA-256 为 `e0a615a67ab0d8985093ae37e08b52812e8380a1ec3f16b10d742420469dd56a`。等长时保留清单中较早的来源。[仓库逐题署名](../origins.csv)
