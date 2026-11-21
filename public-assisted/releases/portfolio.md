# 还原 132,521 条候选

仓库程序、Rudolph 第 124 版和 Asterios 第 187 版逐题取短，可重建全部 1,000 题。相对上一版，第 793 题从 204 条缩到 203 条。[合并清单及各项哈希](portfolio.json) · [前一版 132,522 条的逐题来源](https://github.com/Hansen0223/Santa_2026/blob/ea89a53/public-assisted/releases/portfolio.md)

将官方比赛文件放在 `data/puzzles.csv`，将两份原始 ZIP 放在 `archives/`。

| 文件名 | 固定版本 | 重放指令数 |
| --- | --- | ---: |
| `alexchilton-124.zip` | [Alex Chilton 的 Rudolph 第 124 版](https://www.kaggle.com/datasets/alexchilton/santa-2026-rudolph-programs/versions/124) | 132,625 |
| `asteriospanoras-187.zip` | [Asterios Panoras 第 187 版](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/187) | 132,627 |

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出文件为 `combined/submission.csv`，SHA-256 为 `90f8a2068c2a3ab8836a5fa4e9bb31941b59fef32483b325f035d3928fd80b75`。等长时依次优先采用仓库、Rudolph、Asterios 的版本。Asterios 的逐题来源表将第 793 题标注为 public merge。该版发布说明记为 132,626，下载文件的逐题指令数和实际重放均得到 132,627；本次使用第 793 题的 203 条程序。[仓库逐题署名](../origins.csv)
