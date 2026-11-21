# WorkBuddy round-3：ultra 构造式搜索续批

基线为远端 `main` 的 `9f90613`（公开辅助候选 133,641 条）。

继续以当前公开辅助程序为父本，运行仓库自带的构造式搜索器 `solvers/graphs/virtual_search.py` + `solvers/native/virtual.cpp`，参数 `--leaves 160 --width 10 --scan 2 --joins 16383 --style 5 --tail 6`，用不同随机种子覆盖剩余题目，逐题取严格更短的程序。

| 题号 | 原长度 | 新长度 | 来源文件 |
|---|---:|---:|---|
| scored_0054 | 194 | 193 | round3-wins.csv |
| scored_0944 | 210 | 209 | round3-wins.csv |

合并后公开辅助候选 **133,639** 条（sha256 `22243279c78b9f1e02f89a7a42fea43b21141870f7c7e9302bbcf3aabb52e0da`）。所有新程序均经 `elf.check` 逐题重放，并用 `elf.py` 对完整 1,000 题复核；改进题署名已同步写入 `public-assisted/origins.csv`。独立候选线未改动，以保持其独立性。

复核命令：

```bash
python -B elf.py data/puzzles.csv public-assisted/submission.csv
```

`wins.csv` 只含本批改进题的程序，可直接逐题重放或移植。
