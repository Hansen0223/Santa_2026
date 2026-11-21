# 还原 132,515 条候选

从仓库中的公开辅助解和 Asterios Panoras 第 189 版逐题选择较短程序，得到全部 1,000 题。相对上一版，三道题共省 4 条。公开归档中的实物为 132,618 条。[固定输入与逐题改进](portfolio.json) · [Asterios 第 189 版](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/189)

| 题号 | 上一版 | 新长度 | 上游逐题署名 |
| --- | ---: | ---: | --- |
| 505 | 109 | 107 | goodpjw2008 |
| 778 | 128 | 127 | public merge（原文件未注明个人） |
| 933 | 112 | 111 | goodpjw2008 |

第 505 和 933 题的相同长度也出现在 GoodPJW 第 42 版和 Rudolph 第 125 版。[GoodPJW 第 42 版](https://www.kaggle.com/datasets/goodpjw2008/santa-2026-dag-lns-programs/versions/42) · [Rudolph 第 125 版](https://www.kaggle.com/datasets/alexchilton/santa-2026-rudolph-programs/versions/125)

把官方题目保存为 `data/puzzles.csv`，把 Asterios 第 189 版原始 ZIP 保存为 `archives/asteriospanoras-189.zip`。在仓库根目录运行：

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出为 `combined/submission.csv`，SHA-256 为 `3de9c10837c7911378146c40962ae31038d9511330cd587c3fd5fd3a713c69d5`。等长时优先保留固定仓库版本的程序。[仓库逐题署名](../origins.csv) · [上一版候选](https://github.com/Hansen0223/Santa_2026/blob/c191762/public-assisted/releases/portfolio.md)
