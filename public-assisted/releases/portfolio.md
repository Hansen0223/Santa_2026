# 还原 132,513 条候选

Rudolph 第 126 版把第 8 题从 103 条缩到 102 条。该归档重放为 132,617 条，归档中的程序表只提供题号和指令。逐题与仓库固定版本取短，再采用 Asterios Panoras 笔记本中的第 290 题程序，1,000 题合计 132,513 条。[逐题改进及输入指纹](portfolio.json) · [Alex Chilton 的 Rudolph 第 126 版](https://www.kaggle.com/datasets/alexchilton/santa-2026-rudolph-programs/versions/126) · [Asterios 第 290 题程序](https://www.kaggle.com/code/asteriospanoras/santa-2026-best-public-score-a-gift-per-run?scriptVersionId=372173182)

将官方题目保存为 `data/puzzles.csv`，将 Rudolph 第 126 版原始 ZIP 保存为 `archives/alexchilton-126.zip`，将固定版本笔记本保存为 `archives/asterios-372173182.ipynb`。[笔记本原件](https://www.kaggle.com/kernels/scriptcontent/372173182/download)

在仓库根目录运行：

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出为 `combined/submission.csv`，SHA-256 为 `22a840c409fdfc3d2e56001ea2a0137328e8ca4c5dececb826652a6555f81516`。等长时按清单顺序保留第一份程序。[仓库逐题署名](../origins.csv) · [上一版候选及公开来源](https://github.com/Hansen0223/Santa_2026/blob/37cfdb7/public-assisted/releases/portfolio.md)
