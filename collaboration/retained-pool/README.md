# 保留初始父本的程序搜索

E-Max AI（RoyalAceCat）在第 41、42 版公开笔记本中报告了一种程序池淘汰规则。搜索保存最初的父本，只在后来生成的程序中淘汰候选。另一种规则优先从最早的五个可淘汰候选中抽取。这里使用 wang Jakie 第 5 版 Apache 2.0 算术图搜索引擎独立实现两种规则，沿用公开实验的题号、随机种子和 900 轮预算。[E-Max AI 第 41 版](https://www.kaggle.com/code/royalacecat/santa-2026-public-frontier-score-134-311?scriptVersionId=371829955) · [第 42 版](https://www.kaggle.com/code/royalacecat/santa-2026-public-frontier-score-134-305?scriptVersionId=371833506) · [wang Jakie 的引擎](https://www.kaggle.com/code/wangjakie/santa-2026-arithmetic-recipe-pool-and-milp?scriptVersionId=371736767)

五题共省五条指令。第 0740、0871、0305、0955 题的输出与原作者对应版本逐条相同。第 0079 题省去一个无法核实来源的历史父本，在其余父本上跑出了另一条同为 132 步的程序。这五题由发布者在观察结果后选出。

在仓库根目录运行下列命令可复验五题。需要 Python 3.12 或更高版本、Git、C++17 编译器，以及参赛者自行取得的官方题目文件。可用 `--id scored_0079` 选择单题。编译器未在 PATH 中时，用 `--compiler` 指定可执行文件。

```text
python -B collaboration/retained-pool/replay.py --repo . --puzzles data/puzzles.csv
```

`cases.json.gz` 保存每个实际使用的父程序、Asterios 发布版本、原始逐题署名、输入输出指纹、种子、轮数和被排除的父本。复验从固定 Git 提交取得引擎源码，在临时目录编译，使用官方题面执行每个父程序与输出，再核对指令数和输出指纹。所有父程序都来自有逐题署名的 Asterios 公开数据集。

第 43 版在第 716 题的 117 条旧程序上，使用可归属的三个父本重新生成了 116 条程序。Asterios 第 123 版也在同题取得相同长度，这一条只计一次。[重建记录](v43/audit.json) · [输入和随机种子](v43/cases.json.gz)


## 以等长或邻近的旧解作为首个程序

从 E-Max AI 132638 版的公开输入中，按算式差异及长度差选择 128 道组合题。仅对换团队候选与公开备选的先后，其余父本、种子和 800 轮预算一致，两组均未缩短。[逐题结果](neutral-lead-results.json.gz)
