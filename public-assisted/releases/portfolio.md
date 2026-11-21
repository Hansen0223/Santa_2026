# 还原 132,496 条候选

本地第 190 题的独立程序由 116 条缩短到 114 条。在目标分组试验中，直接搜索得到这一结果。[逐题搜索记录](../../collaboration/target-partition/donor-mask-results.json.gz)

Pardheev 的公开程序让第 505 题从 106 条降到 105 条，第 809 题从 109 条降到 108 条。Asterios Panoras 的 34 条程序比仓库此前的第 880 题程序短两条。三个程序均来自固定版本笔记本。[逐题差额与原作者](portfolio.json) · [上一版 132,498 条候选](https://github.com/Hansen0223/Santa_2026/blob/a96acd4/public-assisted/releases/portfolio.md)

将官方题目保存为 `data/puzzles.csv`，再把下表中的三个文件保存到同一 `archives/` 目录。重建程序从笔记本中读取已发布的算式。

| 保存的文件名 | 来源 |
| --- | --- |
| `royalacecat-372191792.csv` | [E-Max AI 固定版本的 Output 中下载 submission.csv](https://www.kaggle.com/code/royalacecat/santa-2026-public-frontier-score-132-608/output?scriptVersionId=372191792) |
| `pardheev-372197498.ipynb` | [Pardheev 笔记本原件](https://www.kaggle.com/kernels/scriptcontent/372197498/download) |
| `asteriospanoras-372197665.ipynb` | [Asterios Panoras 笔记本原件](https://www.kaggle.com/kernels/scriptcontent/372197665/download) |

在有 Git 历史的仓库根目录运行以下命令。

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

生成的 `combined/submission.csv` 包含全部 1,000 题，SHA-256 为 `a1af826e648e3f1a688cd571821394b465dc3600e37d9028eeed3d22fffdca61`。等长时保留清单中最靠前的程序。[仓库逐题署名](../origins.csv) · [E-Max AI 汇总的上游资料](https://www.kaggle.com/datasets/royalacecat/santa-2026-replay-132608-lean/versions/1)
