# 开发协作进度

更新于 11 月 24 日北京时间 11:18。本地最好候选为 128,494 条。[还原方法](../public-assisted/releases/portfolio.md) · [逐题上下界](puzzle-bounds.csv)

后续研究优先探索能缩短程序的新方法。新候选合入时统一验算，已有结果复用原记录。

选择新题可运行 `python -B collaboration/next_proofs.py --puzzles data/puzzles.csv --limit 20`。清单合并两边的证明，跳过已达到下界的题和已登记的同题同预算计算，按还差几步排序。`helpers` 同时跳过外部仓库已发布、尚待本地复验的预算。提议的新预算不会改动已证下界。[分工清单生成器](next_proofs.py)

| 工作 | 负责方 | 范围与进展 |
| --- | --- | --- |
| 先换一组中间值再搜索 | 独立 607 道 | 独立 36 道省 42 条，旧组合组 112 道未缩短。[逐题结果](recipe-union/forced-alternates-results.json.gz) |
| 第 971 题的精确搜索 | 768 个分片均有结果 | 344 个无解，424 个仍未决。[分片档案](evidence/0971-h9-grid.json.gz) |
| 同一个中间值分叉与加减重组 | 两条路线已测试 | 独立组与组合组均未缩短。[逐题结果](register-search/shared-forks-and-signed-results.json.gz) |
| 两层共享的中间值 | 独立 881 道、组合 875 道 | 第 993 题独立解 220 → 219，组合组未缩短。[逐题结果](register-search/shared-levels-results.json.gz) |
| 小题的候选算式重组 | 38 道完成 | 没有缩短组合候选。[逐题结果](register-search/boundary-ensembles-results.json.gz) |
| 近似等长程序的联合搜索 | 80 道完成 | 比较直接搜索和两种父本顺序，组合未缩短。[逐题结果](target-partition/divergent-donors-results.json.gz) |
| 临时增加寄存器再恢复原限制 | 独立 100 道、组合 120 道完成 | 两组未缩短。第 744 题的 267 步算式暂未排进 48 个寄存器。[逐题结果](register-search/relaxed-registers-results.json.gz) |
| 从两端搜索和配对重建 | 双向搜索独立与组合全量完成 | 双向搜索在独立 4 道各省 1 条。组合组未缩短。[逐题结果](register-search/two-sided-chains-results.json.gz) |
| 逆向重建商和余数 | 两组各 1,000 道完成 | 独立 51 道省 56 条，组合未缩短。[逐题结果](register-search/quotient-chains-results.json.gz) |
| 从其他程序借用可计算的值 | 独立 607 道、组合 230 道完成 | 独立 5 道省 6 条，组合未缩短。[逐题结果](recipe-union/full-union-results.json.gz) |
| 128,501 条候选的新一轮搜索 | 四路首轮已完成 | 倒推 980 道、依赖分区 160 道、新程序 120 道、小数子程序 150 道，组合组均未缩短。[逐题记录](register-search/refresh-128501-results.json.gz) |
| 从目标倒推时保留多条替代路径 | 独立 614 题、组合 968 题完成 | 独立第 525、641 题各省 1 条，组合组无缩短。[逐题结果](recipe-union/backward-beam-results.json.gz) |
| 按依赖关系划分子区域 | 独立 119 题、组合 138 题完成 | 独立组省 3 条，组合组省 1 条。[逐题结果](register-search/spectral-regions-results.json.gz) |
| 局部算式的有理函数重写 | 两组共 1831 道次完成 | 两组均无缩短。[逐题结果](circuit-cuts/rational-cuts-results.json.gz) |
| 从接近公开长度的不同独立解重新出发 | 158 题已完成 | 第 366 题独立解 116 → 115。[逐题结果](target-partition/near-tie-results.json.gz) |
| 收集新旧程序搜索中的备选算式 | 10 题完成 | 共省 0 条。[逐题结果](target-partition/harvest-changes-results.json.gz) |
| 集中搜索领先公开参照的题 | 15 题、20 个起点已完成 | 第 893 题 121 → 120。[逐题记录](target-partition/local-leads-results.json.gz) |
| 借用另一份解里的目标分组 | 独立 591 题、组合 100 题完成 | 独立组与对照逐题取短，在 39 道题共省 43 条。组合组省 0 条。[逐题结果](target-partition/donor-mask-results.json.gz) |
| 用最小割组合两个程序 | 独立 614 题、组合 160 题完成 | 独立 9 道省 10 条，其中 3 道混合起点胜过对照。组合组省 0 条。[逐题结果](recipe-union/cut-parents-results.json.gz) |
| 共同出口与共享因子 | 已完成两条路线 | 共享因子使独立第 183 题由 296 条缩至 295 条。共同出口实验在独立组由直接搜索缩短 3 题。两种方法均未缩短组合解。[共享因子](circuit-cuts/power-products-results.json.gz) · [共同出口](recipe-union/shared-outputs-results.json.gz) |
| 重写程序中段 | 独立和组合两组已跑完 | 独立 896 题中 23 题共省 25 条。组合 887 题中，第 374、681、944 题由中段重写各省 1 条，第 110 题由直接搜索省 1 条。[逐题结果](register-search/interior-band-results.json.gz) |
| 跨题借用算式、双分支替换、移动公因数 | 三种方法均已完成 | 跨题借用算式使独立第 821 题由 103 条降到 102 条。后两种方法分别试了 168、80 次，均未缩短。[跨题](cross-puzzle-templates/foreign-circuit-results.json.gz) · [双分支](circuit-cuts/paired-substitution-results.json.gz) · [公因数](circuit-cuts/factor-motion-results.json.gz) |
| 换掉已算出的数，再沿原指令重算 | 全部 955 道符合筛选的独立题、128 道组合题已完成 | 独立线逐题取短，20 题各省 1 条，其中 11 题改写优于对照。组合组未缩短。[逐题结果](circuit-cuts/propagation-results.json.gz) |
| 从目标倒推中间步骤 | 独立 64 道、组合 80 道已完成 | 回到正式初值后，倒推组未缩短。直接搜索为独立第 418 题省 1 条。[逐题结果](borrowed-starts/reverse-targets-results.json.gz) |
| 协作者发布的可选加速 | Hiyohane 分支 | 该分支已发布固定顺序的寄存器分配和候选算式筛选两项补丁。[寄存器分配](https://github.com/Hansen0223/Santa_2026/commit/96d0f8a) · [算式筛选](https://github.com/Hansen0223/Santa_2026/commit/ee332cd) |
| 拼接两份程序并补回缺少的输入 | 341 道独立题和 86 道组合题已完成 | 拼接后搜索在 9 道独立题胜过直接搜索。逐题择短后，独立程序共省 19 条，组合未变。[逐题记录](register-search/stitch-results.json.gz) |
| 枚举两个短算式再用一次运算连接 | 78 道独立题和 88 道组合题已完成 | 两组枚举均未胜过直接搜索。保留直接搜索找到的 3 条独立改进。[逐题记录](circuit-cuts/product-join-results.json.gz) |
| 从实际寄存器内容重新求解后半段 | 独立路线 874 道已跑完 | 与复用旧中间值及直接搜索的结果合并，38 道独立题共省 41 条，其中第 310 题也缩短仓库的公开辅助解。[逐题结果](register-search/suffix-results.json.gz) |
| 用目标余数推测有用的乘数 | 两组各 64 道，另各 36 道重新构造 | 独立和组合均未缩短，停止扩大。[结果](structure-controls/residue-bridges-results.json.gz) |
| 改写加减程序后继续搜索 | 已完成 410 道独立题、150 道组合题 | 独立主线 18 题共省 21 条；组合未缩短。[逐题结果](circuit-cuts/transposed-sums-results.json.gz) |
| 用中心差值补充中间数 | 两条路线各 96 道已完成 | 两组均未缩短，停止扩大。[结果](circuit-cuts/reflection-results.json.gz) |
| 同时替换两处共用算式 | 独立 370 道、组合 296 道完成 | 本轮独立主线 15 道省 18 条，组合第 268 题省 1 条。[逐题记录](recipe-union/paired-splice-results.json.gz) |
| 共用一个新中间值重建多个出口 | 独立 96 道、组合 64 道完成 | 两路均未缩短，停止扩大。[逐题记录](circuit-cuts/fanout-results.json.gz) |
| 986 道题的新旧程序混合搜索 | 已完成两种搜索 | 第 756 题省 1 条，总分 132,544。[逐题档案](../public-assisted/releases/v182-search-results.json.gz) |
| 重新安排共享中间值的目标组 | 两组各 16 题已完成 | 两组均未缩短。[逐题档案](withheld-targets/frontier-beam-results.json.gz) |
| PR #4 的六项下界 | 已合入逐题表 | 第 50、515、583、773、777、913 题各提高 1 条，合计 37,987。[合并回执](evidence/combined-1875a66.json) |
| 从同一初稿生成多个独立程序再组合 | 25 道已完成 | 11 道独立题共省 13 条，其中 4 道也缩短了最好候选。[逐题结果](recipe-union/sibling-results.json.gz) |
| Pardheev 的 132,997 条候选 | 已合并，三项后续试验已完成 | 419 道带来改进，最好候选 132,841 条。另在 80、24、60 道题上试了三种改写。[合并与逐题结果](../public-assisted/pardheev/) |
| 保留目标的最后几步，重建共用部分 | 已完成，144 道独立题省 6 条 | 第 670 题省 2 条。[逐题结果](withheld-targets/terminal-shell-results.json.gz) |
| 在协作分支的 25 道题上重搜 | 已完成 | 独立解另省 129 条，两条路线按题择短后，最好候选另省 64 条。[输入与结果](recipe-union/contributor-results.json.gz) |
| 72 个位置搜索后编回 48 个 | 已完成，两条路线各 36 道 | 未缩短，结束此方向。[逐题结果](register-search/relaxed-results.json.gz) |
| 对新协作程序继续搜索 | 已完成，两条路线各 25 道 | 独立解少 18 条，最好候选少 17 条。[逐题结果](recipe-union/contributor-second-results.json.gz) |
| 可逆地改变初始数 | 两条路线各 36 道已完成 | 第 995 题比直接搜索短 1 条，与已有最好长度持平。[结果](borrowed-starts/seed-basis-results.json.gz) |
| 借用旧解中消失的中间数 | 48 道公开辅助题已完成 | 三种方法均未省下指令，结束此方向。[结果](borrowed-starts/historical-results.json.gz) |
| 协作分支的 25 个独立程序 | 23 道并入独立解 | 独立解共省 130 条，6 道题也使最好候选缩短 27 条。[各题差额](evidence/hiyohane-0b893d9.json) |
| Hiyohane 的最新结果 | 第 815、870 题各省 1 条 | 第 493 题两边分别找到一份 249 条程序。[逐题来源](evidence/hiyohane-5531355.json) |
| 紧数值上限下共用一个较大的数 | 32 道已完成 | 30 道有多个目标可用同一数相减得到，实际程序长度均无改善，结束此分支。[结果](shared-intercept/upper-anchor-results.json.gz) |
| 共享前缀的暂借初值 | 40 道已完成 | 独立路线逐题择短共省 4 条，第 871 题仅新方法缩短。公开辅助组无改进。[逐题结果](borrowed-starts/shared-prefix-results.json.gz) |
| 可逆地替换一至两个目标 | 两条路线各完成 36 道 | 留出题上未超过直接搜索，结束扩大。[实验](goal-differences/results.json) |
| 暂借数再从正式初值重建 | 已完成全部 840 道独立题 | 148 道共省 198 条，108 道比同预算直接搜索更短。[逐批结果](borrowed-starts/results/summary.json) |
| Hiyohane 的 9 道独立改进 | 已复验全部 1,000 题 | 9 道共省 19 条。[来源与逐题差额](evidence/d6e507e-candidate.json) |
| 早间公开版本第二批 | 已完整回放 | 九道题共省 11 条，公开辅助候选 133,814 条。[逐题来源](../public-assisted/releases/20261121-0933.json) |
| 重新构造 873 道题 | 已完成 | 独立解在 132 道题共省 194 条，其中 73 道比直接优化整题更短。[分组与逐题结果](withheld-targets/extension/results.json) |
| 11 月 21 日早间的公开程序 | 已对照五个版本 | Asterios v150 与 GoodPJW v20 的 171 道改进共省 235 条。与最新独立解合并后为 133,825 条。[逐题来源](../public-assisted/Releases-20261121.json) |
| PR #1 | 作者已更正计数并撤回导入，PR 已关闭 | 91 道题的报告长度仍比主线短，逐题共差 125 条。从主线程序出发尝试两种搜索，本轮均未缩短。[审查意见](https://github.com/Hansen0223/Santa_2026/pull/1#pullrequestreview-6001705905) · [两组结果](evidence/pr-1-score-hints.json) |
| 第 272 题的证明 | 已独立复验 | 24 个分片均已穷尽，本题下界提高到 16，合计 37,981。[合并回执](evidence/combined-62e194b.json) |
| 外部新增的 12 道证明 | 已逐片复核并合入 | 12 道各提高 1 条，合计下界 37,980。[合并回执](evidence/combined-membership-8d4b4df.json) |
| GoodPJW v12 和 E-Max AI 134124 | 全部回放 | 27 道省 34 条，已更新到 134,079。另在 96 道独立题中找到 6 个较短程序，独立候选为 140,675。[逐题来源](frontier-134285/public-134079/README.md) |
| Roman Rozen、bikrambasnet1 和 E-Max AI 新发布的程序 | 已复核来源并导出 | 47 道共省 60 条；独立解在第 697 题另省 2 条，总计 134,113。[逐题署名](frontier-134285/roman-134125/README.md) |
| 是否需要指定的辅助数 | 622 道均已检验 | 47 道各提高 1 条，总下界 37,968。[原理和逐叶复核](conditional-helper-membership/README.md) |
| 从当前算式合成新的临时目标 | 两组已完成 | 独立解省 9 条，公开辅助组无直接缩短。独立解在第 697 题也省 2 条。[结果](synthetic-temporary-targets/README.md) |
| 第 271 和 791 题 | 已验证 | 第 271 题本地重建为 38 条，与发布程序一致。第 791 题取 Asterios v126 的 135 条。两题共省 3 条。[所用版本和作者](frontier-134285/asterios126-audit.json) · [第 271 题复现](frontier-134285/retained48/results.json) |
| 临时增加一个目标再移除 | 三组全部完成 | 独立路线共省 28 条，逐题合入公开辅助候选共省 4 条。六道独立题的临时目标方案胜过两种对照。[分组和结果](temporary-targets/README.md) |
| Asterios 第 125 版 | 已完成 | 第 791 题减少 11 条，公开辅助总计 134,183。[逐题署名及重放](frontier-134285/asterios125-audit.json) |
| 比较 GoodPJW v11 与 E-Max AI 的新父程序包 | 已复核 | GoodPJW v11 的 67 题共缩短 91 条，公开辅助候选降至 134,194；第 44、45 版全表未带来额外缩短；第 46、47 版选中的三道题本地重建后，第 64 题另省 1 条。[三题九次搜索](frontier-134285/retained/README.md) · [逐题复核](frontier-134285/good11-audit.json) · [已登记的数据版本](frontier-134285/sources.json) |
| 从初值出发检验中间值集合是否足够 | 本组已结束 | 两条路线各 8+16 题，产生 8,678 个必要条件，均无严格缩短。[小规模穷举及两组对照](grounding-cuts/README.md) |
| 分开求解两组目标再合并 | 本组已结束 | 两条路线各 12+24 题，独立整题对照省 5 条，两种分组均省 4 条；公开辅助均无缩短。[逐项结果](target-partition/README.md) |
| 把多个目标的相同数位分组 | 本组已结束 | 全部 384 份构造可在物理寄存器上执行，32 题中分组构造在 22 题胜过直接求和，在当前独立父本上零改进。[两组结果](pippenger/result.json) |
| 用模运算同时合成两段短程序 | 本组已结束 | 两种模数设置都通过植入题，32 道真实题的独立全表仍为 140,727 条。[结果和实例](residue-joint/README.md) |
| 在每种首个辅助数上分别排除共边三角形 | 全部条件树已复核 | 680 道中 404 道各增加 1 条下界，4,098 个叶子经独立复核。另五道外部证明已完成全部 133 个分片的复核，两组合并共提高 409 条。[合并结果](evidence/combined-conditioned-external.json) · [复核](distinct-diamond/conditioned.md) |
| 两个共边三角形的五个不同目标 | 已复核全库 | 980 道未达最短的题全部筛完。两套算法在 622 道各证实一条额外的下界。[数学依据和重放](distinct-diamond/README.md) |
| 目标子集的辅助值容量上界 | 已复核全库 | 10 题各提高 1 条，其中 9 题与四辅助数证明重合。第 820 题为这条方法独有。[证书与手算实例](subset-capacity/README.md) |
| 四个互连辅助数的下界 | 已复核全库 | 普通前缀认证 113 题，复用原有条件树再认证 213 题。后者与共边三角形证明重合 205 题。[普通前缀](distinct-helper-edges/README.md) · [逐叶认证](distinct-helper-edges/conditioned.md) |
| 第 926 题新增下界 | 已完成 | 32 片复核完成，37,710,100 个节点。第 926 题上下界为 [15,20]，共同下界 36,768。[原始分片、来源和复验](evidence/upstream-95780b7.json) |
| 第 123 版新变化题的三路对照 | 本组已结束 | 七题三种方法各 168 秒，均无严格缩短；四个完整候选经两个解释器重放。[可复现结果](v123-seven/README.md) |
| 合并 Asterios 第 123 版 | 已验证 | 原版共 134,298 条，七题比本地旧程序合计短 13 条。第 707 题贡献 5 条，总数降至 134,285。[各题作者、节省条数和来源](evidence/asterios-v123-134285.json) |
| 更新公开来源和共同下界 | Hansen0223 / Codex | 已双重回放 Asterios v121，独立导出为 134,316 条；相对主库 5 道题省 6 条。共同下界 36,768 条。[五道题的原始署名](evidence/asterios-v121-134305.json) · [证明回执](evidence/upstream-35c63e8.json) |
| 重建 E-Max AI 的保留父本策略 | 已复现两版 | 用已获署名的父程序及 Wang 原引擎重建 v41 的 0740，以及 v42 的 0079、0305、0871、0955。[v41 来源](retained-pool/audit.json) · [v42 各题父本、种子与比对](retained-pool/v42-audit.json) |
| 多份算式的共同依赖 | 已完成 | 两种搜索在 32 道开发题和 64 道留出题上，两条路线均无缩短，已结束。[选题、输入与结果](recipe-union/README.md) |
| 长题的共享商和带余因式分解 | 已完成 | 在 12 道开发题及 24 道留出题上，两种方法合计缩短 4 道独立题、1 道公开辅助题。附冻结父本、选题和逐组复现。[结果及源码](shared-quotients/README.md) |
| 第 113 版与旧程序的跨版本算式组合 | 已完成 | 在 v113 缩短的 354 题中选 48 道开发题及 48 道留出题。同预算共 288 次搜索，两组均无额外缩短，已停止。[题号与逐项结果](release-crossover/README.md) |
| 全题同步生成有符号位矩阵 | 开发对照已完成 | 在 0493、0269、0163、0255 上，跨目标共享使同一构造从 2,189 降到 2,015 条，强独立父本合计 1,122 条，保留其余四道留出题。[输入、对照及复现](positional-sums/README.md) |
| 共同生成一组相关目标 | 本组已完成 | 独立 96 题省 1 条，公开辅助 180 题无改进，停止扩展。[对照记录](annealing/README.md) |
| 整题图退火 | 第三轮已回放 | 此轮在独立线上另有 65 题省 80 条。原版和多样性变体同时保留。[来源与复现](annealing/README.md) |
| 官方初值的整题再生成 | 已完成 | 已复核三道独立题合计省 7 条。额外 26 题无改进，这一生成器的扩展结束。[父本、消融和全表复验](official-heads/README.md) |
| 退火后的四种局部改写 | 已完成 | 对独立 141,026、公开辅助 134,430 中新缩短的行做分层检验。独立 266 题及公开辅助 61 题均已跑完，独立最后 170 题还省 32 条，合并此前成果后净省 23 条。[各组结果](wang-polish/README.md)[题号与父本哈希](evidence/wang-polish-design.json) |
| 预测同预算下的搜索收益 | 首轮已完成 | 预测组 100 题省 2 条，匹配对照 100 题省 1 条。纯独立双父本对照与后续扩展已回放，1000 题完整跑完，独立表 140,813 条。[固定分组和结果](annealing/README.md) |
| 从练习标签检验多目标递推 | 已完成 | 72 个植入样本均恢复；真实练习 5,224 个遮蔽位置在严格规则下 0 命中，放宽后仅 2 个，12 道计分题的 354 个遮蔽位置均无命中，已结束。[对照与复现](structure-controls/README.md) |
| 多组目标共用偏移量 | 已完成 | 8 个植入样例均能缩短。冻结的 6 道开发题及 6 道留出题均未缩短，停止扩展。[题号及逐组结果](structure-controls/README.md) |
| 独立电路的稀疏算式筛选 | optimize/shared-recipe-portfolio 提供算法，Codex 做新父本对照 | 外部分支 e24a8e5 已发布单父本、共享差值和多父本的图筛选。已完成新独立父本的预登记 32+32 题及 1,000 题全量扫描，单父本省 1 条、多父本省 2 条。公开辅助的两个 1,000 题对照均未继续缩短，已结束。[逐项结果](shared-recipe-branch/README.md) [外部分支及源码](https://github.com/Hansen0223/Santa_2026/tree/e24a8e5557434d2a2022fc7c9873e71aab148661) · [父本指纹与全部题号](evidence/scc-fresh-design.json) |
| 跨不同初值迁移短程序 | 已完成 | 从 40 道练习题提取模板；另用 24 道练习及 12 道计分题检验。计分题没有缩短。0199 的三个数值命中均替代不了当前程序中更短的共享计算，已停止。[输入、分组与实测程序](cross-puzzle-templates/README.md) |
| GoodPJW v10 的历史父本交叉 | 已完成 | 16 道冻结独立题，五组同预算搜索中取短。第 180、225、429、927 题共省 6 条，独立总数 140,805。[五组与逐题结果](goodpjw-incremental/independent-results.json) |
| 近长独立父本的交叉扩展 | 已完成 | 已完成 269/269 道，46 题共省 60 条。每题三种方法各 180 轮。[固定分组](goodpjw-incremental/extension-design.json) · [各批实际结果](goodpjw-incremental/extension) |
| 新公开程序的交叉改写 | 已完成 | 50 道题各跑两种方法，每种 360 轮，0147 从 96 到 94，0557 从 109 到 108。[逐题结果、署名与复现](fresh-public-recombination/README.md) |
| 用连续松弛选新增中间值 | 已完成 | 两条路线各 8+16 题，计数选取、松弛选取及现有数值三种整数模型全部达有限库最优，真实题均未缩短。植入算例从 6 到 3。[逐题结果](helper-pricing/rows.json.gz) · [运行程序](helper-pricing/search.py) |
| 两条目标分支共用尺度和截距 | 已完成 | 另 12 道题检查 13,615 个跨分支节点对，8 个重建候选可落地，均未缩短；植入题从 8 条到 6 条。[实际构造与记录](joint-euclid/README.md) |
| 两目标欧几里得链 | 已完成 | 单轮对照和多轮法在 12 道真实题均无收益；植入例从 18 条缩至 6 条，真实目标对未找到可连接的末端。[逐组实验](joint-euclid/README.md) |
| Atakan 的多目标乘数搜索 | 已完成 | 在 120 道独立题上 8 题省 9 条。公开辅助 24 题无缩短。独立第三批扩展无收益，已按登记停止。[逐题结果与作者源代码复验](atakan-frontier/README.md) |
| Atakan 与 Wang 的先后次序 | 已完成 | 8 个先前改善行及 8 个匹配行，合计省 7 条。0627 先用 Atakan 再用 Wang 得到 115 条，比两者各自运行后取短额外省 1 条。[96 个阶段程序与复验](cross-method-order/README.md) |
| 禁止短期内重用刚弃的算式 | 已完成 | 开发和留出各组均以相等提案次数实测。两个三选一变体没有缩短；原版独立省 2 条、公开辅助省 1 条。[两个分组与源码](reactive-tabu/README.md) |
| 短算术电路的等价替换 | 已完成 | 两组各 32+32 题共检查 13,619 个子图，13,921 个不同的整数改写均未缩短整题。人工完全平方从 6 条缩至 2 条。[代码与逐题实测](circuit-cuts/README.md) |
| 交换不同温度下的程序 | 已完成 | 原版、四条无交换轨迹、四条可交换轨迹都跑完 32+32 题；留出组 203 次交换不同程序，三种设置都未缩短，已停止。[逐题与复现](parallel-tempering/README.md) |
| 从两个已知输出反推两个中间数 | 已完成 | 8+16 题的新逆算式均没有超越同条件对照。对照中的两份父本组合使第 152 题从 115 降到 114。[实验与复现](affine-elimination/README.md) · [逐父本排除](affine-elimination/control-origins.json) |
| 逐个目标替换两份程序的祖先运算 | 已完成 | 32+32 道独立题实际重放 6,888 个中间程序。定向替换、随机替换、原 Wang 均无缩短，已停止。[完整结果与单题复现](target-relink/README.md) |
| 操作数超过 48 个时复用寄存器 | 首轮已完成 | 10 道题各测两种来源，合计 1,920 轮。20 份父程序单独重排均无缩短；重新搜索算式后，独立第 541 题省 1 条，公开辅助第 773 题省 1 条。[题号、结果与复现](register-search/README.md) |
| 18 道短题的单父本和双父本对照 | 已完成 | 三组一共 18,900 轮。单独立父本在第 84 题少 1 条，双独立父本在第 29 题少 1 条，另 16 题两者相同。公开辅助线未缩短。另用布尔约束求解检查 14 题，42 次均达预算，已结束这组配置。[父本、结果及复现](short-program-comparison/README.md) |
| 第 882 题的最短性 | 23 条已证最短 | 10 个辅助值预算的 768 个原分片均已排除。最后 10 个分片的 240 个细分格全部排除，23 条可行程序通过回放。[证明与复跑](puzzle-0882-diversity/README.md) · [合并回执](evidence/combined-882.json) |
| 从独立父程序反推共享中间数 | 首轮已完成 | 已缩短第 250、387、711、818 题；另在 80 道题各做 350 轮，10 道题共省 12 条，其中 4 道也刷新本仓库的公开辅助上界。[单题还原](puzzle-0711/README.md) · [80 题名单、父本与结果](puzzle-0711/wide/README.md) |
| 多目标共用一对操作数 | 已完成 | 96 个可控算例均成功。64 道真实留出题上，两条路线分别检查 37,319 和 37,663 组方程，均无缩短，已结束。 |
| 多父本联合搜索及公开方法核对 | 已完成 | 第 134 题的三份独立父程序合并后得到 28 条，再改写得到 27 条。核对了 Asterios 第 99 版、Rudolph 第 54 版，以及 Sadam Torres 方法在 24 道分层选题上的表现。[三父本实验](three-parents/README.md) · [24 题对照](evidence/sadamtorres-controls.json) · [Rudolph 第 54 版](evidence/rudolph-v54.json) |
| 固定输入与输出的程序段重建 | 已完成 | 两份 1,000 题候选共检查 9,771 组不同的输入与输出，8,988 组已证局部最短。另已完成保留旧辅助值的搜索和寄存器重新排序。第 649 题缩至 118 条，保留原后缀 90 条。[精确搜索记录](window-search/README.md) · [独立回放](exact-boundary/README.md) |
| 其他无约束搜索 | 已暂停 | 第 149 题的新程序达到 16 条，整题已证最短；第 901 和 212 题保留分片存档。各题进度及未决分片数见[运行快照](evidence/ongoing-at-checkpoint.json)。 |
| 检查额外寄存器能否省去中间步骤 | 已完成 | 三组实验共涉及 108 道不同真题。允许至多三个额外输入时，10,970 个符合条件的程序段中，没有一段能省掉全部辅助值。[搜索范围和对照](evidence/register-window-controls.json) |
| 四种程序改写的组合 | 已完成 | 按顺序做成组重写、整题中间值替换、因数分解和算式组合。已比较最近有改进的 40 道独立题、39 道公开辅助题，独立省 11 条、辅助省 3 条。独立线余下 91 题另省 7 条。原先未改进的 48+48 题中仅独立第 730 题省 1 条，串行在两组留出题均未超过最佳单法。 |
| 远端证明复核 | 已完成 | 已合并 8dd7478 新增的 65 项判定，重跑 1,151 个分片，状态、各片节点数及末层候选数均复现。外部证明现合计 33,733 条；逐题合并后仍为 36,731 条。前一批亦已复核 27 项、509 片。[65 项复核明细](evidence/upstream-8dd7478.json) · [复跑脚本](evidence/replay_increment.py) |

已回放独立候选 139,294 条、仓库公开辅助候选 133,599 条及组合候选 128,494 条。全题已证下界 37,988，共 21 题已达最短。北京时间 11:40 的榜首为 125,650 条。[官方榜单](https://www.kaggle.com/competitions/santa-2026/leaderboard)

[可复核的证明与分片](proof-status.md) · [已试方法与来源](methods.md) · [第 334 题复现](factor/README.md)
