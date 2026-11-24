# 超过 48 个数时，回收已用完的寄存器

固定 10 道题。两条路线均从一份可运行的父程序出发。先把原算式重新排入 48 个寄存器作对照，再用相同题号种子搜索 96 轮。两组共完成 1,920 轮。20 个父程序都能重排，单独重排节省 0 条指令。[预登记题号及输入指纹](design.json) · [重排对照](compile-control.json)

| 来源 | 题号 | 父程序 | 新程序 | 使用的寄存器数 | 首次找到的轮号，从 0 起 |
| --- | --- | ---: | ---: | ---: | ---: |
| 独立 | 0541 | 55 | 54 | 24 | 28 |
| 公开辅助 | 0773 | 43 | 42 | 18 | 92 |

第 773 题有 7 个初值。若每条指令都占一个新寄存器，42 条指令需要 49 个位置。每次最后一次使用某个数后回收它的寄存器，实际只需 18 个。该题父程序的上游署名是 Ertugrul Ozer, 138,867 SOTA Verified Portfolio。[原始署名](assisted-origin.csv) · [公开辅助结果](assisted-wins.csv) · [各轮计数](assisted-wins.json)

第 541 题使用纯独立父本。重新选择算式后的 54 条程序追平当时的公开辅助上界。两条路线其余各 9 道在本次预算内均无严格缩短。[独立结果](own-wins.csv) · [各轮计数](own-wins.json)

## 复现

在仓库根目录运行。使用官方 `data/puzzles.csv`、Python 和 GNU C++17。父程序从 Git 提交提取以保持字节指纹。工作目录用于保存可执行文件及临时结果。

```powershell
python -c "from pathlib import Path; Path('work/register-check').mkdir(parents=True,exist_ok=True)"
python -c "import subprocess; from pathlib import Path; d=Path('work/register-check'); (d/'own.csv').write_bytes(subprocess.check_output(['git','show','2e04c7a:submission.csv'])); (d/'assisted.csv').write_bytes(subprocess.check_output(['git','show','2e04c7a:public-assisted/submission.csv']))"
python -B collaboration/puzzle-0711/make_sparse.py work/register-check/sparse.cpp
python -B collaboration/puzzle-0711/wide/make_large.py work/register-check/sparse.cpp work/register-check/large.cpp
g++ -O3 -static -std=c++17 work/register-check/large.cpp -o work/register-check/large.exe
python -B collaboration/register-search/compare.py own work/register-check/own.csv data/puzzles.csv work/register-check/large.exe work/register-check/own-wins.csv
python -B collaboration/register-search/compare.py assisted work/register-check/assisted.csv data/puzzles.csv work/register-check/large.exe work/register-check/assisted-wins.csv
```

原搜索使用 Windows MinGW GCC 16.2.0。使用其他标准库时，随机采样顺序可能不同。[编译配置及原始方法](../puzzle-0711/wide/README.md)

## 保留部分重新计算的指令

从提交 `aacd89c` 的独立程序中筛出第 493 题，原版用 251 条指令，包含 8 次重复计算。把部分重复计算的使用者改接到第一次产生该数的位置，在原有运算顺序上重新分配寄存器，得到 249 条。把八次重复全部折叠并搜索其他顺序的这次尝试没有得到更短的可执行程序。

在仓库根目录运行 `python -B collaboration/register-search/spill_copies.py --id scored_0493 --puzzles data/puzzles.csv --parents old.csv --output wins.csv`，其中 `old.csv` 可从上述提交中的 `submission.csv` 取得。[缩短后的程序](scored-0493.csv)

## 在较大的临时工作区中搜索

在实时占用寄存器较多的程序上，先用 72 个位置寻找更短的算术图，再把它排回正式比赛的 48 个寄存器。对同一父本也从 48 个寄存器直接搜索。两条路线各取 36 道。[输入和题号](relaxed-design.json) · [程序](relaxed_search.py)

36 道独立题中 20 道探索到第 49 个或更高的位置；36 道公开辅助题中有 5 道。两组均未缩短完整程序，结束这一方向。[结果](relaxed-results.json.gz)

## 从实际寄存器内容求解未完成的目标

