# 第 882 题的 22 步解至少需要 6 个新辅助值

五份独立程序用过 **20 个不同的辅助值**。如果本题存在 22 步解，其中至少 **6 个辅助值**必须来自这 20 个数以外。当前全局下界仍是 22 步，已知程序为 23 步。这里的结果限定了还能产生 22 步见证的整数选择。[全局下界](../../proofs/local/proofs/helper-wave17.json) · [五份可回放程序及其来源](parents.json)

第五档固定 5 个旧值，允许另外 5 个任意值。全部 15,504 组都已排除。[第五档推导与复验](five-new.md)

另已找到一份 25 条的程序，13 个辅助值中只有 1 个落在旧集合。可作为搜索 22 条解的另一种起点。[程序和复现方法](novelty-search.md)

在不限制新旧辅助数的 22 条搜索中，原先达限的分片 (11, 4) 已细分为 24 格，全数排除，决策共 134,090,359 个节点。可以从本目录运行 `python -B verify_h10_cell.py --puzzles ../../data/puzzles.csv` 复核，再用编译的搜索引擎指定 `--all` 重跑。[24 格证据](h10-cell-11-4.json) · [复核程序](verify_h10_cell.py)

| 从 20 个旧值中指定的个数 | 另外允许的任意整数个数 | 指定子集总数 | 分片 | 展开节点 | 结果 |
| ---: | ---: | ---: | ---: | ---: | --- |
| 9 | 1 | 167,960 | 16 | 171,754 | 全部无解 |
| 8 | 2 | 125,970 | 32 | 9,645,718 | 全部无解 |
| 7 | 3 | 77,520 | 256 | 557,154,081 | 全部无解 |
| 6 | 4 | 38,760 | 256 | 94,901,836 | 全部无解 |

第四档另用通用遍历独立跑完同样的 38,760 个子问题，共展开 79,443,526 个节点。两种实现共用整数运算规则和目标闭包。第一种增量维护可达值，第二种在每一层重新枚举当前值的全部配对，并在剩余三个辅助数时检查可行条件。两边的全部 256 个分片均已结束。[通用遍历的完整回执](four-new-generic.json)

五份程序长度为 23、24、23、23、23。第一份来自独立提交，第二份来自较早的独立存档。另三份在独立程序的算术候选池中寻找等长解，经目标闭包还原为可执行指令。文件给出每份程序的全部指令、辅助值清单、原始存档名与 SHA-256，复核器从官方题目重新执行五份程序并重建并集。[一个新值的分片](one-new.json) · [两个新值的分片](two-new.json) · [三个新值的分片](three-new.json)

## 为什么这些子集已足够

本题必须首次生成 12 个不在初值中的目标。先前的全局证明已经排除仅用 9 个辅助值，所以任意 22 步解恰好引入 10 个不同辅助值。若其中最多 4 个不在这 20 个数中，则至少有 6 个在其中。把任意这样的 6 个旧值也列为必生成目标，原解至多还需 4 个不限来源的辅助数。一共有 `C(20,6) = 38,760` 种选择，完整穷举全部返回无解。前三档同理。即使另外的数本身也属于旧值并集，该搜索仍然允许它出现。[第四档分片](four-new.json)

每个子问题只提供官方初值。新增的指定目标也必须通过运算取得。搜索保留此前生成的全部数，在每一步生成所有已可达目标，然后枚举下一条合法运算的非目标结果。最后只余一个辅助数时，如果某个目标即便把所有目标当成操作数也还没有生成方法，该辅助数必须和已选辅助值、目标、初值或自身配对得到该目标。反解加、减、乘、整除涵盖全部候选；实际生成顺序最终仍须合法。程序也处理放宽后全部目标已有生成方法的情形，此时直接扫描当前可达的一步结果。限定的数值范围取自官方文件。[C++ 实现](bundle_exact.cpp)

## 复核

