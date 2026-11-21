# 还原 132,514 条候选

将 Asterios Panoras 在固定版本笔记本中给出的第 290 题程序加入 132,515 条候选，这一题从 148 条缩至 147 条。基础候选采用仓库固定版本与 Asterios 第 189 版，含以下三道改进。[第 290 题的原始程序](https://www.kaggle.com/code/asteriospanoras/santa-2026-best-public-score-a-gift-per-run?scriptVersionId=372173182)

公开归档中的实物为 132,618 条。[固定输入与逐题改进](portfolio.json) · [Asterios 第 189 版](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/189)

| 题号 | 上一版 | 新长度 | 上游逐题署名 |
| --- | ---: | ---: | --- |
| 505 | 109 | 107 | goodpjw2008 |
| 778 | 128 | 127 | public merge（原文件未注明个人） |
| 933 | 112 | 111 | goodpjw2008 |

第 505 和 933 题的相同长度也出现在 GoodPJW 第 42 版和 Rudolph 第 125 版。[GoodPJW 第 42 版](https://www.kaggle.com/datasets/goodpjw2008/santa-2026-dag-lns-programs/versions/42) · [Rudolph 第 125 版](https://www.kaggle.com/datasets/alexchilton/santa-2026-rudolph-programs/versions/125)

把官方题目保存为 `data/puzzles.csv`，把 Asterios 第 189 版原始 ZIP 保存为 `archives/asteriospanoras-189.zip`，将[固定版本笔记本原件](https://www.kaggle.com/kernels/scriptcontent/372173182/download)保存为 `archives/asterios-372173182.ipynb`。程序读取其中的算式表。在仓库根目录运行：

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出为 `combined/submission.csv`，SHA-256 为 `095b8bca4878789ab1cd56c33ddb7a3e091792171e1afcb3ed1abd26b192149e`。等长时优先保留固定仓库版本的程序。[仓库逐题署名](../origins.csv) · [上一版候选](https://github.com/Hansen0223/Santa_2026/blob/9e63695/public-assisted/releases/portfolio.md)