在原程序的 25% 和 55% 处切开。把此刻寄存器里的值作为新题的初值，运行 Wang Jakie 的 `anneal_diverse`。原题只需产生尚未完成的目标。把缩短的后半段接回原程序，再按需删去未被使用的运算。对照组直接从同一份完整父程序出发。每次单独搜索固定为 520 轮；两个截点各跑一次，对照跑一次。

独立组取 `f6aaa58` 中所有至少 45 条的程序，共 874 道。直接搜索省 13 条，两个截点逐题择短省 27 条，23 道的截点结果严格优于直接搜索。三组取短后 36 道省 39 条。另在 68 道独立题尝试用已算出、随后被覆盖的值替换闲置输入位置，合入其新增结果后，共有 38 道独立题省 41 条。组合候选上分别尝试 120 道和 84 道，均未缩短。[后半段求解](suffix_search.py) · [恢复旧值](recover_prefix.py) · [逐题结果、父程序及引擎指纹](suffix-results.json.gz) · [38 道改进](suffix-independent-wins.csv)

例如运行 `python -B collaboration/register-search/suffix_search.py --puzzles data/puzzles.csv --parent submission.csv --binary /path/to/anneal_diverse --out scratch/suffix --count 1000 --rounds 520`。复现实验须使用上文固定版本的独立父程序。[Wang 引擎与署名](../../generative/wang/NOTICE.md)

## 拼接两份不同程序的前段与后段

在同一题的两份历史程序中选取截点。当前段缺少后段需要的值时，允许补最多三个输入，每个输入最多新增两次计算。把拼接结果重新分配到 48 个寄存器后，挑两份不同的候选分别继续搜索 430 轮，与同一随机种子下从原程序直接搜索 430 轮的结果比较。

独立组覆盖所有符合此次父本筛选条件的 341 道题，320 道生成了可执行拼接。第 790 题直接拼出 228 条，比原程序短 1 条。拼接及其后续搜索在 9 道题上严格胜过直接搜索；三种起点逐题取短，19 道各省 1 条。第 985 题的直接搜索结果为 108 条，同时缩短了仓库的公开辅助解。组合组抽取 86 道，均产生了拼接，完整程序长度未缩短。[程序](stitch_programs.py) · [来源、分组及全部结果](stitch-results.json.gz) · [19 道改进](stitch-independent-wins.csv)

运行入口接受 `--puzzles`、`--parent`、`--donors`、`--engine`、`--out` 及 `--count`。独立父本出自 `87bfed4`，组合父本由 `c191762` 中的清单生成。结果文件的 `donor_sources` 包含每个旧程序的 Git 版本或外部归档地址。公开归档中的 CSV 取出 id 和 program 两列后用本仓库的 write_submission 规范化。[Wang 搜索引擎来源](../../generative/wang/NOTICE.md)

## 从中间截取连续的一段程序重新求解

对原程序按首次产生数值的顺序、离初值的距离、离末端的距离分别排序。最多选三个区间，保留区间以外仍需用到的出口。区间内除必需输入外还可以借用从初值独立可达的数。重写后拼回整题，与相同种子下从完整原程序直接搜索的结果比较。

独立组覆盖全部 896 道至少 35 条的题。逐题取短，23 题合计省 25 条，其中 14 题的中段重写胜过直接搜索。组合组覆盖全部 887 道符合条件的题。第 374、681、944 题各由中段重写省 1 条，第 110 题由直接搜索省 1 条。第 110 题同一程序也在独立组生成。[逐题结果及运行设置](interior-band-results.json.gz) · [独立改进](interior-band-independent-wins.csv) · [组合改进](interior-band-assisted-wins.csv)

使用 `interior_bands.py --puzzles data/puzzles.csv --parent FROZEN.csv --engine ANNEAL_DIVERSE --out scratch/interior --count 1000`。输入取自 `37cfdb7` 的独立提交和该版本清单还原的组合提交。编译原有 Wang 搜索引擎的说明与改动随仓库发布。[Wang 引擎](../../generative/wang/NOTICE.md)

## 按依赖关系划分不连续的子程序

