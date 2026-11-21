# 还原 132,519 条候选

仓库固定版本和 Asterios Panoras 第 188 版逐题取短，可以重建全部 1,000 题。对照上一版，第 295 题从 119 条缩到 118 条，第 812 题从 103 条缩到 102 条。发布文件的逐题署名分别为「E-Max AI, Santa 2026 | Public Frontier | Score 132,622」和「E-Max AI, Santa 2026 | Public Frontier | Score 132,622」。[合并清单](portfolio.json) · [Asterios 第 188 版](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/188)

将官方题目放在 `data/puzzles.csv`，将上述版本的原始 ZIP 保存为 `archives/asteriospanoras-188.zip`。在仓库根目录运行：

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出为 `combined/submission.csv`，SHA-256 为 `3929c08b2755c5b5721fadb320788d06dd47898e67af2402937b10311b9976ef`。原始 ZIP 重放为 132,622 条。等长时优先采用仓库中已有的程序。[仓库逐题署名](../origins.csv) · [上一版的完整还原方式](https://github.com/Hansen0223/Santa_2026/blob/87bfed4/public-assisted/releases/portfolio.md)
