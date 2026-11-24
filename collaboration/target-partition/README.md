# 分开求解两组目标再合并

每题从官方初值出发。先把目标平分，让两个子程序分别优化，再合并算式并重排到 48 个寄存器，最后优化一次整题。随机分组和从 160 种分组里选择共享中间值最少的分组，各给两个子题和合并后的整题 100 轮。对照组将同样的 300 轮分作三次整题优化。每题使用同一组三个固定种子，底层搜索来自 Wang Jakie 的增量算式优化器。[算法来源](../../generative/wang/NOTICE.md) · [冻结方案](design.json)

独立解与公开辅助解各 12 道开发、24 道留出，开发组均无缩短。独立留出组中，整题对照省 5 条，两种分组各省 4 条，两种分组均未独自赢得一道题。公开辅助组均无缩短。四个完整候选各用两个解释器重放全部 1,000 题，独立结果由 140,727 降至 140,722。[开发结果](development.json) · [留出结果](holdout.json) · [四份采用的程序](holdout-independent.csv)

复核时先使用 collaboration/reactive-tabu/build.py 构建 original，再运行 compare.py，指定 --repo、--puzzles、--exe、--design、--group 和 --out。把 development.json.gz 和 holdout.json.gz 复制到输出目录并加 --replay-only，可以仅用官方题目、冻结 Git 版本和两套解释器检查已保存的结果。

## 从其他程序借用目标分组

收集其他程序里共用同一中间值的 2 至 5 个目标，只保留当前程序尚未出现的分组。让 GoodPJW 的局部搜索优先尝试其中最多六组。对照从同一程序、同一种子和相同时间预算开始，用原有分组顺序搜索。每一路每题 6 秒，墙钟截断可能使重跑的搜索次数不同。

独立组共 591 题，逐题取短后 39 题省 43 条，其中 5 题的借用分组方案严格优于对照。组合组 100 题，逐题共省 0 条。[逐题设置、来源和结果](donor-mask-results.json.gz) · [独立改进](donor-mask-independent-wins.csv)

从 E-Max AI 固定的 132,608 重放数据集下载原始 ZIP。该版本使用 GoodPJW 的 Apache 2.0 搜索器，并在首次严格缩短时停止。运行 `python -B donor_masks.py build-source ARCHIVE.zip donor-masks.cpp` 后用 C++17 编译，再运行 `python -B donor_masks.py search --puzzles data/puzzles.csv --parent PARENT.csv --donors DONOR.csv --exe SOLVER --out OUTPUT`。[本地修改](donor_masks.py) · [固定原始归档与上游署名](https://www.kaggle.com/datasets/royalacecat/santa-2026-replay-132608-lean/versions/1)

## 集中搜索仓库已经领先的题

用 E-Max AI 的 132,608 条输出作参照。在组合候选由仓库提供且比该参照严格更短的全部 15 道题上，选取合格独立父本及公开辅助父本，同一份物理程序只计算一次。每个起点使用两个随机种子，分别允许或关闭中间值搜索，每次最多 16 秒。共 20 个起点。独立组内共省 1 条，辅助组内共省 1 条。第 893 题 121 → 120。[逐题记录和来源](local-leads-results.json.gz) · [求解器](local_leads.py)

## 从相近长度的不同程序继续搜索

独立程序与组合程序长度相差至多两条、辅助值差异至少 20% 的 158 道题，分别从两个起点直接搜索，再交叉搜索。第 366 题的独立程序 116 → 115，组合解没有缩短。搜索器来自 GoodPJW、E-Max AI 及 Wang Jakie。[逐题结果](near-tie-results.json.gz) · [独立改进](near-tie-own-wins.csv)

另对两个组合版本之间有变化的 10 道题，从新旧组合解及独立解搜索，收集等长搜索过程及局部备选算式，按每题去重后合计 31,722 种。比较直接搜索与重新组合，逐题共省 0 条。[逐题记录](harvest-changes-results.json.gz) · [算式组合](harvest_changes.py)
