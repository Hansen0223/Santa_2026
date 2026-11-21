# 还原 132,507 条候选

本地中段重写让第 374、681、944 题各省一条，分别由 211 降至 210、193 降至 192、209 降至 208。第 110 题选用独立生成的 167 条程序。第 347 题来自 Pardheev，第 985 题来自 GoodPJW，第 290 题来自 Asterios Panoras 的固定笔记本。[本轮逐题实验](../../collaboration/register-search/README.md) · [输入与逐题差额](portfolio.json) · [上一版候选](https://github.com/Hansen0223/Santa_2026/blob/cd705b4/public-assisted/releases/portfolio.md)

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

生成的 `combined/submission.csv` 包含全部 1,000 题，SHA-256 为 `8e11d3c084c63f97b9a2c07eae6bf1a5a9a25a6a836af9ae33599a9b6cf740a2`。当长度相同时，保留清单中较早来源的程序。[仓库逐题署名](../origins.csv)
