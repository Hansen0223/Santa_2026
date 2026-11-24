# 还原 132,477 条候选

本轮 3 道题共省 3 条。[逐题来源与指纹](portfolio.json) · [上一版 132,480 条候选](https://github.com/Hansen0223/Santa_2026/blob/c42f416/public-assisted/releases/portfolio.md)

| 题号 | 步数 | 改进来源 |
| --- | --- | --- |
| 571 | 189 → 188 | 本地按依赖关系划分子区域并与整题搜索择短 |
| 927 | 119 → 118 | Sargis Khachatryan, Elf Calc \| Backward Frontier Rewrite |
| 946 | 207 → 206 | Asterios Panoras 的笔记本 372207578 |

将官方题目保存为 `data/puzzles.csv`，将以下原件放入 `archives/`。

| 文件名 | 下载来源 |
| --- | --- |
| `asteriospanoras-196.zip` | [asteriospanoras-196](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/196) |
| `asteriospanoras-372207578.ipynb` | [asteriospanoras-372207578](https://www.kaggle.com/kernels/scriptcontent/372207578/download) |

在有 Git 历史的仓库根目录运行以下命令。

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出 `combined/submission.csv` 包含 1,000 道题，SHA-256 为 `208c1f7e839b893f103db0261bb06353fa5810b3a6544d18681a1e5ad7224be9`。等长时保留清单中较早的来源。[仓库逐题署名](../origins.csv)
