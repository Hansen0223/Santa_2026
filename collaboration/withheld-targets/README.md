# 暂时拿掉部分目标再重建整题

从一个已有程序中移除一个目标，或移除共享中间值的两至三个目标。先优化保留下来的程序，再尝试用这份程序中的新数值通过一两步算术补回原目标，最后对整题搜索。对照组用同一对种子和轮数直接优化整题。所有路线在接受改动前都重放每一条寄存器指令。[固定的预算与选择规则](design.json) · [最初选定的 48 个案例](selection.json)

两条路线分别有 8 道开发题、16 道留出题。独立候选在开发组有 2 道共省 3 条，留出组另有 7 道共省 9 条。7 道留出题均严格优于普通搜索。公开辅助候选在同等规模的小组没有直接缩短。固定的后续范围包含 873 道符合条件且未参与这两组的独立题，48 道一批。[开发结果](development.json) · [留出结果](holdout.json) · [扩展名单](extension-selection.json.gz)

复验时，使用设计指定的 Git 历史、官方 puzzles.csv 和本项目根目录。将本目录里的 selection.json、development.json.gz 与 holdout.json.gz 放在临时目录，运行 compare.py，带上 --puzzles、--out、--phase development 或 holdout，并加 --replay-only。从头搜索时使用 collaboration/reactive-tabu/build.py 的 original 引擎。

## 873 道扩展题的结果

19 批全部完成。按题选取最短结果，132 道共省 194 条。直接优化整题共省 90 条，单独移除一个目标共省 116 条，同时移除多个目标共省 102 条。73 道题的重建结果严格短于直接优化，逐题取短后额外省 104 条。独立候选由 140,663 降至 140,469。[逐题改进与每批校验值](extension/results.json)

归档包含三种方案的逐题长度、程序校验值及所有改进程序。要复核任意一批，将本目录的 `extension-selection.json.gz` 和 [extension](extension/) 下对应的 `block-NN.json.gz` 复制到同一个临时目录。从仓库根目录运行以下命令，替换数据和临时目录路径，批次编号为 0 到 18。

```shell
python -B collaboration/withheld-targets/compare.py --puzzles data/puzzles.csv --out work/replay --phase extension --block 0 --replay-only
```

## 保留结尾，重建共用部分

对 48 道题同时保留所有目标的最后三层算式，或者保留每个目标独用的整条分支。把它们需要的中间数作为一组新目标，求出更短的前半段，再接回结尾。两条路线使用同一组题。[题号和预算](terminal-shell-design.json) · [搜索程序](terminal_shell.py)

第一批 48 道题的独立解共省 4 条。第 120、345 题各省 1 条，第 670 题从 189 条缩到 187 条。三道题都能由保留目标独用分支的方法缩短，公开辅助路线未缩短。用同一方法另取接下来的 96 道独立题。[首批结果](terminal-shell-results.json.gz) · [扩展题号](terminal-shell-next.json)

追加的 96 道独立题中，第 204、314 题各省 1 条。两批 144 道独立题共省 6 条，结束本次扩展。[96 道结果](terminal-shell-next-results.json.gz)
