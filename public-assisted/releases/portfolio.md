# 还原 132,530 条候选

将仓库的公开辅助程序与 Alex Chilton 的 Rudolph 第 123 版逐题取短，即可还原全部 1,000 题。源文件与仓库提交均固定在[合并清单](portfolio.json)中。[Rudolph 第 123 版原始 ZIP](https://www.kaggle.com/datasets/alexchilton/santa-2026-rudolph-programs/versions/123)

将官方比赛的 `puzzles.csv` 放在 `data/`，将原始 ZIP 保存在 `archives/alexchilton-123.zip`，然后从仓库根目录运行：

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出为 `combined/submission.csv`。完整文件的 SHA-256 是 `2c0c961d51b3333b3447fedcec644bd08ad3ebd8b1cd23173458b12afbb990ca`。等长时选择仓库已发布的程序，各题的历史署名保留在[仓库来源表](../origins.csv)中。

相对 132,536 条候选，本轮 5 题共省 6 条。第 111、618 题的改进先在 GoodPJW 第 40 版发现，第 374 题采用 Hiyohane 的 211 条程序，第 689、751 题的改进同时见于 Asterios 第 186 版和 Rudolph 第 123 版。最终选定清单中的两份来源即可重现全部改进。[GoodPJW 第 40 版](https://www.kaggle.com/datasets/goodpjw2008/santa-2026-dag-lns-programs/versions/40) · [第 374 题提交](https://github.com/Hansen0223/Santa_2026/commit/0521078c877f1fea6b02d4409973cf9ef9b5f612) · [Asterios 第 186 版](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/186)
