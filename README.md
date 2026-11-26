# Santa 2026 · The Elf Calculator

[当前分工、已完成的实验和正在搜索的题号](collaboration/STATUS.md) · [本轮进展](PROGRESS.md) · [第 649 题怎样少用一步](collaboration/exact-boundary/README.md)

目前最短的本地候选为 **127,967 条**，尚未提交 Kaggle。北京时间 11 月 26 日 20:57 的榜首为 124,494 条，相差 3,473 条。仓库可直接下载的公开辅助解为 133,594 条，独立解为 139,265 条。[还原当前候选](public-assisted/releases/portfolio.md) · [公开辅助提交](public-assisted/submission.csv) · [独立提交](submission.csv) · [榜单快照](collaboration/leaderboard.json)

每道题从给定的初始值出发，在 48 个寄存器中使用加、减、乘和整除生成全部目标值。程序中的值必须始终为正整数并且不超过题目上限。提交文件包含 `id` 和 `program` 两列，每题最多 4,096 条指令。总分是全部程序的指令数之和，越低越好。合并各项证明的总下界为 38,014 条，当前共有 21 题已证最短，合计 151 条。[逐题证明与运行分工](collaboration/proof-status.md)

## 仓库导航

| 想找什么 | 从哪里开始 |
| --- | --- |
| 当前最短候选、独立生成的候选 | [还原最短候选](public-assisted/releases/portfolio.md) · [公开辅助提交](public-assisted/submission.csv) · [独立提交](submission.csv) |
| 接手任务、查看其他开发者已经试过的方案 | [协作实验索引](collaboration/README.md) · [当前分工](collaboration/STATUS.md) |
| 运行或改进求解器 | [按方法浏览求解器](solvers/README.md) · [统一运行入口](run.py) |
| 找一道题的已知最短程序和已证下界 | [逐题上下界](collaboration/puzzle-bounds.csv) · [证明进展](collaboration/proof-status.md) |
| 追溯历史结果或公开代码来源 | [进展记录](PROGRESS.md) · [历史证明](proofs/) · [协作者证明](proofs_ext/) · [公开求解器与署名](generative/NOTICE.md) |

## 校验与复跑

