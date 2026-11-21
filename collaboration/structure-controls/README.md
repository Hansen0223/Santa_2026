# 两种多目标结构的检验

两项试验都能识别人为植入的结构。在预先指定的计分题上，第一项没有预测到遮蔽目标，第二项没有缩短独立程序。两项均停止扩大。官方练习文件给出题型、难度和下界，没有提供生成算式的轨迹。

## 用四个目标预测第五个

假设部分题中存在顺序未知的二阶递推 `z = a y + b x + c`。每题把大于 4,096 且不在初始值中的目标分三份，轮流遮蔽一份。在可见目标上枚举四个不同值和非零系数 `a,b ∈ [−3,3]`，用前三个值求常数 c，检查第四个值，再向前或向后预测一个新值。分别测试精确匹配和允许误差 16 的匹配。对照将目标做小幅随机扰动，保留量级及模 30 的余数。另行排除能由两项小整数线性组合加种子、或两项乘除得到的预测。

| 测试 | 实际遮蔽位置 | 精确拟合与预测 | 容许误差 16 后、超出上述简单关系的命中 |
| --- | ---: | ---: | ---: |
| 真实练习题 | 5,224 | 0 | 2 |
| 练习题扰动对照 | 5,224 | 0 | 0 |
| 12 道预登记计分题 | 354 | 0 | 0 |
| 计分题扰动对照 | 354 | 0 | 0 |

72 个人为植入、参数已知的例子都准确预测了至少一个遮蔽值，其中 36 例的预测也能由简单的两项关系解释。真实练习中两个容差命中均在 multiplicative 家族，只有一个预测值刚好相等。[分组统计](recurrence/summary.json)

复跑时用 C++17 编译器编译 `recurrence/predict.cpp`，将下列路径替换为实际位置。三个命令通过 `--set` 区分数据及合成对照。

```sh
g++ -O3 -std=c++17 recurrence/predict.cpp -o predict
python -B recurrence/experiment.py /path/to/practice_puzzles.csv ./predict scratch/practice --set practice
python -B recurrence/experiment.py /path/to/practice_puzzles.csv ./predict scratch/planted --set planted
python -B recurrence/experiment.py /path/to/puzzles.csv ./predict scratch/scored --set scored
```

## 允许多个大数簇共用小偏移

计分题中有 1,162 个相邻目标之间的差不超过 4,096，且较小目标大于 8,192、超过差值的 64 倍。在已有的题面分类中，553 个来自高票 shared 题。筛选至少六个此类相邻差的题，以固定哈希排序选出六道开发题和六道留出题，全程只使用冻结的独立程序测量效果。[冻结父本和题号](ruler/design.json)

直接对照允许用另一个目标加减差值得到当前目标。另两组允许把每簇平移到自己的中心，让多个簇的目标共用相同小偏移，把偏移的构造计入整张算术图。一组随机抽取中心，另一组按覆盖目标数、能否由现有值一步构造、跨目标差的可用程度选择中心，每簇最多 24 个。三组均先直接重放候选，再用相同预算进行全题联合选择和寄存器调度。

| 数据 | 直接构造 | 随机中心 | 定向中心 |
| --- | ---: | ---: | ---: |
| 8 道植入例的单题步数 | 24–27 | 23–27 | 全部 16 |
| 6 道正式开发题严格改善数 | 0 | 0 | 0 |
| 6 道正式留出题严格改善数 | 0 | 0 | 0 |

12 道正式题中，11 道在本次两个中心方案的有限候选集合内都求到了最优。另 1 道达到限额时保留了原方案。这个最优性只覆盖所列候选。值域接近确实存在，但在这批独立程序上已经难以用新的偏移复用赚回中心构造成本。[逐题候选规模、求解状态与步数](ruler/results.json)

```sh
git show a7903ac6f322fbdf0c8702a4398e4e8b46521c82:submission.csv > parent.csv
python -B ruler/planted.py scratch/ruler-positive --n 8
python -B ruler/ruler.py /path/to/puzzles.csv parent.csv scratch/ruler-development --split pilot
python -B ruler/ruler.py /path/to/puzzles.csv parent.csv scratch/ruler-holdout --split holdout
```

## 由目标附近的平方数提出乘积

在 36 道目标接近整数倍平方的题上，分别从当前独立程序和公开辅助程序出发。把不同平方根两两相乘，在乘法前后补回偏差，再按可执行程序长度取短。共形成 10,737 条交叉乘积候选路径与 4,089 条平方路径，两条路线均未缩短，因此结束此方向。[搜索](square_products.py) · [逐题数据](square-products.json.gz)

## 用重复出现的余数推测中间乘数

用 Ishan Karnick 第 5 版的程序作为参考，对 Hiyohane 贡献的 25 个独立程序寻找参考程序里没有、却至少被用过三次的中间数。在前八个候选中，7 道题命中至少一个这类数。将目标作小幅随机扰动后，2 道命中。这 25 道来自已知有改进的程序，不能用来估计所有题的命中率。[可复验对照](scale_recovery.py) · [各题排名](scale-recovery-results.json.gz)

从初值不大于 35、目标有 28–32 个的计分题中固定抽取 64 道。在独立和组合程序上，比较把目标写成另一个目标加减共同乘数的整数倍、再补余数的方案；分别构造 7,311 和 7,187 个候选片段，均未缩短。前 36 道又以保留的中间值为初值，分别用 Rudolph 从头生成八个目标，试验额外提供推测的乘数并将构造成本计回整题，两组仍无净改进。[算式候选](residue_bridges.py) · [重新生成](residue_groups.py) · [完整结果](residue-bridges-results.json.gz) · [Rudolph 来源](../../generative/NOTICE.md)
