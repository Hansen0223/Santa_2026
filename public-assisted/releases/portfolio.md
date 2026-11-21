# 还原 132,502 条候选

第 505、524、563、607、854 题各省一条。第 505 题由 E-Max AI 用 GoodPJW 的求解器缩短，第 524 和 563 题来自 Pardheev。第 607 题在 Asterios 第 191 版署名为 Mizero Lucky Gall，第 854 题来自 Asterios Panoras 的笔记本。五份程序都出现在 E-Max AI 的同一个固定输出中。[原作者及版本](portfolio.json) · [上游资料和求解器](https://www.kaggle.com/datasets/royalacecat/santa-2026-replay-132608-lean/versions/1) · [上一版候选](https://github.com/Hansen0223/Santa_2026/blob/7587ea3/public-assisted/releases/portfolio.md)

将官方题目保存为 `data/puzzles.csv`。在 E-Max AI 笔记本的固定版本打开 Output，下载 `submission.csv` 并保存为 `archives/royalacecat-372191792.csv`。该输入的 SHA-256 为 `d9facfc02930a32925d6f463c71371ffb7bfd54287e1ddd839572b58ace95b10`。[固定笔记本输出](https://www.kaggle.com/code/royalacecat/santa-2026-public-frontier-score-132-608/output?scriptVersionId=372191792)

在有 Git 历史的仓库根目录运行以下命令。

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

生成的 `combined/submission.csv` 包含全部 1,000 题，SHA-256 为 `0f6902ae51ccea2e0ea792a10e08f96405414f140e4f8c9f5a6d10c23c6674ea`。等长时优先采用仓库程序。[仓库逐题署名](../origins.csv)