从指令依赖图的拉普拉斯特征向量选取子区域，补上区域内两点之间的依赖路径。每题最多优化三个区域，将它们的输出放回原题，再比较同一种子的整题直接搜索。底层算式搜索来自 Wang Jakie。独立组 119 题，逐题择短在 3 题省 3 条，其中 1 题的区域搜索优于整题对照。组合组 138 题，在 1 题省 1 条，其中 1 题的区域搜索优于对照。[逐题结果](spectral-regions-results.json.gz) · [分区搜索](spectral_regions.py) · [搜索引擎来源](../../generative/wang/NOTICE.md)

运行 `python -B collaboration/register-search/spectral_regions.py --puzzles data/puzzles.csv --parent PARENT.csv --engine WANG --out OUTPUT --count COUNT`。独立父本为 `82d0de0:submission.csv`，组合父本为 `c42f416` 的 portfolio。完整记录含引擎指纹、选区、各区和对照结果。

## 重建供其他算式使用的小数

从原程序中截取可以仅凭初值及其他小数构造的子程序，保留外部程序实际读取的值。在三个上限下枚举备选算式并求解，再放回原题，用官方题目重放。组合组 150 道题试了 391 个子程序，均未缩短。
独立组 150 道题省 0 条。
结构线索来自 Sadam Torres 对共享常量的公开分析。[固定版本](https://www.kaggle.com/code/sadamtorres/santa-2026-the-elves-left-their-scratch-paper?scriptVersionId=373154578) · [求解器](small_dictionary.py) · [逐题结果](refresh-128501-results.json.gz)

## 从结果向后寻找商和余数

截取最多六个只有一个去处的根节点，并找出能一同移除的算式。用剩余程序中可独立得到的值作乘数和余数，逆向尝试重建，然后重新分配寄存器。独立组 1000 道题中 51 道共省 56 条。组合组 1000 道题未缩短。第 744 题得到 267 条的算式图，尝试分别移动单条指令和整段指令，另换了两份同长度算式，尚未找到满足 48 个寄存器的执行顺序。[逐题结果](quotient-chains-results.json.gz) · [采用的独立程序](quotient-chains-independent-wins.csv) · [求解器](quotient_chains.py)

## 从两端相遇，再尝试合并两段算式

从目标一端反推全部四种运算的未知操作数，从已知值一端枚举可一步得到的整数。当两端相遇时，将候选重新放入原题检查。独立组全量 1,000 道中有 4 道各省 1 条，组合组扩大到全部 1,000 道，未缩短。

另一项试验比较不同截断位置的新路径。同一个新值出现在两段互不重叠的子程序中时，尝试只计算一次。独立组 150 道提出 272 对长度可能更短的路径，完整重排后均未缩短。组合组 145 道没有形成这样的成对路径。[逐题结果](two-sided-chains-results.json.gz) · [采用的独立程序](two-sided-chains-independent-wins.csv) · [两端搜索](two_sided_chains.py) · [成对重建](joint_chains.py)

## 临时增大寄存器容量后再恢复比赛限制

对组合解中寄存器占用较高的 120 道，以及独立解的 100 道，分别在原始限制、增加 1 个和增加 4 个寄存器的条件下搜索。两组均未缩短。单独重建第 744 题的 267 步算式时，增加 6 个和 10 个寄存器的两组都得到 267 步程序，恢复到 48 个寄存器后仍未找到可用顺序。组合评分沿用 268 步。[逐题结果](relaxed-registers-results.json.gz) · [求解器](relaxed_registers.py)

## 两层共享中间值和小题的候选算式

从不同目标反推它们需要的中间值，再检查这些值能否从同一个新中间数出发得到。独立组 881 道，其中第 993 题 220 → 219。组合组 875 道未缩短。[逐题结果](shared-levels-results.json.gz) · [采用的程序](shared-levels-independent-wins.csv) · [求解器](shared_levels.py)

另选候选解接近已证下界且长度至多 33 的 38 道题，枚举可用数的一步结果与目标的逆向算式。用 8、30、100 个备选的三组均未缩短组合解。[逐题结果](boundary-ensembles-results.json.gz) · [求解器](boundary_ensembles.py)

## 分叉共享和加减重组

尝试先算一个新中间数，再由它构造两个不同中间数供多个结果使用。两组分别试了仅针对终端目标，以及同时针对被多个结果读取的中间数。独立组 156 + 241 道、组合组 166 + 252 道，均未缩短。两种分组的题目有重叠。[求解器](shared_forks.py)

把连在一起的加减算式展开成带符号的输入数列，尝试让多个输出共享同一对加减。独立和组合各 200 道均未缩短。另在 19 道小题上用至多三个操作替换原有中间数，组合解也未缩短。[加减重组](signed_overlaps.py) · [小题替换](two_hop_replacements.py) · [全部逐题结果](shared-forks-and-signed-results.json.gz)

## 分解目标附近的整数

用现有的小数作为偏移量，对截取算式的目标加减该偏移后做有界因数分解。只保留两个因数都能自现有值一步构造的方案。以 128,494 步组合解为父本，97 道题共试 99 个截取位置，没有得到符合该条件的乘积，组合解未缩短。[逐题结果](nearby-factors-results.json.gz) · [求解器](nearby_factors.py)

## 在原指令之间插入新算式

保持部分原指令的顺序，对其余指令枚举合法交错方式。另一种方法从最后一条指令向前安排，按尚需保留的值筛选部分顺序。两法在 200 个小算例中与枚举全部拓扑顺序一致。第 744 题以 128,494 步组合作为父本，尝试原顺序、局部窗口及最大宽度 8,192 的反向搜索，均无法将已有的 267 条算式装入 48 个寄存器，仍使用原 268 条程序。[逐项结果](interleave-schedule-results.json) · [实现](interleave_schedule.py)

在提供题目和组合父本文件后，运行 `python -B collaboration/register-search/interleave_schedule.py --puzzles PUZZLES.csv --parent PARENT.csv --out OUTPUT --puzzle-id scored_0744 --root 966557520839863841` 可重跑固定原顺序和反向搜索。

## 同时重建一对共享算式的目标

拆掉仅服务于该目标对的算式。分别尝试从保留算式开始、保留一个共享中间数再重建，或让后完成的目标复用先完成目标的中间数。独立组覆盖 893 道题，第 314 题 200 → 199，第 903 题 158 → 157。组合组试了 200 道，未缩短。另允许替代起点多用一步，在 120 道中实际继续搜索了 97 道的 189 个不同起点，与同预算直接搜索均未缩短。[逐题结果及公开来源核对](pair-exclusive-cuts-results.json.gz) · [采用的独立程序](pair-exclusive-cuts-independent-wins.csv) · [实现](pair_exclusive_cuts.py)

## 先完成一组目标，再搜索剩余程序

把一组目标及其依赖提前安排，实际分配寄存器后从这个截点继续搜索。对照采用相同长度的原顺序截点和整题搜索，轮数与种子相同。独立组 126 道，第 846 题 99 → 98，两种对照均为 99。 此后扩大到另外 240 道独立题。逐题择短后 3 道共省 4 步，其中 0 道按目标划分的结果严格优于两种对照。组合组 102 道，未缩短。另对组合组所有 870 道符合筛选条件的题尝试只重排，其中 832 道得到新截点，长度均未缩短。[逐题结果](target-frontier-results.json.gz) · [采用的程序](target-frontier-independent-wins.csv) · [实现](target_frontier_cuts.py)

同一轮在组合解的另外一组 96 道中，复跑两个联合替换中间数的版本，均未缩短。两个版本分别检验 1,215 和 1 个三值移除情形。所用引擎、种子策略及逐题计数已一并存档。[逐题结果](target-frontier-results.json.gz) · [联合替换](../../solvers/native/cooperative_exchange.cpp) · [分阶段替换](../../solvers/native/staged_exchange.cpp)

## 用两个新中间数合成第三个

先找能从已有值一步算出的两个新中间数，再检查两者是否能合成供另一条算式使用的第三个。一起估算哪些旧算式会失去全部使用者，并和保留同一批单步算式的对照比较。独立组覆盖 880 道题，第 447 题 230 → 229，第 902 题 223 → 222，两题均仅加入联合算式后缩短。组合组的 875 道符合筛选条件的题跑完，其中 270 道进入算式选择，两组均未缩短。[逐题结果](helper-triangles-results.json.gz) · [采用的独立程序](helper-triangles-independent-wins.csv) · [实现](helper_triangles.py)

完整组合组使用 `python -B collaboration/register-search/helper_triangles.py --puzzles PUZZLES.csv --parent PARENT.csv --out OUTPUT --count 1000 --width 170 --allow-direct --joint`，需在 Python 环境安装 OR-Tools。

## 倒推时保留接近已有算式的数

倒推时把一半候选位置留给最靠近已有值或一步正向结果的数。与只按原顺序保留候选比较，搜索宽度和截取位置数量相同。独立组的两路各跑完 1,000 道，加入新筛选省 9 条，原筛选省 3 条，两组并取逐题最短后 10 道各省 1 条。组合组的新筛选覆盖全部 1,000 道，未缩短。另对组合与独立各抽 240 道，专门重建多个目标共用的中间数，试了 90 和 112 个截取位置，均未找到更短的替代算式。[逐题结果及公开核对](inverse-proximity-results.json.gz) · [采用的独立程序](inverse-proximity-independent-wins.csv) · [实现](two_sided_chains.py)

在冻结父本上运行 `two_sided_chains.py --puzzles PUZZLES.csv --parent PARENT.csv --out OUTPUT --count 1000 --roots 8 --width 24 --proximity`。去掉 `--proximity` 重跑原筛选，加 `--shared` 改选两条以上目标支路共用的值。

## 用两步造出一个供多条算式复用的数

为两条以上原算式寻找同一个可复用的中间数。组合组 350 道与独立组 650 道没有通过保守的依赖筛选。允许一起重建原输入后，组合 130 道与独立 180 道进入算式选择，未缩短。再允许替代程序多一步并要求实际用到新算式，两组共 260 道未找到能执行的起点，其中 252 道在预算内未决。人工例从 9 步缩至 4 步，同样条件下只允许一步构造的对照为 5 步。[逐题结果](composed-hubs-results.json.gz) · [实现](composed_hubs.py)

## 放大局部结果后再整除

先造出目标值的整数倍，用带正负余数的乘积表示分子，最后做整除。同一个截取位置也直接构造原值作为对照。筛选后的组合 875 道与独立 880 道已全部检查，分别覆盖 2,350 和 2,748 个截取位置。两组在本次范围内均未找到更短的替代算式。人工例从 37、53、17、11 出发，能用三步构造 116。[逐题结果](scaled-numerators-results.json.gz) · [实现](scaled_numerators.py)

## 临时减少寄存器，再按正式限制继续搜索

以原程序的峰值需求为基准，尝试少用 3 或 6 个寄存器。将原算式重排或按需重算后，在较小容量下搜索，再恢复官方容量继续搜索。与两段都按正式容量搜索的对照使用相同种子和轮数。独立组 195 道中 162 道得到合格的较小容量起点，逐题从全部组取短共省 3 步，其中 1 道的较小容量起点及后续搜索胜过两段正式容量对照。组合组 165 道中 128 道得到合格起点，组合评分未缩短。[逐题结果](tight-register-results.json.gz) · [采用的独立程序](tight-register-independent-wins.csv) · [实现](tight_register_search.py)

## 省略一次写入并替换使用它的算式

沿原有执行顺序删除一步，先尝试用当时寄存器里的数重建受影响的各步，再尝试延长此前算出的数的保留时间并重新分配寄存器。128,492 步组合解、独立解和仓库公开辅助解各试 1,000 道，均未缩短。[逐题记录](omit-physical-write-results.json.gz) · [实现](omit_physical_write.py)

## 用同一对整数重建两个中间结果

分别反解加、减、乘、除的六种搭配，再开放其中一个结果做一步额外变换。独立组 240 道、组合组 180 道测试前者，分别从中取 165、125 道测试后者。组合组有少量可编排的新方案，两组最终均未缩短。[逐题结果](dual-operation-results.json.gz) · [实现](dual_operations.py)

第 744 题把 267 步候选的中间数保留区间放入完整的寄存器容量约束，限时未得到可行编排，仍保留 268 步程序。[结果](register-intervals-result.json) · [实现](register_intervals.py)

## 同时重建一个中间值的所有使用者

替换同一中间值的全部直接使用者。组合 180 道、独立 220 道测试一个新共享值，再各取 118、145 道允许两个。另对组合 52 道、独立 74 道在固定输入下做分片内穷举。两路均未缩短完整程序。[逐题结果](fanout-results.json.gz) · [候选构造](fanout_repair.py) · [固定输入搜索](fanout_exact.py)
