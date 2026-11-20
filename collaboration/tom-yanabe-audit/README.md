# 导入 TomYanabe 候选：122 题、省 173 条、总计 133,890

## 来源

`TomYanabe/santa2026` 的 `submissions/best.csv`，HEAD 为提交 `b6a746676a26a6af9b1eba7396f3069bf81f3a9b`（"Merge pull request #3 … 自前の値DAG LNSエンジン v0: 135,453"，2026-11-20T13:24:29Z）。文件包含 1,000 题、`id,program` 两列，2,185,209 字节。

该候选整体为 134,926 条，比本仓库的公开辅助候选更长，但逐题比较后并非全面落后：122 题的单个程序更短。

## 结果

| 项 | 数值 |
| --- | --- |
| 导入前（`public-assisted/submission.csv`） | 134,063 |
| 导入后（本目录 `submission.csv`） | **133,890** |
| 节省 | **173 条 / 122 题** |
| 逐题最大单笔节省 | 第 0220 题 113 → 107 条（−6） |
| 序列化后 sha256 | `b74282728cad92c27ab39af97f0481e4f0b27427373d10647f14e55ec469cc0a` |

合并规则是逐题取较短，不做任何其他改动。外部候选 1,000 行先逐行通过 `elf.replay` 才参与比较，0 行被拒；合并结果写出后重新读盘再次完整回放，得分 133,890 与写出前一致。

节省最多的十题：

| 题号 | 原 | 导入 | 省 |
| --- | ---: | ---: | ---: |
| 0220 | 113 | 107 | 6 |
| 0603 | 120 | 115 | 5 |
| 0008 | 109 | 106 | 3 |
| 0144 | 116 | 113 | 3 |
| 0169 | 101 | 98 | 3 |
| 0195 | 125 | 122 | 3 |
| 0431 | 83 | 80 | 3 |
| 0534 | 108 | 105 | 3 |
| 0649 | 118 | 115 | 3 |
| 0895 | 122 | 119 | 3 |

逐题明细见 [wins.csv](wins.csv)，列为 `id,incumbent,imported,saved`。

## 许可状态：未决，不可直接用于提交

`TomYanabe/santa2026` **没有 LICENSE 或 NOTICE 文件**，仓库元数据的 `license` 字段为空。程序的上游来源也没有声明。因此这 122 条不能直接进入 Kaggle 提交：赛题要求公开代码的使用条件与署名，而这里既没有可援引的许可证，也没有逐题作者链。

处理建议（三选一）：

1. 联系仓库作者，取得书面许可并在本目录记录其条款；
2. 确认这些行的上游是已有的 Apache-2.0 公开池（Asterios 或 GoodPJW 等），按上游逐题署名；
3. 仅把本目录当作候选存档，不并入 `public-assisted/submission.csv`。

在此之前，`public-assisted/origins.csv` 与 `NOTICE.md` 未做任何改动，避免产生无法自圆其说的署名记录。

## 复现

```powershell
curl -L -o best.csv https://raw.githubusercontent.com/TomYanabe/santa2026/b6a746676a26a6af9b1eba7396f3069bf81f3a9b/submissions/best.csv
python -B elf.py data/puzzles.csv best.csv
python -B elf.py data/puzzles.csv collaboration/tom-yanabe-audit/submission.csv
```

第一条命令对导入前的候选，输出总分 134,926；第二条对本目录合并结果，输出 133,890。

## 附带结论

以这份更短的表为新起点，用本仓库自带的虚寄存器规划器对变动过的 122 题各跑一轮 `--leaves 120 --width 7 --joins 13 --scan 1`（2 进程，237.7 秒，16,689 个原始步）：0 题再缩短。说明这批新程序在同等预算下已无位移空间，下一步需要更深预算或不同父本。

同一轮复核里另做了三项检查，均无严格改进：全库 84 份 `id,program` 候选表逐题取最短仍为 133,890 之前的 134,063；四份完整提交之间逐题取最短无增益；对 1,000 题做死代码与重复计算清理（每步以 `replay` 判定）0 题缩短。这三项说明既有合并已经收口，本次 173 条的增量完全来自外部仓库。
