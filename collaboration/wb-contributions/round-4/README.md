# WorkBuddy 第四批：独立线构造式搜索 + 跨线移植

基线为远端 `main` 的 `c982b16`（独立 139,766 条，公开辅助 133,639 条）。

对独立候选线运行 ultra 构造式搜索（参数同前三批），再把独立线中短于公开辅助线的程序逐题移植。独立线程序由仓库自带求解器从官方输入生成，移植不引入外部公开数据。

## 独立候选线

| 题号 | 原长度 | 新长度 |
|---|---:|---:|
| scored_0104 | 243 | 242 |
| scored_0106 | 233 | 232 |
| scored_0119 | 231 | 227 |
| scored_0240 | 114 | 113 |
| scored_0263 | 231 | 229 |
| scored_0264 | 215 | 214 |
| scored_0310 | 110 | 109 |
| scored_0321 | 294 | 293 |
| scored_0352 | 237 | 236 |
| scored_0372 | 124 | 123 |
| scored_0483 | 175 | 174 |
| scored_0488 | 157 | 156 |
| scored_0494 | 216 | 215 |
| scored_0502 | 173 | 172 |
| scored_0505 | 112 | 111 |
| scored_0527 | 222 | 221 |
| scored_0671 | 198 | 197 |
| scored_0692 | 208 | 207 |
| scored_0740 | 144 | 143 |
| scored_0795 | 189 | 187 |
| scored_0815 | 211 | 210 |
| scored_0826 | 201 | 200 |
| scored_0844 | 269 | 267 |
| scored_0850 | 186 | 185 |
| scored_0870 | 212 | 211 |
| scored_0912 | 220 | 218 |
| scored_0993 | 222 | 221 |

独立候选 **139,766 → 139,732** 条（sha256 `b79e6240c4ef26b2fe5a509d72c804d5673aee954c39883f2ffc37c68a379e74`）。

## 公开辅助候选线

| 题号 | 原长度 | 新长度 | 来源 |
|---|---:|---:|---|
| scored_0374 | 214 | 213 | ultra |
| scored_0505 | 112 | 111 | independent |
| scored_0756 | 152 | 151 | ultra |
| scored_0815 | 211 | 210 | independent |
| scored_0870 | 212 | 211 | independent |

公开辅助候选 **133,639 → 133,634** 条（sha256 `5aff5a6d5c83742ba3f28ff28e89b01a53c68f5a07c2ee2fadaf54bd6b53443a`）。

两份候选均已用 `elf.check` 逐题重放并用 `elf.py` 完整复核；`origins.csv` 与 `public-assisted/origins.csv` 的相应署名同步更新。

```bash
python -B elf.py data/puzzles.csv submission.csv
python -B elf.py data/puzzles.csv public-assisted/submission.csv
```