从比赛数据页取得官方 `santa-2026.zip`，将其中的 `puzzles.csv` 和 `practice_puzzles.csv` 解压到仓库根目录下的 `data/`。前者用于计分，后者用于有标签的练习题实验。仓库中保存求解代码、候选提交和验证记录，官方原始数据由参赛者自行取得。[官方数据页](https://www.kaggle.com/competitions/santa-2026/data)

在仓库根目录运行以下命令即可复核两个总分和提交文件的 SHA-256。验证只需要 Python 3.12 或更新版本的标准库。

```powershell
python -B elf.py data/puzzles.csv submission.csv
python -B elf.py data/puzzles.csv public-assisted/submission.csv
```

从头生成一份新基线时，可运行 `python -B run.py --output candidate.csv --profile quick`。快速档构造混合进制基线并精确求解小题。标准档加入动态算式库、同余余数搜索、因式分解和算式重写。深度档进一步比较寄存器内搜索、算术提示和图合并。发布分数来自多轮独立实验逐题择优。合并过程和每轮采用的程序哈希见[独立结果记录](result.json)。

扩展搜索按算法另需工具。部分 Windows 搜索使用 .NET Framework C# 编译器，C++ 搜索使用 g++，因式分解使用 SymPy，整数规划实验使用 SciPy 或 OR-Tools。OpenCL 实验还需兼容设备和驱动。编译器、实验性可执行文件、SQLite 检查点和大部分候选池保存在原机器的 `work/` 目录。新检出仓库时，重跑特定实验需重新安装相应工具并生成其输入候选。

## 方法和验证

- 混合进制基线尝试多个底数和有符号余数，并共享重复子表达式。
- 动态算式库搜索正负余数、精确因数和邻近乘积。分别尝试在全局依赖图上编译，以及直接限制搜索使用的寄存器。
- 同余搜索允许选择同余类中的多个余数。商变得更容易构造时，即使余数较大，整条算式也能缩短。
- 因式分解利用精确因子、近邻乘积及多个目标共同的因数。
- 依赖图重写搜索可复用的和、差与乘积，删除无用计算。每次修改后重新分配寄存器并重放整段程序。
- 部分题可以从目标值的近似平方和近似乘积恢复一组整数。求解器利用它们的乘法表构造多个目标，同时比较把偏差加在乘法之前或之后的指令数。[结构识别](solvers/matrix/matrix_scan.py)只接收题目数据，[算式构造器](solvers/matrix/matrix_construct.py)可基于恢复的整数重新生成完整的算式。设计算式时仍须支付构造这些整数的成本。
- 独立整数解释器检查 CSV 编码、题目 ID、寄存器索引、无余数除法、值域和目标覆盖。输入寄存器先读取，随后写回目标寄存器。已经生成的目标值被覆盖后仍计为已完成。

早期逐题证明给出的下界为 **36,731 条**。仓库保留其他开发者的逐题证明，复核时可合并各来源对同一道题的最强结论。[本轮证明与复核命令](collaboration/proof-status.md) · [早期逐题上下界](proofs/bounds.csv) · [其他开发者的证明](proofs_ext)

原计数方法如下。对每个目标，先检查给定初值或其他目标能否直接产生它，再计算固定数量的额外中间值最多能覆盖多少个剩余目标。对于两个中间值可以产生多个目标的情况，用和、差、积、整商的所有成对方程精确列举例外。逐题证书同时记录当时可行解的长度。用当前提交运行 `python -B lower_bounds.py data/puzzles.csv public-assisted/submission.csv bounds-current.csv` 可另存一份采用当前可行解的对照表。[逐题证书](work/virtual/certificates.csv) · [证书与输入哈希](work/virtual/certificates.json)

当前主文件中的程序由求解器从官方输入生成，或由这些程序进一步缩短。公开求解器的作者、版本、许可证和本地改动记录在 `generative/NOTICE.md`。每次主文件更新时，`checkpoint.py` 对完整 CSV 进行两次独立重放，并把每题所用来源写入 `origins.csv`。当前总分、文件哈希和历次改进见 `result.json`。实际排名由 Kaggle 提交后的榜单确定。[官方排行榜](https://www.kaggle.com/competitions/santa-2026/leaderboard)

公开辅助候选以 Asterios Panoras 汇总的第 **126** 版为基准。原版重放为 134,185 条，本地逐题择短后省 **572 条**。每题的公开来源、历史许可及本地修改随程序一起发布。[公开辅助结果](public-assisted/result.json) · [逐题署名](public-assisted/origins.csv) · [来源说明](public-assisted/NOTICE.md) · [Kaggle 第 126 版](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/126)

## 持续优化

[已对照的方案与收益](collaboration/methods.md) · [用第 334 题重跑因数分解](collaboration/factor/README.md) · [组合改写的真实案例](collaboration/polish/)

[共享中间值搜索](solvers/native/virtual.cpp)借用 Tony Li 和 konbu17 的整数索引、初始算式与依赖图表示。新搜索器逐轮选择目标，用刚得到的中间值更新可用算式。它比较多个目标对同一中间值的需求，估计目标顺序对后续计算的影响，并把整张图重新编译到 48 个寄存器。以下是一个独立实验示例。在仓库根目录的 PowerShell 中运行，先将本机 MinGW-w64 的 `g++` 加入 PATH。输出是一份新候选。

```powershell
New-Item -ItemType Directory -Force work\virtual | Out-Null
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TEMP=(Resolve-Path work\virtual).Path
$env:TMP=$env:TEMP
g++ -O3 -march=x86-64 -static -std=c++17 solvers/native/virtual.cpp -o work\virtual\rerun.exe
python -B -m solvers.graphs.virtual_search data/puzzles.csv submission.csv work/virtual/rerun.csv --exe work/virtual/rerun.exe --fresh --leaves 86 --width 6 --scan 1 --joins 13 --jobs 4
python -B elf.py data/puzzles.csv work/virtual/rerun.csv
```

对照实验覆盖公开成品程序，因此对照总分须连同其来源和许可一起解读。已逐题复核 2026 年 11 月 19 日发布的 138,460 条指令版本。[公开 Notebook 的固定版本](https://www.kaggle.com/code/kindasomethin/santa-2026-exact-portfolio-frontier-138460?scriptVersionId=371361105)

[比赛说明和评分](https://www.kaggle.com/competitions/santa-2026/overview) · [官方数据和计算规则](https://www.kaggle.com/competitions/santa-2026/data) · [比赛规则](https://www.kaggle.com/competitions/santa-2026/rules)

官方赛程的报名截止为北京时间 2027 年 1 月 22 日 07:59，最终提交截止为北京时间 2027 年 1 月 29 日 07:59。[官方赛程](https://www.kaggle.com/competitions/santa-2026/overview#timeline)
