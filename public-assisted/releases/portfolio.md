# 还原 132,510 条候选

和 132,513 条的版本相比，第 110、347、985 题各省一条。此版本在第 110、985 题采用 GoodPJW，第 347 题来自 Pardheev 发布的文件。第 110 题的本地独立搜索也得到了另一份等长程序。第 290 题沿用 Asterios Panoras 的笔记本程序。[逐题改进及输入指纹](portfolio.json) · [上一版候选](https://github.com/Hansen0223/Santa_2026/blob/a8338d3/public-assisted/releases/portfolio.md)

将官方题目保存为 `data/puzzles.csv`，将以下三个文件放进 `archives/`。

| 保存的文件名 | 下载来源 |
| --- | --- |
| `goodpjw2008-43.zip` | [GoodPJW 第 43 版原始 ZIP](https://www.kaggle.com/datasets/goodpjw2008/santa-2026-dag-lns-programs/versions/43) |
| `pardheev-13.zip` | [Pardheev 第 13 版原始 ZIP](https://www.kaggle.com/datasets/pardheev/santa-2026-elf-calculator-132997/versions/13) |
| `asterios-372173182.ipynb` | [Asterios 第 290 题笔记本原件](https://www.kaggle.com/kernels/scriptcontent/372173182/download) |

在有 Git 历史的仓库根目录运行以下命令。

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

生成的 `combined/submission.csv` 包含全部 1,000 题，SHA-256 为 `b952abf6425ba01e49e96aeff0c56f5fcc316b2800964a6e86c3bcf939fe27a0`。当长度相同时，保留清单中较早来源的程序。[仓库逐题署名](../origins.csv)