从比赛下载官方 `puzzles.csv`。在仓库根目录执行以下命令，需要 Python 3.12 以上及支持 C++17 的编译器。专用求解器穷尽前三档并复核 240 项小值域对照及 236 项官方数值对照。最后两行分别用两种引擎穷尽第四档。给 `verify.py` 添加 `--max-new 2` 可先复核计算量较小的前两档。给 `verify_four.py` 添加 `--shard 17` 可只检查第四档的一个分片，或用 `--receipts-only` 核对整档清单的覆盖和计数。

```bash
g++ -O3 -std=c++17 collaboration/puzzle-0882-diversity/bundle_exact.cpp -o diversity-proof
python -B collaboration/puzzle-0882-diversity/verify.py --puzzles data/puzzles.csv --binary ./diversity-proof --jobs 4 --audit
python -B collaboration/puzzle-0882-diversity/verify_four.py --puzzles data/puzzles.csv --jobs 4
python -B collaboration/puzzle-0882-diversity/verify_four.py --puzzles data/puzzles.csv --engine generic --jobs 4
```

小值域对照用独立广度优先搜索覆盖 87 项有解和 153 项无解。真实第 882 题的首批 203 项对照覆盖 71 项已知可行与 132 项无解。第二轮从另取的 84 个七旧值子集中挑选计算量最大的 18 个，另加 15 个可行子集；通用遍历的 33 个结果与专用求解器全部相符。另对该题值域内每个整数逐一正向运算，验证了 3,366,864 项操作数配对、1,496,384 项一步可达结果和 120 个闭包。以下命令可重做这两项交叉验证。Windows 可把可执行文件名改为 `.exe`。[小域审计](small-audit.json) · [首批官方审计](official-sample-audit.json) · [独立审计及父本溯源](independent-audit.json)

```bash
g++ -O3 -std=c++17 proofs/local/exact_helpers.cpp -o diversity-reference
g++ -O3 -std=c++17 collaboration/puzzle-0882-diversity/operations.cpp -o diversity-operations
python -B collaboration/puzzle-0882-diversity/verify.py --puzzles data/puzzles.csv --binary ./diversity-proof --reference-binary ./diversity-reference --operations-binary ./diversity-operations --jobs 4
```

## 对剩余分片的细分搜索

已返回 226/240 个细分格，其中 220 个已排除，6 个仍待判定。已完整排除 5 个额外的原分片。[本轮逐格结果](h10-open-progress.json.gz)

全部 768 个分片中，757 个直接排除，一个细分后排除。本轮继续检查其余十个，每个再分为 24 格。任一 22 条程序可与现有下界相遇，只有剩余各格全部排除才能证明现有 23 条程序最短。[第一轮逐片记录](h10-first-grid.json.gz) · [剩余坐标](../evidence/active-search-20261121.json)

使用 [hot.cpp](../../proofs/local/work/gpu/closest-36729/hot.cpp) 编译搜索程序，然后从仓库根目录运行以下命令。复用同一输出目录可以继续检验尚未完成的格。

```shell
python -B collaboration/puzzle-0882-diversity/refine_open.py --puzzles data/puzzles.csv --binary ./proof-hot --out work/h10-882 --jobs 4
```


原批次仍在运行时，使用同一输出目录并添加 `--retry-only --budget 80000000`，仅处理已有的未决格。汇总时运行 `summarize_refinement.py --puzzles data/puzzles.csv --in work/h10-882 --out h10-open-progress.json.gz`，检查坐标是否完整、来源是否一致、有没有可回放的 22 步程序。


达到搜索上限的格子可以继续拆分。第一种对第三层枚举序号取更细的余数，例如原余数为 0（模 24），就检查模 96 的 0、24、48、72。第二种按第四层的枚举序号分组，保留前三层坐标。只有一组更小分片全部判为无解，才排除它们的父分片。新程序的未分片搜索与原程序的三个对照逐项一致。运行 `build_fourth.py` 构建可选的第四层搜索，再用 `refine_fourth.py` 指定已有的未决格。汇总时可传入 `--deep` 和 `--fourth`，后者同时需要执行这些分片的 `--fourth-binary`。[第三层拆分](refine_cell.py) · [第四层拆分](refine_fourth.py) · [汇总程序](summarize_refinement.py)
