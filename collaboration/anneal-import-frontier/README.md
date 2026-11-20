# 在新父本上跑 Wang 退火 · 133,890 → 133,883

仓库里的退火实验此前都以上一代表为父本（134,430、134,500、141,435 等）。本目录把
`collaboration/tom-yanabe-audit/submission.csv`（PR #1 导入后的 **133,890** 条）作为唯一输入，
用仓库内原封不动的 Wang Jakie 算法（`generative/wang/anneal.cpp`，Apache-2.0，
署名与许可见 `generative/wang/NOTICE.md`）重新跑一遍逐题退火，再把每一轮胜出的程序
逐题取短合并。

## 输入与引擎

| 项 | 值 |
| --- | --- |
| 父本 | `collaboration/tom-yanabe-audit/submission.csv`，1,000 题 **133,890** 条 |
| 引擎 | `generative/wang/anneal.cpp`（原始实现）、`anneal_diverse.cpp`、`incremental.cpp` |
| 适配 | `generative/wang/replay_search.py`（输入适配 + 双解释器回放） |
| 编译 | `g++ -O3 -std=c++20 -static` |
| 题面 | 官方 `data/puzzles.csv`，sha256 `b0c70d84…500428` |

等长输出保留输入程序，所以任何一轮都不会让某题变长；合并只取逐题更短者。

## 跑过的配置

| 轮次文件 | 模式 | 轮数 | 种子偏移 | 结果 |
| --- | --- | ---: | ---: | --- |
| `anneal35.csv` | anneal（单父本） | 35 | 737049 + 题号 | 133,886 |
| `anneal200.csv` | anneal（单父本） | 200 | 737049 + 题号 | 133,884 |
| `annealB.csv` | anneal（单父本） | 200 | 1 + 题号 | 133,884（无新行） |
| `annealC.csv` | anneal_diverse | 120 | 737049 + 题号 | 133,883 |
| `annealD.csv` | incremental（带缓存） | 150 | 737049 + 题号 | 133,883（无新行） |

每轮 1,000 题在 2 核上耗时 2.5–10 分钟。第二轮（种子偏移 1）与增量模式都没有找到新行，
说明这一父本上的退火收益主要来自前 200 轮。

## 逐题结果 · 5 题共省 7 条

| 题号 | 原 | 新 | 省 | 来自 |
| --- | ---: | ---: | ---: | --- |
| scored_0310 | 111 | 108 | 3 | anneal200（200 轮） |
| scored_0016 | 123 | 122 | 1 | anneal35（35 轮） |
| scored_0512 | 124 | 123 | 1 | anneal35 |
| scored_0747 | 155 | 154 | 1 | anneal200 |
| scored_0803 | 130 | 129 | 1 | annealC（多样化） |

整表 133,890 → **133,883**（−7）。`submission.csv` 是本目录的合并结果，`wins.csv` 是逐题胜表。

## 校验

- 合并后的 1,000 行逐行用 `elf.replay` 重放，全部合法（目标在过程中至少出现一次、每步结果落在 1..limit）。
- 每轮输出本身也由 `replay_search.py` 用两份解释器回放后才落盘。
- 读盘后再回放一次（不依赖任何内存中的状态）：
  `python -B elf.py data/puzzles.csv collaboration/anneal-import-frontier/submission.csv`

## 复现

```bash
g++ -O3 -std=c++20 -static generative/wang/anneal.cpp -o /tmp/anneal
g++ -O3 -std=c++20 -static generative/wang/anneal_diverse.cpp -o /tmp/anneal_diverse
g++ -O3 -std=c++20 -static generative/wang/incremental.cpp -o /tmp/incremental
python -B generative/wang/replay_search.py data/puzzles.csv \
    collaboration/tom-yanabe-audit/submission.csv /tmp/anneal35.csv \
    --binary-dir /tmp --rounds 35 --jobs 2
```

## 许可与可用性

本目录的输出是从 `TomYanabe/santa2026` 的 `submissions/best.csv` 派生出来的，该仓库没有
LICENSE / NOTICE，元数据里的 license 为空。因此和 PR #1 一样，这里只作为候选，
**在授权问题解决之前不要直接用于 Kaggle 提交**；`public-assisted/origins.csv` 与
`NOTICE.md` 也未被改动。
