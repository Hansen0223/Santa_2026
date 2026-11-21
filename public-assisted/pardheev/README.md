# 合并 Pardheev 的公开程序

Pardheev 的完整结果为 132,997 条。将这份程序与本仓库 `8038039` 上的 133,655 条公开辅助候选逐题比较，419 道采用 Pardheev 的版本，其余 581 道采用仓库版本，合计 **132,841 条**。同长度时保留仓库程序。程序写出时按官方题目规则检查全部 1,000 道。[逐题差额与文件校验值](assembly.json)

发布者说明该数据可直接用于参赛或作为继续搜索的起点。Pardheev 在 436 道题上使用自己的程序，其他程序来自 royalacecat 汇总的公开成果，包括 Asterios、GoodPJW 等作者。发布页将使用条款标为 “Other (specified in description)”。从作者页面下载第 1 版 ZIP，保留原样；下面的命令会在本地生成可提交的 CSV。[Pardheev 的固定版本](https://www.kaggle.com/datasets/pardheev/santa-2026-elf-calculator-132997/versions/1) · [仓库程序的上游贡献者](../NOTICE.md)

在仓库根目录运行，替换比赛数据和压缩包的路径。输出文件为 `combined/submission.csv`。

```sh
python -B public-assisted/pardheev/combine.py --puzzles data/puzzles.csv --archive /path/to/pardheev-v1.zip --out combined
```

从 423 道算式差异较大的题中先选 80 道，将发布程序、仓库公开程序、独立程序一同作为起点，每道搜索 700 轮，完整程序均未缩短。使用的 Wang Jakie 搜索代码来自 E-Max AI 汇编的第 3 版。[题号与预算](search-pilot-design.json) · [逐题结果](search-pilot-results.json.gz) · [搜索程序](search.py) · [所用源码](https://www.kaggle.com/datasets/royalacecat/santa-2026-retained-graph-search-source/versions/3)

另外尝试了两种改写。第一种选 24 道，把一份程序的前半段接到另一份的后半段，允许用新算式补出缺少的中间数。第二种选 60 道，重新组合带正负号的和、积与整除，并将不同目标可共用的中间数合并。两组均未缩短当前候选，结束扩大。[24 道的结果](boundary-results.json.gz) · [前后段连接](boundary_join.py) · [60 道的结果](reassociation-results.json.gz) · [代数改写](reassociate.py)
