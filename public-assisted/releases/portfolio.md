# 还原 127,798 条候选

Asterios Panoras 第 415 版通过完整回放，共 127,799 步。与上一版组合解相比，11 道题共缩短 14 步，逐题来源标为 Sargis Khachatryan 和 Ross Wade。加上第 678 题的本地补丁，组合解为 127,798 步。[固定归档](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/415) · [版本对比与逐题署名](../../collaboration/evidence/public-archives-20261126-v415.json) · [本地补丁](../../collaboration/recipe-union/asterios414-0678-win.csv) · [上一版](https://github.com/Hansen0223/Santa_2026/blob/6b5703b/public-assisted/releases/portfolio.md)

将官方题目保存为 `data/puzzles.csv`，并将固定归档保存为 `archives/asteriospanoras-415.zip`。在仓库根目录运行以下命令。

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出包含 1,000 道题，SHA-256 为 `dabe2980e5b29807482d81d73568a118a28ca215ed8683599382e20a333ab9b3`。[清单](portfolio.json)
