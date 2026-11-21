# 还原 132,522 条候选

从仓库固定版本、Ishan Karnick 第 5 版和 GoodPJW 第 41 版中逐题取短，即可还原全部 1,000 题。相对上一次的 132,530 条，Ishan 在第 68、142、295、390、563、736 和 907 题各省 1 条，GoodPJW 在第 930 题省 1 条。[逐题改进与输入哈希](portfolio.json)

将官方比赛文件放在 `data/puzzles.csv`，将下列原始 ZIP 放在 `archives/`。

| 文件名 | 来源 |
| --- | --- |
| `ishankarnick-5.zip` | [Ishan Karnick 第 5 版](https://www.kaggle.com/datasets/ishankarnick/santa-2026-frontier-programs/versions/5) |
| `goodpjw2008-41.zip` | [GoodPJW 第 41 版](https://www.kaggle.com/datasets/goodpjw2008/santa-2026-dag-lns-programs/versions/41) |

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出文件为 `combined/submission.csv`，SHA-256 为 `241d5566e47ac6453371f567c6a61f1b620958cccde1fb3e6d71a4084da9750e`。等长时优先采用表内较早的来源，仓库优先。Ishan 的 `sources.csv` 将新增的七道题均归于其图搜索或自有求解器，其 `CREDITS.md` 列出 Wang Jakie 的搜索代码及原始程序贡献者。GoodPJW 第 930 题来自 `our_programs.csv`。[仓库逐题署名](../origins.csv)
