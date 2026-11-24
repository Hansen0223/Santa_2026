# 多份算式之间能否共用中间值

按公开辅助父程序的长度将 1,000 题分为八层，每层确定 4 道开发题、8 道留出题。独立与公开辅助各自比较同一批 96 道题。两种搜索在开发、留出和两种来源上均节省 0 条，已停止扩展。[固定题号和输入哈希](design.json) · [各组计数](controls.json)

第一种搜索从目标反推各选项都需要的数值，每组选项最多展开 800 个节点。在 64 道留出题上，独立线上 287 组选项穷尽 165 组，公开辅助线上 117 组穷尽 71 组。第二种搜索移除一或两个中间值的计算，再用多个父本中的现成数值重建。每题最多尝试 32 种移除方式。独立和辅助留出组各检查 1,817 和 1,816 种，没有找到更短的局部重建。结论仅适用于这些输入、候选算式和搜索预算。

运行 `python -B test_small.py` 比较 128 个小算式库的穷举结果并复核一个 3 条缩到 2 条的实例。复验正式题时，从本目录运行以下命令，可在末尾加 `--id scored_XXXX` 仅复验分组中的一道题。

```sh
python -B benchmark.py --puzzles ../../data/puzzles.csv --lane own --mode union --part pilot
python -B benchmark.py --puzzles ../../data/puzzles.csv --lane assisted --mode rooted --part holdout
```

[冻结的父程序和逐行作者](parents.json.gz) 仅包含这 96 题。独立输入由官方初值及目标生成；公开试验包含仓库历史候选及 Asterios 版本，每个输入保留上游署名。公开来源沿用原许可证。[各原始版本和来源](../../public-assisted/NOTICE.md) · [逐题计算记录](rows.json.gz)

## 按完整依赖子图选父本

从冻结的 133,798 条候选出发，选取至少三个不同算式图且每个程序至多长 12 条的题。750 道符合条件，按固定顺序抽取 18 道开发题和 36 道留出题。每个目标可选一个父本来提供整段算式，第二组另外允许在最多 14 个各父本共有的中间值处改换来源。模型按使用的不同整数计费，并限制依赖次序。可行解重新分配寄存器并按题面回放。两组各 54 题均在各自候选子图范围内求到最小整数数目，均未缩短整题。人工构造的对照例由 3 条缩为 2 条。此分支结束。[模型](cone_assignment.py) · [固定版本、题号、预算与逐题记录](cone-assignment-results.json.gz)

## 在协作分支的新程序上重新搜索

25 道题分别使用 Hiyohane 的独立程序、当前主线及不同历史版本的程序，先联合挑选算式，再用 Wang Jakie 的多父本搜索 680 轮。单独挑选算式未缩短完整程序。后续搜索在独立路线上缩短 21 道共 129 条，在公开辅助路线上缩短 8 道共 39 条。两条路线逐题择短后，最好候选共省 64 条。第 644 题只在独立方案上缩短。[搜索程序](contributor_circuits.py) · [各题输入与结果](contributor-results.json.gz)

## 从其他独立旧程序重新起步

17 份独立搜索历史中，有 890 道题具备长度相近且算式不同的候选。先取备选质量最高的 24 道，另按题号抽取 24 道。每个程序分别从当前最短解和不同结构的旧解开始，两路各 360 轮；独立候选只缩短 1 条，公开辅助候选没有缩短。把旧解放在首位未取得额外改进，本轮没有扩大到其余题目。[逐题结果](alternate-pilot-results.json.gz) · [48 道的历史候选](alternate-pilot-donors.json.gz) · [程序](alternate_starts.py)

第二轮重新搜索同一批题，11 道独立题共省 18 条。逐题比较两条路线后，最好候选在 10 道共省 17 条，其中第 190 和 996 题各省 3 条。[每道题及其父程序](contributor-second-results.json.gz)

从 25 份协作初稿各生成 4 份独立备选，再按长度和算式的差异选出第二代的父程序。第一代在 8 道题各省 1 条，第二代又省 5 条，两代合计缩短 11 道、13 条。4 道改进也缩短了 132,841 条组合。[生成及选择](sibling_population.py) · [逐题结果和父程序指纹](sibling-results.json.gz)


## 引入两个共用新中间值的算式片段

在不同来源的程序中选两个共同出现的数，比较两种程序对它们的计算方式。若两个替换片段都用到了同一个主程序没有的中间值，将两处同时替换，同时保留单处替换作为备选。将合法、长度最多比原解多 5 条的候选交给搜索器作起点。对照搜索用同一随机种子和相同轮数，直接从原父本出发。

