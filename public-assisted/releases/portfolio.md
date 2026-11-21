# 还原 132,532 条候选

从 GoodPJW 的第 40 版完整程序、仓库两个固定版本的程序表及本地搜索结果逐题取短。官方题面和一份公开 ZIP 即可还原全部 1,000 题。[输入与逐题改进](portfolio.json) · [GoodPJW 第 40 版](https://www.kaggle.com/datasets/goodpjw2008/santa-2026-dag-lns-programs/versions/40)

将官方比赛的 `puzzles.csv` 放入 `data/`，将第 40 版 ZIP 原样保存为 `archives/goodpjw2008-40.zip`。在仓库根目录运行：

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

提交文件为 `combined/submission.csv`，完整程序的 SHA-256 为 `7a153aa475b2c8170509f111f281e5c6d57fbb4ebd8ccdb2215f88f046d0c122`。清单记录源文件的哈希、仓库提交及上游页面。GoodPJW 的公开汇总保留其原贡献者的署名，Atakan Aldemir 和 Wang Jakie 的算法署名见原 ZIP 内的 NOTICE。

对比上一版，第 111、618 题各省 1 条，Hiyohane 的第 374 题从 213 条降到 211 条。[第 374 题的提交](https://github.com/Hansen0223/Santa_2026/commit/0521078c877f1fea6b02d4409973cf9ef9b5f612)
