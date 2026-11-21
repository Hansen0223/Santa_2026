# WorkBuddy 可复现改进（2026-11-21 16:38）

基线为远端 `main` 的 `d33a49a`（独立候选 139,767 条，sha256 `3b82307693b3717bed485c37d133917add76d5faa4791942b604c0480f8b0872`；公开辅助候选 133,644 条，sha256 `139ada409d31632f0f73403e8be4c2cdf87f9babbd164fb860a52622d15f8453`）。

| 题号 | 候选线 | 原长度 | 新长度 | 方法 |
|---|---|---:|---:|---|
| scored_0235 | 独立候选 | 201 | 200 | `solvers/graphs/algebra_rewrite.repair_algebra`（四轮代数重结合，全库扫描） |
| scored_0246 | 公开辅助候选 | 114 | 113 | 从独立候选逐题移植（独立解更短） |
| scored_0268 | 公开辅助候选 | 200 | 199 | 同上 |

合并后：独立 **139,766** 条（sha256 `0db6279e106917218dfbe8d51addc436dfcb21464df13598510ec826a39b4568`），公开辅助 **133,642** 条（sha256 `108b871eea82c4d51ea8b64e80ee36bef919028639a1c379844d75967f98e34a`）。三条程序都用 `elf.check` 独立重放确认，且严格短于各自父本；移植行的署名同步更新到 `public-assisted/origins.csv`。

复核命令（仓库根目录）：

```bash
python -B elf.py data/puzzles.csv submission.csv
python -B elf.py data/puzzles.csv public-assisted/submission.csv
python -B collaboration/wb-contributions/apply.py
```

负结果也一并记录，避免重复开跑：对公开辅助线跑过 Wang 三模式（anneal_diverse / incremental / compact_rotate，各 360 轮）、虚拟寄存器 style=1（40 题）、短题全域合成与全库代数重写，均未产生严格缩短；对独立候选 139,767 的代数全库扫描只有 `scored_0235` 一处收益。
