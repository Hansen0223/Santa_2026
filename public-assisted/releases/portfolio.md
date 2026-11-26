# 还原 127,812 条候选

第 960 和 991 题各再省一步。[本地补丁](../../collaboration/recipe-union/interleaved-orders-combined-wins.csv) · [上一版 127,814 步候选](https://github.com/Hansen0223/Santa_2026/blob/041f3e7/public-assisted/releases/portfolio.md)

Asterios Panoras 第 414 版回放为 127,815 步。相对上一版本，有 6 道题缩短，来源标为 Ross Wade。[固定归档](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/414) · [对比和署名](../../collaboration/evidence/asteriospanoras-414-comparison.json) · [上一版候选](https://github.com/Hansen0223/Santa_2026/blob/4b763c3/public-assisted/releases/portfolio.md)

第 678 题另缩短至 151 步。[本地补丁](../../collaboration/recipe-union/asterios414-0678-win.csv)

将官方题目保存为 `data/puzzles.csv`，并将固定归档保存为 `archives/asteriospanoras-414.zip`。在仓库根目录运行以下命令。

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出包含 1,000 道题，SHA-256 为 `6cfa9a18d54a1a909634bc9d68d019289fa309fdf4aaea321c6ce070e107ce29`。[清单](portfolio.json)
