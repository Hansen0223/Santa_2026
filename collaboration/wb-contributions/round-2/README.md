# WorkBuddy 第二批改进：ultra 构造式搜索

基线为远端 `main` 的 `c5ed33d`（公开辅助候选 133,642 条，sha256 `108b871eea82c4d51ea8b64e80ee36bef919028639a1c379844d75967f98e34a`）。

以当前公开辅助程序为父本，运行仓库自带的构造式搜索器 `solvers/graphs/virtual_search.py` + `solvers/native/virtual.cpp`，参数 `--leaves 160 --width 10 --scan 2 --joins 16383 --style 5 --tail 6`（`--joins 16383` 为全部移动），逐题取严格更短的程序。

| 题号 | 原长度 | 新长度 | 来源文件 |
|---|---:|---:|---|
| scored_0996 | 117 | 116 | virtual-ultra.csv |

合并后公开辅助候选 **133641** 条（sha256 `166aba96fbc9e0621878e4b33dce8c7fb0a9e79184e79cd2bdfa1d8e92f6c73a`）。所有新程序均经 `elf.check` 逐题重放，并用 `elf.py` 对完整 1,000 题复核。改进题的署名已同步写入 `public-assisted/origins.csv`；独立候选线未改动，以保持其独立性。

复核命令（仓库根目录）：

```bash
python -B elf.py data/puzzles.csv public-assisted/submission.csv
```

`wins.csv` 只包含本批改进题的程序，可直接用于逐题重放或移植。

## 本批已排除的负结果（避免重复开跑）

- 仓库内 948 个文件的 4,983 条历史程序逐题择优：公开辅助线 0 条更短。
- 物理寄存器指令级单条删除 / 后缀截断 / 连续窗口删除（k=2..6）：两条线共 2,000 题 0 命中。
- 多父本 `anneal_seeded`（24 题 400 轮等若干批次）：0 增益。
- `solvers.graphs.mix` 用 9 份候选全库交叉重组（trials 5 / passes 8 / --joins）：0 增益。
- `solvers.graphs.whole_pools` 放大到 109 题 / 12,000 visits / 5 种值池宽度：0 增益。
- 独立候选已无短于公开辅助线的题目（146 题等长），跨线移植空间用尽。
