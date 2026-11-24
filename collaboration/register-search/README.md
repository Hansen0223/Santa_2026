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

截取最多六个只有一个去处的根节点，并找出能一同移除的算式。用剩余程序中可独立得到的值作乘数和余数，逆向尝试重建，然后重新分配寄存器。独立组 1000 道题中 51 道共省 56 条。组合组 1000 道题未缩短。第 744 题得到 267 条的算式图，待找到满足 48 个寄存器的顺序。[逐题结果](quotient-chains-results.json.gz) · [采用的独立程序](quotient-chains-independent-wins.csv) · [求解器](quotient_chains.py)