独立组从 `00f9cd0` 固定的父本及四个仅含独立程序的历史版本出发，两批 370 题总计缩短 22 条，其中 5 题的替换组胜于直接搜索。合并时协作者已更新部分同题，仍有 15 题给主线节省 18 条。公开组合两批 296 题只在第 268 题省 1 条，来自对照搜索。上游搜索器为 Wang Jakie 和 E-Max AI 发布的 `anneal_crossover14.cpp`，每题以 716052 加数字题号为种子。完整分组、哈希、参数与输出见[实验记录](paired-splice-results.json.gz)和[搜索程序](paired_splices.py)。

## 通过最小割混合两个父程序

选两份共享部分目标或中间值的程序。对每个选为边界的数，给它指定左或右父程序。一个父程序的私有中间值被多个边界使用时只计一次。最小割按这个代价选择父程序。两种顺序分别约束边界间的依赖，拼接后再删除多余计算和分配寄存器。只对产生新算式组合的起点继续搜索。最小割的最优性限于固定边界、既定顺序和两份给定算式。

独立组覆盖 614 道有合格历史父程序的题，逐题与直接搜索取短，9 道共省 10 条，其中 3 道的混合起点胜过对照。组合组 160 道未缩短。[逐题数据与来源](cut-parents-results.json.gz) · [独立改进](cut-parents-independent-wins.csv) · [实现](cut_parents.py)

## 用两份程序重建共同出口

选取两个程序都计算、但求法不同的一组数作为出口。从原程序中移除专门为这组出口执行的指令，以不依赖出口且仍能从初值抵达的数作为输入。在这个较小的题内从两份程序出发重新搜索，再拼回所有正式目标。独立组 106 道，由完整程序直接搜索得到 3 道改进，共 3 条。组合组 132 道未缩短。[逐题数据](shared-outputs-results.json.gz) · [独立改进](shared-outputs-independent-wins.csv) · [实现](shared_outputs.py)

两组实验均由 `cut_parents.py` 运行。指定 `--method cut` 或 `--method shared-outputs`，再传入 `--puzzles`、`--parent`、`--donors`、`--engine` 和 `--out`。每份结果中的输入记录提供 Git 版本或 Kaggle 固定归档地址，程序按实际来源区分。[Wang 求解引擎](../../generative/wang/NOTICE.md)

## 反向保留多个未完成目标集合

从所有目标向前驱倒推。在保留一份原始解的值顺序时，把其他解能提前算出的中间值插入其中。每处理一个值，按尚需生成的数集合合并状态，保留已经付出步数更少的路径。不同替代式共同需要的祖先给出剩余步数下界。首轮保留单条路径作对照，再保留 32 条路径。所有计分程序重新分配寄存器并按官方题目回放。倒推思路参考 Sargis Khachatryan 的公开笔记本。[参考笔记本的固定版本](https://www.kaggle.com/code/avazaku/elf-calc-backward-frontier-rewrite?scriptVersionId=372206360) · [本地实现](backward_beam.py)

独立组 614 道题共省 2 条，第 525 题 117 → 116，第 641 题 118 → 117，第 641 题只有保留多条路径才缩短。组合组 968 道题共省 0 条。[逐题记录及父本](backward-beam-results.json.gz) · [独立改进](backward-beam-own-wins.csv)

独立历史均取自记录所列 Git 版本的根目录提交；组合组同时使用两条仓库主线、旧组合解、Asterios Panoras 第 196 版、GoodPJW 第 43 版与 Alex Chilton 第 126 版。外部表取原件的 id 和 program 两列，保留原顺序及程序文本，再传入 --donors。[Asterios](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/196) · [GoodPJW](https://www.kaggle.com/datasets/goodpjw2008/santa-2026-dag-lns-programs/versions/43) · [Alex Chilton](https://www.kaggle.com/datasets/alexchilton/santa-2026-rudolph-programs/versions/126)

## 用其他程序的值生成新算式

在独立 607 道题、组合 230 道题上，对比合并原有算式，以及用相同的值枚举额外算式再求解。独立组 5 道共省 6 条，均由新增算式带来。组合组未缩短。[逐题结果和父本](full-union-results.json.gz) · [采用的独立程序](full-union-independent-wins.csv) · [求解器](full_union.py)
