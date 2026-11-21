# Atakan’s multiplier frontier on the 134311 and 140745 releases

The Atakan search shortened eight independent programs by nine instructions on the frozen aca4989 parent, taking the full independent table from **140745 to 140736**. The alternate version recovered one extra instruction. None of the 24 tested public programs improved the 134311 public table. Both final tables passed full replay under a separate interpreter.

| Search | Independent cases | Shorter rows | Instructions saved | Public cases | Public savings |
| --- | ---: | ---: | ---: | ---: | ---: |
| v15, legacy style 4 | 120 | 7 | 8 | 24 | 0 |
| v30, legacy style 4 | 120 | 7 | 8 | 24 | 0 |
| v30, temporary length increase and numeric diversity, style 13 | 120 | 8 | 9 | 24 | 0 |

The two legacy-style arms produced byte-identical winners on all seven common improved rows. Style 13 additionally shortened 0274 from 139 to 138. The full gains were 0274 (139→138), 0535 (145→144), 0573 (196→195), 0577 (133→132), 0627 (119→118), 0807 (132→130), 0827 (185→184) and 0904 (109→108). The primary experiment used each lane’s own input tape, with no imported public programs in the independent lane.

## Source identification

Atakan Aldemir’s fixed v15 run describes the original Multiplier Frontier and includes its C++ implementation, benchmark and case-by-case audit. Its original 238-row cohort uses at least 25 targets, maximum seed at most 100, and a largest target of 50–59 bits. On the author’s v14 reference the union of multiple profiles saved 88 instructions on 60 rows. As a positive check we recovered the author’s v14 physical program for 0185 and reproduced the published 148→146 result with its recorded v15 profile. [Atakan, fixed v15 notebook](https://www.kaggle.com/code/atakanaldemir/santa-2026-joint-recipes-for-large-puzzles?scriptVersionId=371328068)

Asterios v120 credits the 114-step row 0506 to a rerun of Atakan’s multiplier-frontier optimizer on a merged set. Its archive lists neither a unique Atakan run nor the exact merged input and command. All five configs from Atakan’s published v15 winner log retained the predecessor Asterios v119 row at 117. That diagnostic produced no exact hash match to v120. It is separate from both scoring samples. [Asterios Panoras v120](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/120)

The frozen v30 source bundle changes the main frontier and the multiplier-lanes dependency. Style 13 allows intermediate programs up to two instructions longer and includes a distance measure counting differences between sets of important numeric intermediates. The v30 bundle omits a transitively included file, elf_whole_graph.cpp. We used Atakan’s v15 file for that dependency. Its v14/v15 copies match; all files used and their hashes are itemized in source-hashes.json. The v29 and v30 main frontier files also match. This benchmark reports the compiled combination precisely. [Atakan, fixed v30 notebook](https://www.kaggle.com/code/atakanaldemir/santa-2026-joint-recipes-for-large-puzzles?scriptVersionId=371505096)

The previous full project sweep used a different input tape and the v15 profile 2,6,4,6,4,257. That earlier reference produced 155011 instructions. The current matched comparison used width 4, a 14-state budget, packet size 4, depth 6 and salt 257. Style was the only parameter changed between the two v30 arms. Neither the author’s historical 88-instruction gain nor previously merged third-party rows are included in the nine new savings.

## Design and stopping rule

From the original author’s 238-puzzle band, eight strata were formed from official puzzle attributes alone. The development group included eight rows and the held-out group sixteen. The public arm stopped there with zero gains. On the independent lane, the development sample saved one, the held-out sample saved one, the next two blocks of 32 saved three and four, and the third block of 32 saved zero. That last block triggered the registered stop for all three arms. No inference of global optimality follows from this search.

## Reproduction and evidence

Use Python 3.13 and a C++17 compiler. Set SANTA_PROJECT to the solver tree containing elf.py and checkpoint.py, SANTA_CHECKOUT to the Git clone containing aca4989, and SANTA_PUZZLES to the official puzzles.csv. Work in a fresh copy of this directory when repeating the experiment. build.py downloads the exact two public notebooks into memory, verifies byte hashes and extracts the C++ string literals without running notebook cells.

```text
python build.py --cxx g++
python history_check.py
python run.py dev --jobs 4
python run.py hold --jobs 4
python run.py 1 --jobs 4
python run.py 2 --jobs 4
python run.py 3 --jobs 4
python verify.py
```

To repeat the source diagnosis, run lineage.py with --previous and --next pointing to the v119 and v120 best_programs.csv exports. Its five profiles and input-row hashes are frozen in lineage-design.json.

The two shorter.csv files and matching origins files are the portable output. verification.json records the full table totals and hashes; details.json.gz contains each of the 432 scoring trials and solver counters. The published package contains no Kaggle input data, binaries, full submission or third-party source copies.

GoodPJW v23 contains Atakan Aldemir’s interface closure, joint-interface and relay searches. Each received the same 900 ms per case on 54 independent and 54 assisted cases. None shortened a program. [Source, settings and per-case outputs](goodpjw23-interfaces.json.gz)


## 共同重建多处算式接口

从 GoodPJW 第 40 版所附的 Atakan 源码构建两种搜索。独立与组合各测试 72 题，每题 60 个切口、宽度 24、模式 2、每次最多 600 毫秒。两种方法都没有产生更短的程序。[逐题结果](boundary-batch-results.json.gz)
