# 超过 48 个数时，回收已用完的寄存器

固定 10 道题。两条路线均从一份可运行的父程序出发。先把原算式重新排入 48 个寄存器作对照，再用相同题号种子搜索 96 轮。两组共完成 1,920 轮。20 个父程序都能重排，单独重排节省 0 条指令。[预登记题号及输入指纹](design.json) · [重排对照](compile-control.json)

| 来源 | 题号 | 父程序 | 新程序 | 使用的寄存器数 | 首次找到的轮号，从 0 起 |
| --- | --- | ---: | ---: | ---: | ---: |
| 独立 | 0541 | 55 | 54 | 24 | 28 |
| 公开辅助 | 0773 | 43 | 42 | 18 | 92 |

第 773 题有 7 个初值。若每条指令都占一个新寄存器，42 条指令需要 49 个位置。每次最后一次使用某个数后回收它的寄存器，实际只需 18 个。该题父程序的上游署名是 Ertugrul Ozer, 138,867 SOTA Verified Portfolio。[原始署名](assisted-origin.csv) · [公开辅助结果](assisted-wins.csv) · [各轮计数](assisted-wins.json)

第 541 题使用纯独立父本。重新选择算式后的 54 条程序追平当时的公开辅助上界。两条路线其余各 9 道在本次预算内均无严格缩短。[独立结果](own-wins.csv) · [各轮计数](own-wins.json)

## 复现

在仓库根目录运行。使用官方 `data/puzzles.csv`、Python 和 GNU C++17。父程序从 Git 提交提取以保持字节指纹。工作目录用于保存可执行文件及临时结果。

```powershell
python -c "from pathlib import Path; Path('work/register-check').mkdir(parents=True,exist_ok=True)"
python -c "import subprocess; from pathlib import Path; d=Path('work/register-check'); (d/'own.csv').write_bytes(subprocess.check_output(['git','show','2e04c7a:submission.csv'])); (d/'assisted.csv').write_bytes(subprocess.check_output(['git','show','2e04c7a:public-assisted/submission.csv']))"
python -B collaboration/puzzle-0711/make_sparse.py work/register-check/sparse.cpp
python -B collaboration/puzzle-0711/wide/make_large.py work/register-check/sparse.cpp work/register-check/large.cpp
g++ -O3 -static -std=c++17 work/register-check/large.cpp -o work/register-check/large.exe
python -B collaboration/register-search/compare.py own work/register-check/own.csv data/puzzles.csv work/register-check/large.exe work/register-check/own-wins.csv
python -B collaboration/register-search/compare.py assisted work/register-check/assisted.csv data/puzzles.csv work/register-check/large.exe work/register-check/assisted-wins.csv
```

原搜索使用 Windows MinGW GCC 16.2.0。使用其他标准库时，随机采样顺序可能不同。[编译配置及原始方法](../puzzle-0711/wide/README.md)

## 保留部分重新计算的指令

从提交 `aacd89c` 的独立程序中筛出第 493 题，原版用 251 条指令，包含 8 次重复计算。把部分重复计算的使用者改接到第一次产生该数的位置，在原有运算顺序上重新分配寄存器，得到 249 条。把八次重复全部折叠并搜索其他顺序的这次尝试没有得到更短的可执行程序。

在仓库根目录运行 `python -B collaboration/register-search/spill_copies.py --id scored_0493 --puzzles data/puzzles.csv --parents old.csv --output wins.csv`，其中 `old.csv` 可从上述提交中的 `submission.csv` 取得。[缩短后的程序](scored-0493.csv)
