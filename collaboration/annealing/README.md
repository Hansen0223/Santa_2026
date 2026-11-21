# 按算式图做模拟退火

在冻结的独立 141,435 条方案上，以各题的独立程序为唯一输入运行 Wang Jakie 的算法，1,000 道题中有 150 道缩短，总计省 194 条。完整回放得到 141,241 条。原始程序与修改源码均保留 Apache 2.0 许可和来源说明。[独立搜索回执](independent35.json) · [源码、许可与复现入口](../../generative/wang/NOTICE.md)

独立起点来自提交 2488949 的 submission.csv，把三个新行替入后按官方题号写出。这三个程序从本地独立父程序和官方初值生成。[三个替换行](three-before.csv)

在公开辅助的试验里，以 Asterios 第 113 版为起点，选用有记录的旧算式作为额外输入。确认来源并复跑的 7 道题共省 8 条，该试验单独得到 134,500 条。主提交还逐题比较了其他改进，重叠的节省只计一次。[各题输入版本与种子](assisted-recipes.csv) · [公开输入署名](assisted-origins.csv) · [结果](assisted-seven.csv) · [双重回放](assisted135.json)

在第二轮中，使用带缓存的退火继续优化独立生成的算式，并与仓库的独立候选逐题择短。154 题合计省 214 条，整表降至 141,026 条。以第 113 版为单独对照的公开辅助试验在 24 题省 30 条，得到 134,478 条；与此前的改进和新的独立候选逐题合并后，整表为 134,456 条。[独立重放](independent95.json) · [独立输入来源](independent95-origins.csv) · [公开重放](assisted160.json) · [输入程序与种子](assisted160-recipes.csv) · [逐题来源](assisted160-origins.csv)

对 47 道近期出现改进的题和 47 道长度、初值数量、目标数量相近的对照题使用同一计算预算。前组四题各省一条，对照组无改进。每个入选程序均从实际父本重新运行，并按原署名保存。另测同时重建多个目标，在独立 96 题省 1 条，公开辅助 180 题没有缩短，已停止扩展。[四项改进回执](active-pairs.json) · [重跑种子和父程序](active-pairs-recipes.csv) · [父程序署名](active-pairs-origins.csv) · [独立多目标试验](anneal-region75-own.json) · [公开多目标试验](anneal-region120-pub.json)

使用历史图结构预测下一题能否缩短。先去掉 49 道已知改善题，再冻结预测靠前的 100 题和 100 道长度匹配的对照。相同预算下两组各省 2 条和 1 条；这三项改进都通过完整回放。这次前瞻差距只有一条。[固定分组](prospective-100-pairs.json) · [早期交叉验证](rank-validation.json) · [前瞻结果](prospective-replay.json) · [复跑输入](prospective-recipes.csv)

在 256 题上比较只用一种独立父程序与增加 Rudolph、konbu 的独立生成程序。用于生成这些父程序的输入只含官方初值及目标。单父本合计省 26 条，多父本合计省 21 条，逐题选优共省 35 条。与仓库当时的独立上界逐题合并，140,914 降到 140,879 条。[同预算结果与基线指纹](own-portfolio160.json) · [逐题来源](own-portfolio160-origins.csv)

继续检验其余独立程序，54 题合计省 65 条。冻结候选由 140,879 降至 140,814 条，两份整数解释器均已复核。编排额外父程序时，Rudolph 数据中只使用直接由官方初值生成的 250 行，konbu 数据中只使用对应的 174 行。所有入选程序保留输入算式、种子与作者。[独立父程序筛选](independent-donors.json) · [改进结果](independent-wide.json) · [搜索输入和种子](independent-wide-recipes.csv) · [署名](independent-wide-origins.csv)

两个互不重叠的批次（256 题及余下的 744 题）现已覆盖全部 1,000 题。与冻结的 140,946 条输入相比，总计 87 题省 106 条。最后一题 0686 将主线从 140,814 降到 140,813。[最后一题回放](independent1000.json) · [父本与种子](independent1000-final-recipe.csv)


## 两种指令偏好

独立与组合路线各试 96 题。两个程序群分别偏向使用更多或更少的乘除，在最多落后当前最短 4 条时保留备选，再将算式重组。对照保持相同的轮数和程序群数量。两组均未缩短，停止扩大。[逐题结果](opcode-mix-results.json.gz)
