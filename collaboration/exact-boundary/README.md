# 第 0649 题怎样从 119 步缩短到 118 步

从官方初值 6 和 29 出发，前后两份完整程序都在 48 个寄存器和题目规定的数值上限内生成全部 32 个目标。改动集中在一个子图。下游需要它算出 25 个数，原来用了 29 步，新程序用了 28 步。逐条解释两份程序，再按操作数的数值比对，可以确认子图外的 90 条算式相同。[两份完整程序和边界见证](case.json)

旧子图的四个辅助数是 7、23、64、361。新子图只需 64、363、7428。以 363 为例，先用已有的 357 加上初值得到它，再分别用它算出 378 和 7065。旧程序先算出 8303 再减去 1238 得到 7065，新程序将这两步的依赖关系倒过来。完整操作顺序见下表，每行按从左到右执行。

| 步数 | 逐步计算 |
| --- | --- |
| 1–4 | 6 ÷ 6 = 1，1 + 1 = 2，6 − 1 = 5，6 ÷ 2 = 3 |
| 5–8 | 2 + 6 = 8，5 + 29 = 34，3 × 5 = 15，3 + 29 = 32 |
| 9–12 | 8 × 29 = 232，34 ÷ 2 = 17，5 × 15 = 75，232 ÷ 2 = 116 |
| 13–16 | 29 × 116 = 3364，3364 − 32 = 3332，8 × 8 = **64**，116 − 64 = 52 |
| 17–20 | 64 − 5 = 59，17 × 52 = 884，6 × 59 = 354，3 + 354 = 357 |
| 21–24 | 354 + 884 = 1238，64 × 354 = 22656，22656 − 17 = 22639，6 + 357 = **363** |
| 25–28 | 15 + 363 = 378，6 × 1238 = **7428**，7428 − 363 = 7065，1238 + 7065 = 8303 |

从旧程序取出仅依赖初值和子图内先前结果、且每个结果不超过 32768 的算式。该子图向外提供 1、2、3、5、8、15、17、32、34、52、59、75、116、232、354、357、378、884、1238、3332、3364、7065、8303、22639、22656。32768 仅用于选取旧子图。后续搜索允许中间结果达到本题的官方上限 128402229799。

## 从官方题面复核

在仓库根目录运行。把从比赛下载、解压的原始 `puzzles.csv` 放在命令指定的位置。脚本仅用 Python 标准库读取题面、核对官方文件哈希、模拟寄存器写入、检查每个目标是否曾被生成，再从两份完整程序中独立核对 25 个边界值和 90 条外部算式。[复核器](verify.py) · [官方数据](https://www.kaggle.com/competitions/santa-2026/data)

```bash
python -B collaboration/exact-boundary/verify.py data/puzzles.csv
```

`case.json` 的 `before` 和 `after` 是两份完整实体，`boundary_program` 是 28 步的独立寄存器程序。每条指令的四个元素为运算符、左输入寄存器、右输入寄存器、目的寄存器。文件还记录了原程序及补丁的 SHA-256。公开原始记录在 Asterios 第 99 版的 `best_programs.csv`，该行 120 步，作者栏原文为 `goodpjw2008, Santa 2026 | DAG LNS + Depth-5 Search | LB 136,240`。本项目先前的 `work/gpu/donor-trusted.csv` 已把它缩短到 119 步。本例再次改写得到 118 步。取得该版本的文件后，可在上述命令末尾加 `--public-reference 路径/best_programs.csv`，同时核对公开行的作者、哈希与全部 120 步。[固定公开版本，Apache 2.0](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/99) · [项目署名](../../public-assisted/NOTICE.md)

## 重跑固定边界搜索

下面用随仓库归档的原生源码编译搜索器，示例输出文件可改到本机临时目录。Windows 上使用 MinGW g++，也可以直接向 `--solver` 传入已经编译好的可执行文件。[原生源码与编译信息](../../proofs/local/work/gpu/wave10/build.json)

```bash
g++ -O3 -std=c++17 -Iproofs/local/work/gpu proofs/local/work/gpu/wave10/sparse_all_limits.cpp -o sparse-boundary.exe
python -B collaboration/exact-boundary/verify.py data/puzzles.csv --solver ./sparse-boundary.exe
python -B collaboration/exact-boundary/small_domains.py ./sparse-boundary.exe
```

实测搜索从 6 和 29 出发，允许永久保留生成的值。预算为三个辅助数时，13477 个节点后返回表中的可行顺序。预算降至两个时，246 个节点后穷尽。因此，**从这两个初值生成这组固定的 25 个边界值，最少需要 28 步**。整题的 118 步是可行上界，改变对下游提供的边界值仍可能继续缩短。

独立的 Python 广度优先穷举还对照了 105 个固定随机实例。数值上限取 13–23，目标数取 2–8，每种目标数与辅助数预算组合抽 5 个实例。三个预算的结果依次为 11 可行 / 24 无解、26 可行 / 9 无解、32 可行 / 3 无解，所有判定一致，69 个可行见证均已逐步复算。实例和判定的摘要为 `194a9e10e0361fe6c417af802b9ce6c720a37c9101dfd85d2695e4e3c0c20c96`。[小域对照程序](small_domains.py)

## 小题重新构造起始常数

从正式初值构造一批至多用三步得到的数。选取能替换原算式的单个数或数对，并和原本算式一起选择。组合候选试了 34 道，独立候选试了 48 道，均未缩短。[逐题结果](seed-basis-menu-results.json.gz) · [实现](seed_basis_menu.py)

## 按短程目标覆盖选取初始算式

从正式初值构造 4、6 或 8 步的可执行前缀，按目标在接下来一两步中可达到的数量筛选。后续倒推仍须将前缀计入得分。组合与独立各 14 道小题，各检查 336 个前缀，均未缩短。[逐题结果](target-supported-prefix-results.json.gz) · [前缀筛选](target_supported_prefixes.py) · [现有倒推引擎](reverse_obligations.cpp)

可用 C++20 编译 `reverse_obligations.cpp`，再将可执行文件传给 `target_supported_prefixes.py --engine`。逐题记录包含引擎指纹、前缀、搜索宽度和种子。

## 从初值向前生成多目标程序

每加一个中间值后立即生成已可达的目标，按接下来还能支持的目标数量选取保留方案。从初值、原顺序截点和部分目标的依赖集合出发。组合组与独立组各 21 道，第 635 题的独立程序由 36 步缩至 35 步。另以三份程序为起点尝试缩短该题 32 步组合解，未进一步缩短。[结果](forward-pressure-results.json.gz) · [采用的程序](forward-pressure-independent-wins.csv) · [试验入口](forward_pressure.py)

扩展数值范围后，另试组合 85 道和独立 84 道。Ertuğrul Özer 第 502 版含 49 道等长替代程序，从有实际中间值差异的小题里选 14 道重新搜索。这三组均未缩短。[逐题结果](forward-pressure-results.json.gz) · [公开版本](https://www.kaggle.com/datasets/ozertuu/santa-2026-verified-programs/versions/502)

## 扩展可登记的精确搜索值域

分片入口也接受已有的通用搜索器。使用固定二进制指纹，合并记录按引擎核对数值上限与分片覆盖。第 388、472 题的首轮已启动，当前下界尚未改变。[通用搜索器构建回执](../../proofs/local/work/gpu/closest-36729/build.json)
