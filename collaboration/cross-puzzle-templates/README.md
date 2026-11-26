# 跨初始值迁移的算术模板

40 道官方练习题上，从初始值重新生成合法程序，得到 900 种依赖 2–4 个不同初始值、含 5–9 步的算术模板。**没有一个完整模板在两道训练题重复出现。** 训练使用自行生成的程序，官方文件只提供练习输入和题型等元数据。此后按模板内较短的操作依赖在其他练习题中的出现频率排序，对照实测前已登记这一调整。[训练与留出题号及各组 SHA-256](design.json)

每臂有 446 个完整模板，指令数及初值占位数的分布相同。第一组保留高频局部依赖，第二组保留低频局部依赖，第三组打乱第一组的操作符位置，保留操作符数量及数据依赖。将占位符逐一绑定到新题不同初始值，严格检查正整数、精确整除和数值上限。各臂都经过同样的旧值配方重选与 48 寄存器编译。打乱组相当一部分绑定未满足正整数或精确除法要求。

| 数据和绑定方式 | 每臂尝试数 | 高频 / 低频 / 打乱的合法绑定数 | 仅旧值的步数 | 三组完整程序步数 |
| --- | ---: | ---: | ---: | ---: |
| 24 道独立留出练习题，原始初值 | 330,642 | 247,067 / 135,266 / 79,301 | 4,526 | 4,525 / 4,525 / 4,526 |
| 8 道计分开发题，原始初值 | 61,842 | 50,263 / 27,865 / 16,472 | 1,325 | 1,325 / 1,325 / 1,325 |
| 4 道计分留出题，原始初值 | 122,484 | 99,480 / 52,142 / 32,913 | 698 | 698 / 698 / 698 |
| 同 8 道开发题，额外允许一个一步初值 | 3,894,540 | 2,958,207 / 1,551,539 / 1,009,319 | 1,325 | 1,325 / 1,325 / 1,325 |

高频和低频模板各在相同的一道练习题省一步。计分题相对冻结独立程序均未改善。额外初值必须由官方初值实际算出，这一步计入程序。原生生成器完整枚举并输出候选数量后，才接收用于筛选读回值的查询。由于八道开发题没有改善，额外初值方案停止扩大。[各组统计](summary.json) · [逐题原始判断](runs.json.gz)

**第 0199 题**确实出现了跨题迁移。高频组的三个程序分别源自练习题 0133、0124、0077。绑定新初值后，4、10、8 条指令即可产生计分题目标表中索引 0、2、3 的三个值，索引从零起算。可是这三个目标在原有 101 条程序中，各自只占一条独享运算，其余步骤还要服务其他目标。分别用迁移模板替换后，算术图变为 104、110、108 条。这也解释了数值命中为何没有带来整题收益。[独立可重放的三个程序](example0199.json)

训练程序使用 Alex Chilton 的 Rudolph 源码及项目既有的固定配置，作用限于从练习题官方初值生成训练轨迹。计分题中生成候选只依赖题目初始值、数值上限和训练好的符号库。冻结独立程序在最后用于筛选、组合与比较。9 组独立枚举校验覆盖 3,204 次绑定，其中 1,512 次合法，1,247 个去重输出与另写的 Python 解释器逐组一致。[枚举校验](parity.json) · [Rudolph 来源](https://www.kaggle.com/code/alexchilton/rudolph-the-red-nosed-register-allocator)

在仓库中的本目录执行下列示例，将路径换成本地实际位置。无需重新训练就能复现 0199 的三个完整程序。完整实验需要项目的算术图工具、OR-Tools 与 C++17 编译器。

```sh
g++ -O3 -std=c++17 instantiate.cpp -o instantiate
python -B restore.py scratch --git-root /path/to/repository
python -B example.py /path/to/puzzles.csv scratch ./instantiate scratch/parent.csv scratch/repeated-example.json
python -B parity.py scratch ./instantiate scratch/parity.json
python -B evaluate.py /path/to/puzzles.csv scratch ./instantiate scratch/dev --split pilot --parent scratch/parent.csv
python -B evaluate.py /path/to/puzzles.csv scratch ./instantiate scratch/held --split holdout --parent scratch/parent.csv
python -B evaluate.py /path/to/puzzles.csv scratch ./instantiate scratch/dev-extended --split pilot --parent scratch/parent.csv --lift
```

要从头重建练习轨迹，再编译仓库的 `generative/rudolph.cpp`。运行 `train.py /path/to/practice_puzzles.csv ./rudolph output-library` 后，`evaluate.py /path/to/practice_puzzles.csv output-library ./instantiate output-practice --split practice --generator ./rudolph` 会重放 24 道练习留出题。

## 借用另一道题已经用过的数和算式

为每题选出与它共享少见中间数的其他题，在接收题的初值和原有算式上重建借来的算式。独立组 70 题、组合组 78 题，分别产生 1,291 和 1,102 个候选片段。第 821 题的独立程序由 103 条缩到 102 条，直接搜索仍为 103 条。组合组未缩短。父程序取自 `37cfdb7` 的独立提交和该版本重建的组合提交。[求解器](foreign_circuits.py) · [来源、设置和逐题结果](foreign-circuit-results.json.gz) · [第 821 题程序](foreign-circuit-independent-wins.csv)

## 对其他题的加减片段作缩放或平移

用 440 道题的两步加减片段建库，只在其余题上测试。缩放组在组合 130 道、独立 145 道中分别有 110、136 道获得可重搜的起点。平移组在组合 104 道、独立 115 道中分别有 93、111 道。四组逐题取短后，组合解省 0 步，独立解省 3 步。[逐题结果](scaled-fragments-results.json.gz) · [实现](scaled_fragments.py)
第 432、613 题只在缩放组得到改进，第 462 题的改进来自整题对照。

## 缩放含乘除的两步算式

缩放部分或全部输入，根据加减乘除确定中间值和输出的缩放幅度。保留小常数的版本也一起测试。三道构造例分别检查连乘、整除和固定常数。新版公开归档切换前开始的试验覆盖 72 道组合题、88 道独立题，均未缩短各自的父本。[逐题结果](homogeneous-fragments-results.json.gz)
