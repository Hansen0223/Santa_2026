# 合并 Pardheev 的公开程序

Pardheev 的完整结果为 132,997 条。将这份程序与本仓库 `8038039` 上的 133,655 条公开辅助候选逐题比较，419 道采用 Pardheev 的版本，其余 581 道采用仓库版本，合计 **132,841 条**。同长度时保留仓库程序。程序写出时按官方题目规则检查全部 1,000 道。[逐题差额与文件校验值](assembly.json)

发布者说明该数据可直接用于参赛或作为继续搜索的起点。Pardheev 在 436 道题上使用自己的程序，其他程序来自 royalacecat 汇总的公开成果，包括 Asterios、GoodPJW 等作者。发布页将使用条款标为 “Other (specified in description)”。从作者页面下载第 1 版 ZIP，保留原样；下面的命令会在本地生成可提交的 CSV。[Pardheev 的固定版本](https://www.kaggle.com/datasets/pardheev/santa-2026-elf-calculator-132997/versions/1) · [仓库程序的上游贡献者](../NOTICE.md)

在仓库根目录运行，替换比赛数据和压缩包的路径。输出文件为 `combined/submission.csv`。

```sh
python -B public-assisted/pardheev/combine.py --puzzles data/puzzles.csv --archive /path/to/pardheev-v1.zip --out combined
```

另取 80 道算式差异较大的题继续搜索。将发布程序、仓库公开程序、独立程序一同作为起点，各题运行 700 轮。[题号与预算](search-pilot-design.json) · [搜索程序](search.py)