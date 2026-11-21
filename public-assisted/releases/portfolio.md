# 还原 132,480 条候选

九道题共省 15 条。第 791 题由 124 条降至 118 条，第 71、246、464、608、723、987 题各省一条。这七道程序由 Asterios 的第 194 版收录并署名为 Ishan Karnick。Pardheev 在第 169 题省两条，Asterios Panoras 在第 911 题省一条。[逐题来源与指纹](portfolio.json) · [Ishan 第 6 版](https://www.kaggle.com/datasets/ishankarnick/santa-2026-frontier-programs/versions/6) · [上一版 132,495 条候选](https://github.com/Hansen0223/Santa_2026/blob/82d0de0/public-assisted/releases/portfolio.md)

将官方题目保存为 `data/puzzles.csv`，将以下原件放入 `archives/`。

| 文件名 | 下载来源 |
| --- | --- |
| `asteriospanoras-194.zip` | [asteriospanoras-194 原始 ZIP](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/194) |
| `pardheev-372201937.ipynb` | [pardheev-372201937 笔记本原件](https://www.kaggle.com/kernels/scriptcontent/372201937/download) |
| `asteriospanoras-372201982.ipynb` | [asteriospanoras-372201982 笔记本原件](https://www.kaggle.com/kernels/scriptcontent/372201982/download) |

在有 Git 历史的仓库根目录运行以下命令。

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出 `combined/submission.csv` 包含 1,000 道题，SHA-256 为 `9996f5feda0eb2716e7b6f1fa59e03405a8e44237b42e5e2c812b0f976c084d7`。遇到等长程序时，保留清单中较早的来源。[仓库逐题署名](../origins.csv)
