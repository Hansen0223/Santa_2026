# Santa 2026 求解进展

## 北京时间 11 月 21 日 20:09

Rudolph 第 126 版让第 8 题再省 1 条。组合候选现为 **132,513 条**，已重放全部题目。[固定输入和重建方法](public-assisted/releases/portfolio.md)

## 北京时间 11 月 21 日 20:01

独立解降至 **139,515 条**。沿现有指令重算，在 955 道独立题上与直接搜索逐题取短，20 道共省 20 条。另在反向求解试验中，直接搜索使第 418 题再省 1 条。把这些新程序与最新公开程序重新组合，组合候选保持 **132,514 条**。[重算结果](collaboration/circuit-cuts/README.md) · [反向试验](collaboration/borrowed-starts/README.md)

## 北京时间 11 月 21 日 19:59

Asterios Panoras 的公开笔记本在代码中提供第 290 题的 147 条程序。合入后比上一版少 1 条，组合候选为 **132,514 条**。[还原方式和原始笔记本](public-assisted/releases/portfolio.md)

## 北京时间 11 月 21 日 19:52

第 505 题少 2 条，第 778 和 933 题各少 1 条，组合候选降至 **132,515 条**。第 505、933 题由 GoodPJW 贡献，第 778 题在 Asterios 的归档中署名为 public merge。[逐题改进与还原方法](public-assisted/releases/portfolio.md)

## 北京时间 11 月 21 日 19:40

独立解缩短 22 条至 **139,536 条**。把历史程序的前段和另一份程序的后段拼接，第 790 题直接由 229 条降至 228 条，拼接后继续搜索在 9 道题上胜过直接搜索。第 985 题的独立程序也将仓库直接提供的公开辅助解缩短到 **133,624 条**。组合候选仍为 **132,519 条**。[拼接实验](collaboration/register-search/README.md) · [短算式枚举](collaboration/circuit-cuts/README.md)

## 北京时间 11 月 21 日 19:23

Asterios 第 188 版让第 295 和 812 题各省 1 条，最好候选为 **132,519 条**。目前仅需一份外部 ZIP 即可从仓库重建。[完整还原方式](public-assisted/releases/portfolio.md)

## 北京时间 11 月 21 日 19:09

第 793 题从 204 条缩至 203 条，候选总计 **132,521 条**，已按官方输入重放 1,000 题。独立搜索在 38 道题共省 41 条，独立主文件为 **139,558 条**。第 310 题也让仓库直接发布的公开辅助解省下一条，现为 **133,625 条**。[组合候选](public-assisted/releases/portfolio.md) · [独立结果](collaboration/register-search/README.md)

## 北京时间 11 月 21 日 18:53

Ishan Karnick 第 5 版在七题各省一条，GoodPJW 第 41 版在第 930 题省一条，最好候选为 **132,522 条**。[还原方法与逐题来源](public-assisted/releases/portfolio.md)

## 北京时间 11 月 21 日 18:40

第 689 和 751 题各省 1 条，最好候选降至 **132,530 条**。Rudolph 第 123 版与仓库的公开辅助程序即可重建完整解。独立搜索中，对 410 道题尝试更换加减程序的起点，与相同轮数的直接搜索逐题取短后，18 题共省 21 条。合并协作者进展后，独立解为 **139,599 条**。北京时间 18:36，官方榜首降至 127,200 条。[候选与来源](public-assisted/releases/portfolio.md) · [独立搜索逐题结果](collaboration/circuit-cuts/transposed-sums-results.json.gz)

## 北京时间 11 月 21 日 18:30

最好候选从 132,536 降至 **132,532 条**。GoodPJW 的第 40 版和 Hiyohane 的第 374 题带来 4 条改进。固定这次仓库版本后，只需一份公开 ZIP 即可还原完整候选。[输入、来源和还原方式](public-assisted/releases/portfolio.md)

## 北京时间 11 月 21 日 18 时

最好候选为 **132,536 条**，比上一版省 8 条。独立候选为 **139,655 条**。本轮两处算式同时改写的试验在 370 道独立题上与直接搜索比较，5 道题的改写组优于对照。两组逐题择短后的结果与协作者最新版本合并，独立主线 15 道共省 18 条。公开组合 296 道中，第 268 题由对照组缩短 1 条。[候选及来源](public-assisted/releases/evening-20261121.md) · [实验数据](collaboration/recipe-union/paired-splice-results.json.gz)

## 北京时间 11 月 21 日 17 时

公开程序与协作者提交逐题合并后为 132,545 条，再从第 756 题省下 1 条，达到 **132,544 条**。独立候选为 **139,730 条**。PR #4 的六项证明使总下界升至 37,987，仍有 20 题已证最短。PR #5 的分片成本估算工具和两种替代方法的分析也已合入。[还原当前最好候选](public-assisted/releases/v182.md) · [第 4 号 PR](https://github.com/Hansen0223/Santa_2026/pull/4) · [第 5 号 PR](https://github.com/Hansen0223/Santa_2026/pull/5)

## 北京时间 11 月 21 日 11:49

Pardheev 新公开的 132,997 条程序中，419 道短于仓库的公开辅助程序。按题择短得到 **132,841 条**，比 Pardheev 整份解少 156 条。北京时间 11:44 官方榜首为 128,330 条，相差 4,511 条，尚未提交。Pardheev 说明其程序可直接用于比赛或作为继续搜索的起点，原版从作者的发布页取得。已开始在 80 道题上重搜。另一组 96 道独立题共省 2 条，独立候选达到 **139,930 条**。[合并方法和署名](public-assisted/pardheev/) · [逐题差额](public-assisted/pardheev/assembly.json) · [96 道独立题](collaboration/withheld-targets/terminal-shell-next-results.json.gz)

## 北京时间 11 月 21 日 11:47

协作程序的第二轮搜索让最好候选在 10 道题上共省 17 条。另合入 Asterios 第 380 题的 1 条改进，可直接下载的公开辅助候选为 **133,655 条**。独立候选为 **139,932 条**，包含重建前半段得到的 3 道改进。截止 11:44，官方榜首为 128,330 条。[协作程序](collaboration/recipe-union/contributor-second-results.json.gz) · [重建结果](collaboration/withheld-targets/terminal-shell-results.json.gz) · [第 380 题](public-assisted/releases/gift-380-v67.json)

## 北京时间 11 月 21 日 11:36

在三道新公开程序及四道可重建的程序上取得改进，第 558 题在公开的 119 条基础上再省 1 条，达到 118 条。当前最好候选 **133,673 条**，比上一版少 8 条；独立候选 **139,954 条**。截至 11:28，官方榜首为 128,330 条，相差 5,343 条。[七道题及各自来源](public-assisted/releases/frontier-133772.json) · [已结束的旧程序试验](collaboration/recipe-union/alternate-pilot-results.json.gz)

## 北京时间 11 月 21 日 11:26

Hiyohane 同时发布的 11 个独立程序全部较短，独立候选达到 **139,955 条**。当前最好候选为 **133,681 条**。[11 道题及贡献者提交](collaboration/evidence/hiyohane-88c64b6.json)

## 北京时间 11 月 21 日 11:25

在协作分支的 25 道题上重新搜索，已有程序还能再缩短。独立路线中 21 题共省 129 条，得到 **139,966 条**；从两条路线逐题择短，最好候选省 64 条。另合入 Asterios 第 121 题的 1 条改进，本地最好候选为 **133,681 条**，与 11:00 榜首相差 5,351 条。[25 道题逐项结果](collaboration/recipe-union/contributor-results.json.gz) · [第 121 题](public-assisted/releases/gift-121-v64.json)

## 北京时间 11 月 21 日 11:11

Hiyohane 在协作分支另存了 25 个独立程序。其中 23 道比当前独立解短，共省 130 条，独立解达到 **140,095 条**。6 道同时超过公开辅助解，共省 27 条，最好候选达到 **133,746 条**。第 995 题省 14 条，第 362 题省 8 条。[各题差额与原始提交](collaboration/evidence/hiyohane-0b893d9.json)

## 北京时间 11 月 21 日 11:08

Hiyohane 刚提交的第 815、870 题各再省 1 条。本地最短候选为 **133,773 条**，距 11:00 官方榜首 128,330 条相差 5,443 条。第 493 题双方独立找到了两份不同的 249 条程序，保留本地找到的程序，合并记录保留另一份。[合并的三道题](collaboration/evidence/hiyohane-5531355.json) · [作者提交](https://github.com/Hansen0223/Santa_2026/commit/553135531d60b3d780104b6cdfadff1c65f79016)

## 北京时间 11 月 21 日 11:06

本地最好候选 **133,775 条**，比上一版少 8 条，距 11:00 官方榜首 128,330 条还差 5,445 条。独立候选 **140,225 条**，比上一版少 29 条。原定的 840 道独立题已完成，148 道比实验起点短，共省 198 条。另一组 40 道题的共享前缀实验在第 871 题获得独有改进；第 493 题通过保留部分重复计算由 251 条降至 249 条。[八道公开改进](public-assisted/releases/frontier-133780.json) · [840 道题](collaboration/borrowed-starts/results/summary.json) · [40 道题](collaboration/borrowed-starts/shared-prefix-results.json.gz) · [第 493 题](collaboration/register-search/README.md)

## 北京时间 11 月 21 日 10:47

本轮 5 道公开辅助题各省 1 条，当前最好候选为 **133,783 条**。独立候选为 **140,254 条**，以 10:35 官方榜首 128,330 条计算，最好候选相差 5,453 条。[五道改进及署名](public-assisted/releases/frontier-133788.json) · [独立搜索](collaboration/borrowed-starts/results/summary.json)

## 北京时间 11 月 21 日 10:41

公开辅助候选 **133,788 条**，独立候选 **140,282 条**。第 76、458 题各省 1 条。学习排序、可逆目标替换及三种接口重建都完成了与现有方法的比较，均未带来额外节省。[两道改进](public-assisted/releases/20261121-1035.json) · [学习排序](collaboration/helper-pricing/learned-results.json.gz) · [目标替换](collaboration/goal-differences/) · [接口重建](collaboration/atakan-frontier/goodpjw23-interfaces.json.gz)

## 北京时间 11 月 21 日 10:30

公开辅助候选为 **133,790 条**，独立候选为 **140,327 条**，均已逐题回放。E-Max AI 的五个新程序与作者逐条吻合，再合入独立程序后，比其 133,796 条的文件少 6 条。54 道题上的两种子图组合均未缩短整题，结束这项实验。[五道复现题与额外改进](public-assisted/releases/emax-133796-output.json) · [54 道对照题](collaboration/recipe-union/cone-assignment-results.json.gz)

## 北京时间 11 月 21 日 10:21

公开辅助候选从 133,808 降到 **133,798 条**，其中第 279 题是 Asterios 新发布的 255 条程序。独立候选为 **140,363 条**。两份候选各完整回放 1,000 题。10:12 官方榜首为 128,330 条。另开始对比直接搜索与暂时改写一至两个目标的搜索。[逐题改进与原作者](public-assisted/releases/20261121-1012.json) · [新实验的分组和预算](collaboration/goal-differences/)

## 北京时间 11 月 21 日 10:11

E-Max AI 发布的搜索条件在 2 道题上从已确认来源的程序重新得到改进，两套解释器均回放为 **133,808 条**。独立候选为 **140,371 条**。另一项对 88 道题组合已有算式的试验没有得到更短程序。[逐题复现与来源](public-assisted/releases/emax-133806-reruns.json) · [88 道题的尝试记录](collaboration/evidence/graph-selection-88.json.gz)

## 北京时间 11 月 21 日 10:03

公开辅助候选降到 **133,810 条**，独立候选降到 **140,384 条**，均已回放全部 1,000 题。公开辅助候选的第 185、358、988 题各省 1 条。另已合并第 2 个 PR，复现旧父本的两道改进并保留主分支更短的程序。[三道改进和原作者](public-assisted/releases/20261121-three-programs.json) · [独立搜索进度](collaboration/borrowed-starts/results/summary.json) · [PR 实验](collaboration/anneal-current-parent/)

## 北京时间 11 月 21 日 09:50

接入 Asterios 公开的第 295 题 122 条程序后，公开辅助候选为 **133,813 条**。Hiyohane 的九道独立程序省 19 条，暂借中间值的留出和第一批扩展试验合计省 17 条，合并的独立候选为 **140,411 条**。全部 1,000 题已重放。[第 295 题的来源](public-assisted/releases/asterios-gift-0295.json) · [九道协作改进](collaboration/evidence/d6e507e-candidate.json) · [独立实验](collaboration/borrowed-starts/README.md)

## 北京时间 11 月 21 日 09:39

Asterios 第 151 版和 GoodPJW 第 21 版共提供九道较短程序。完整复核后，公开辅助候选由 133,825 降到 **133,814 条**，独立生成候选为 **140,447 条**。09:33 官方榜首为 128,330 条，相差 5,484 条，尚未提交 Kaggle。[逐题得分、归属与固定版本](public-assisted/releases/20261121-0933.json)

## 北京时间 11 月 21 日 09:29

Hiyohane 提交的独立解在六道题共省 22 条。复验全部 1,000 题后，独立候选更新到 **140,447 条**。这六题现有公开辅助解均更短，公开辅助总分仍为 **133,825 条**。[逐题变动](collaboration/evidence/dd930b4-candidate.json) · [贡献者提交](https://github.com/Hansen0223/Santa_2026/commit/dd930b4420380a954469c31c9faefed5a859b349)

## 北京时间 11 月 21 日 09:25

独立搜索完成预先选定的 873 道题，132 道共省 194 条，候选由 140,663 降至 **140,469 条**。五份公开版本与上一份公开辅助候选逐题比较，在 171 道省 235 条，合计 133,828。与新独立解合并后再省 3 条，得到 **133,825 条**。两个完整文件均已逐题双重回放。09:11 榜首为 128,330，相差 5,495 条，尚未提交 Kaggle。[独立实验](collaboration/withheld-targets/README.md) · [公开版本与逐题变动](public-assisted/Releases-20261121.json)

## 北京时间 11 月 21 日 00:16

公开来源合并后为 **134,065 条**，再与独立解逐题择短为 **134,063 条**。重建 E-Max AI 的七个结果省 8 条，另有六个公开程序各省 1 条。独立路线在 24 道试验题省 12 条，独立候选为 **140,663 条**。两份候选均已完整回放，未提交 Kaggle。[公开来源与程序](collaboration/frontier-134285/diverse-134083/README.md) · [独立结果和 873 道扩展名单](collaboration/withheld-targets/README.md)

## 北京时间 11 月 21 日 00:05

另外 12 道题的最短长度下界各提高 1 条。经完整复核，1,000 题合计下界从 **37,968** 升至 **37,980**。仍有 20 题已证最短。[12 道题的复核结果](collaboration/evidence/combined-membership-8d4b4df.json)

## 北京时间 11 月 21 日 00:02

公开辅助候选为 **134,079**。与前一版相比，GoodPJW 发布的 26 道题省 33 条，E-Max AI 的第 942 题再省 1 条。独立搜索另在 6 道题省 9 条，独立候选为 **140,675**。两份候选均已完整回放。00:02 榜首 128,330，相差 5,749 条，尚未提交。[本轮 27 道](collaboration/frontier-134285/public-134079/README.md) · [独立搜索](collaboration/synthetic-temporary-targets/README.md)

## 北京时间 11 月 20 日 23:52

公开辅助候选 **134,113**，独立候选 **140,684**。与上一份 134,175 条的程序相比，47 道题的公开成果省 60 条，另由独立搜索在第 697 题省 2 条。两份候选均已重放；与 23:31 官方榜首 128,330 相差 5,783 条。另在 47 道题各证明了一条新的下界，全题已复核下界为 **37,968**。[公开程序的逐题来源](collaboration/frontier-134285/roman-134125/README.md) · [独立新增方案](collaboration/synthetic-temporary-targets/README.md) · [证明汇总](collaboration/evidence/combined-membership.json)


## 北京时间 11 月 20 日 23:37

公开辅助候选降到 **134,175**。第 271 题由 39 条降至 38 条，本地重建程序与 E-Max AI 的发布结果和 Asterios 收录的版本完全一致。第 791 题再省两条，到 135 条。独立候选为 **140,694**。按 23:31 榜首 128,330 计算，还差 5,845 条。五道外部证明均已复核，全题下界提高到 **37,921**。[公开版本与行署名](collaboration/frontier-134285/asterios126-audit.json) · [合并证明](collaboration/evidence/combined-conditioned-external.json)


## 北京时间 11 月 20 日 23:31

独立解在 19 道题共省 28 条，已降到 **140,694**。与公开辅助候选合并后，第 492、809、919 题分别少 1、2、1 条，公开辅助总数 **134,178**。所有候选均已重放。[完整实验](collaboration/temporary-targets/README.md)


## 北京时间 11 月 20 日 23:19

第 64 题由 112 条缩短到 111 条，公开辅助候选 **134,182**，独立候选 **140,722**。四个可署名输入在本机重新搜索后得到该解。第 362 和 501 题原有程序更短。[三道题的复核](collaboration/frontier-134285/retained/README.md)


## 北京时间 11 月 20 日 23:13

Asterios Panoras 的第 125 版收录了重跑 Atakan Aldemir 优化器所得的第 791 题。该题从 148 条减为 137 条，公开辅助候选更新为 **134,183**，较 23:11 的官方榜首 128,330 多 5,853 条。两套解释器均已验证。独立候选仍为 **140,722**。[逐题贡献与原始版本](collaboration/frontier-134285/asterios125-audit.json)


## 北京时间 11 月 20 日 23:05

GoodPJW 第 11 版的完整导出为 134,203 条。逐题与原有解比较，67 道题共省 91 条，公开辅助候选降至 **134,194**；两套解释器重放了全部 1,000 题。独立候选为 **140,722**。按 22:57 官方榜首 128,330 对照，差 5,864 条。两份候选均为本地成绩。[逐题缩短与校验](collaboration/frontier-134285/good11-audit.json) · [上游作者](collaboration/frontier-134285/good11-origins.csv) · [本轮独立对照](collaboration/target-partition/README.md)


## 11 月 20 日两种搜索的执行次序

独立程序 **140,727** 条，公开辅助程序 **134,298** 条，均已用两种解释器重放全部 1,000 题。独立试验的 4 题省 7 条，其中 0627 只有先用 Atakan 再用 Wang 才达到 115。公开辅助另外 4 题的父本均有署名，0079 是本地搜索得到的另一份同长程序。[执行次序与程序](collaboration/cross-method-order/README.md) · [公开源复现](collaboration/retained-pool/v42-audit.json) · [完整分数与逐题变动](collaboration/evidence/ordered-search-v42-merge.json)

## 11 月 20 日的多方法整题重放

独立文件达到 **140,734** 条，公开辅助文件达到 **134,303** 条。原版 Wang 增量搜索在新对照中改善独立 0228、0746 及公开辅助 0164。第 740 题用两份有署名的旧程序重建了 E-Max AI 的保留父本方法。另有 8 道独立题来自 Atakan 两个原版乘数搜索的复跑。所有成果以两种解释器逐题校验。[合并前后的逐题长度](collaboration/evidence/trajectory-frontier-merge.json) · [三种搜索的完整对照](collaboration/reactive-tabu/README.md)

## 11 月 20 日更新 Asterios 第 121 版

完整重放得到 134,316 条。相对上次发布的公开辅助文件，第 395、457、608、871 题各省 1 条，第 646 题省 2 条，合计达到 **134,305** 条。前四题在上游逐行署名 E-Max AI，第 646 题署名 Asterios Panoras 复跑 Atakan Aldemir 优化器。独立文件为 **140,745** 条。[固定来源、逐题回执及榜单](collaboration/evidence/asterios-v121-134305.json)

## 11 月 20 日第 506 题的公开改进

Asterios v120 汇总程序独立重放为 134,322 条。第 506 题由 117 条缩至 114 条，原始行署名 Asterios Panoras 重新运行 Atakan Aldemir 的优化器。合入已公布的 269 题搜索后，当前独立候选 **140,745** 条，公开辅助候选 **134,311** 条。21:52 的官方榜首为 128,330 条，相差 5,981 条。[固定版本、逐题作者及榜单](collaboration/evidence/asterios120-134311.json)

## 近长独立父本的扩展结果

首轮 16 道独立题后，预登记的另外 269 道中已完成 269 道，46 道刷新，合计节省 60 条。独立候选 **140,745** 条，公开辅助候选 **134,314** 条。两份均用两个解释器重放 1,000 题。[全部输入与筛选条件](collaboration/goodpjw-incremental/extension-design.json) · [逐批程序与署名](collaboration/goodpjw-incremental/extension)

## 11 月 20 日新公开程序的 50 题复验

在刚采用新公开程序的 50 道题上，单父本把第 147 题从 96 条缩到 94，多父本另把第 557 题从 109 条缩到 108。公开辅助候选共 **134,321** 条，已用两套解释器重放全部 1,000 题。独立候选 **140,805** 条。北京时间 21:45 的官方榜首是 128,330 条，差 5,991 条。[实测](collaboration/fresh-public-recombination/verification.json) · [逐题作者](collaboration/fresh-public-recombination/shorter.origins.csv) · [官方榜单对照](collaboration/evidence/rank-134321.json)

## 11 月 20 日独立候选缩短 6 条

在只使用独立生成程序的 16 道分层选题中，第 180 题 89→87、第 225 题 119→117、第 429 题 121→120、第 927 题 124→123。五组同预算对照的逐题最短合计得到 **140,805** 条，完整双重回放已通过。搜索方法向 Wang Jakie、GoodPJW 及 E-Max AI 署名。公开辅助文件仍为 **134,324** 条。[逐题实测](collaboration/goodpjw-incremental/independent-results.json) · [四行程序](collaboration/goodpjw-incremental/winners.csv)

## 11 月 20 日公开辅助候选缩短 61 条

独立候选为 **140,811** 条，公开辅助候选为 **134,324** 条。新公开版本缩短 50 道题，共 60 条，采用 Asterios v119 的 11 道、Hanif v24 的 10 道及 GoodPJW v10 的 29 道。另外，第 152 题组合旧父本和 Rudolph v67，从 115 缩短到 114。两份候选均经两种解释器重放全部 1,000 题。[公开来源与逐题改进](collaboration/evidence/four-source-134325.json) · [第 152 题的父本消融](collaboration/affine-elimination/control-origins.json)

21:35 官方榜首为 128,330 条。此时有 120 队的成绩优于本地候选，1 队同分，相距榜首 5,994 条。尚未提交 Kaggle。[榜单对照](collaboration/evidence/rank-134324.json)

## 跨初值模板对照完成

从 40 道练习题重建合法程序并抽取短算式，再绑定到其他题目的初始值。24 道练习留出题中，高频与低频模板在同一道题各省 1 条；12 道计分题均未进一步缩短。对第 199 题，三个模板确实能产生目标数，但每个目标在原解中只占一条独享运算，直接替换会使整题变长，已结束这条路线。[冻结输入、三臂对照与程序复验](collaboration/cross-puzzle-templates/README.md)

## 11 月 20 日协作分支的程序改进

复用其他开发者在 `optimize/shared-recipe-portfolio` 发布的实现，独立解的第 680 题从 211 降到 210，第 324 题从 187 降到 186。与主线合并后，独立候选 **140,811** 条，公开辅助候选 **134,385** 条。两份文件均经两套解释器完整回放。两条路线相对暂停时分别减少 627 和 692 条。[来源、对照和两道程序](collaboration/shared-recipe-branch/README.md)

21:22 的官方榜首为 128,330 条，129 支已排名的队伍优于本地公开辅助候选，0 队同分；若插入该快照约第 130 名。两项公开辅助全量对照已经完成，未找到更短的程序。[官方快照对照](collaboration/evidence/rank-134385-2122.json)

## 11 月 20 日新增四题并同步协作分支

公开辅助候选 **134,385** 条。第 148 和 855 题来自 Asterios 第 118 版，第 695 和 752 题来自 Alex Chilton 发布的 Rudolph 第 67 版，各省 1 条。后者按发布版保留署名，来源未按题区分原作者。与暂停时相比，401 道题缩短 692 条；纯独立候选 140,813 条也已完整重放。21:07 的榜单快照中有 120 支队伍领先、0 支同分，距榜首 128,330 条还有 6,055 条。[逐题署名](collaboration/evidence/four-source-134385-origins.csv) · [复核证明](collaboration/evidence/four-source-134385.json) · [榜单对照](collaboration/evidence/rank-134385.json)

远端独立开发分支已发布四次算法更新。其最新提交 e24a8e5 根据当前程序和备用程序的共同结构筛选算式；新试验将该实现直接用于独立 140,813 父本，先在两组各 32 题上与单父本比较。公开清单已列明本次使用的全部题号。[分支源码](https://github.com/Hansen0223/Santa_2026/tree/e24a8e5557434d2a2022fc7c9873e71aab148661) · [分组和父本指纹](collaboration/evidence/scc-fresh-design.json)

## 11 月 20 日两条路线的逐题净改进

与暂停时的提交逐行比较，1,000 题里独立解有 **327 题**缩短，合计从 141,438 降至 **140,813**；公开辅助有 **400 题**缩短，从 135,077 降至 **134,389**。净省最多的是独立第 177 题（12 条）和公开辅助第 807 题（16 条）。每一题均保留当时和当前两个版本中较短的可行程序。[前后文件指纹及逐题最大改进](collaboration/evidence/evening-134389.json) · [当前协作分工](collaboration/STATUS.md)

21:07 再查官方榜单，前方有 120 支已排名的队伍，按本次快照插入约第 121 名，榜首仍为 128,330 条。[21:07 排名对照](collaboration/evidence/rank-134389-2107.json)

## 11 月 20 日扩展独立父程序搜索

独立候选继续降到 **140,814** 条。选出的 54 道题合计省 65 条，3 条也缩短公开辅助候选，后者为 **134,389** 条。与暂停时相比，两条路线分别减少 624 条和 688 条。20:59 的榜单中，117 支队伍优于当前公开辅助结果，零队同分；本地候选距榜首 6,059 条。[入选程序的输入与复核](collaboration/annealing/README.md) · [逐题上下界](collaboration/puzzle-bounds.csv) · [各方法与来源总览](collaboration/evidence/search-portfolio-20261120.json)

## 11 月 20 日 21 时外部证明复核完成

**140,879** 条独立候选与 **134,392** 条公开辅助候选均通过两套解释器重放。单一与多个独立父程序的同预算比较，在 29 道题共省 35 条，其中 6 条也刷新公开辅助总长。20:59 的榜首为 128,330 条，本地公开辅助候选相差 6,062 条。按该快照插入约第 118 名。[双父本对照](collaboration/annealing/own-portfolio160.json) · [完整候选逐题计数](collaboration/puzzle-bounds.csv)

其他开发者提交的 16 个新预算判定已全部独立复核，239 个分片的 1,927,093,004 个节点逐片吻合。全题合并下界提高到 **36,767** 条，已有 **20 道题**达到最短。公开的分工工具现在也会跳过其他人已发到仓库、正在等待本地复验的预算。[复核收据](collaboration/evidence/upstream-35c63e8.json) · [协作分工](collaboration/STATUS.md)

## 11 月 20 日选题的前瞻检验

公开辅助候选 **134,398** 条，独立候选 **140,914** 条。对 200 道事先冻结的题使用同一搜索预算，预测优先组与长度匹配组分别省 2 条、1 条，均保留改进并完整回放。按北京时间 20:59 的官方快照插入本地候选，117 支队伍优于这一成绩、0 队同分，约第 118；距榜首 128,330 条还有 6,068 条。[试验分组与结果](collaboration/annealing/README.md) · [对照榜单](collaboration/evidence/rank-134398.json)

## 11 月 20 日独立搜索扩展

独立候选 **140,914** 条，公开辅助候选 **134,401** 条，两份都已全量回放。对余下 170 道近期缩短的独立题组合四种局部改写，和当时的整表逐题合并后，有 12 题净省 23 条，其中一条也继续缩短公开辅助候选。从官方初值生成的 0048、0324 和 0680 已补齐从零编译和重放的小包。[改写实验](collaboration/wang-polish/README.md) · [从零生成复现](collaboration/official-heads/README.md)

第 882 题原本达限的 (11, 4) 分片已完整排除，整题仍在 22–23 条之间。另外已检查 20:49 榜单前 24 支队伍合计 29 名成员的公开数据集目录，在此次检索范围内未发现本届比赛的新数据集。[分片回执](collaboration/puzzle-0882-diversity/h10-cell-11-4.json) · [公开目录检索范围](collaboration/evidence/public-catalog-top24.json)

## 11 月 20 日留出题与配对比较

当前独立解 **140,937** 条、公开辅助解 **134,402** 条。独立线在前一版基础上，0048 和 0324 合计再省 5 条，另外两道留出题 0741 和 0890 各省 1 条。0048 仅用普通生成器启动及同样的后续改写也能获得 153 条。0324、0680 在这组实验中通过随机挑选、按成本生成辅助值取得改进。[重新生成的逐题对照与结果](collaboration/evidence/random-dictionary-results.json) · [冻结留出题](collaboration/wang-polish/README.md)

在有过近期改进的题上再搜索，0186、0427、0923、0985 各缩短一条。与上一份公开辅助提交相比总计省 4 条。按官方榜单快照比较，有 113 支队伍优于这份本地候选，0 队同分，距榜首 128,330 条还有 6,072 条。[父本、算式和验证](collaboration/annealing/active-pairs.json) · [排名对照](collaboration/evidence/rank-134402.json)

## 11 月 20 日多样性搜索及第 117 版

独立候选已降到 **140,944** 条，公开辅助候选降到 **134,406** 条。前一份已发布的 140,000 级独立表为 141,026，保持不同形态算式的搜索在 65 题省 80 条，另有两道独立题 0324 和 0680 各省 1 条。后两题的程序从官方初值重新生成，使用随机挑选的低成本辅助数作为开头，所有辅助数的生成成本均计入结果。[独立退火核验](collaboration/annealing/independent105.json) · [从零生成路线的逐题程序](collaboration/evidence/random-dictionary-wins.csv)

公开辅助线合并第 117 版时，5 道题使 134,414 再减 6 条。四种改写的 48 题开发对照在早先冻结的父本上省了 6 条，其中 2 条继续缩短当前候选。两份整表均经过两套解释器实际回放。[第 117 版记录](collaboration/evidence/release-v117.json) · [各题上游作者](collaboration/evidence/asterios-v117-sources.csv) · [四种改写](collaboration/wang-polish/README.md)

北京时间 20:49 的官方快照里，114 支已排名的队伍优于 134,406，0 队同分。按该快照插入约第 115，距榜首 128,330 还有 6,076 条。[排名计算](collaboration/evidence/rank-134406.json)

## 11 月 20 日公开版本更新

公开辅助候选为 **134,430** 条，比上一版的 134,456 条再省 26 条，独立候选为 **141,026** 条。21 个改进的题中，8 题采用 Asterios 第 115 版，8 题采用 Hanif 第 23 版，其余 5 题来自本地退火。Rudolph 第 65 版中更短的行已由其他来源覆盖。两套解释器均已重放全部 1,000 题。[合并回执](collaboration/evidence/release-union-134430.json) · [逐题署名](collaboration/evidence/release-union-134430-origins.csv) · [Hanif 原始声明](public-assisted/Hanif-v23-NOTICE.md)

北京时间 20:29 的官方榜单有 1,782 支已获排名的队伍，其中 119 队优于 134,430 条，0 队同分。按该快照插入约第 120，比榜首 128,330 条多 6,100 条。此为本地结果的对照，尚未提交 Kaggle。[快照及排名口径](collaboration/evidence/rank-134430.json)

## 11 月 20 日第二轮整表退火

纯独立候选从 141,240 降到 **141,026**，154 道题共省 214 条。将独立解和有逐题授权来源的公开搜索结果合并后，公开辅助候选从 134,487 降到 **134,456**。两套解释器均已重放两份完整候选。20:18 的榜首为 128,330，相差 6,126 条。[复跑和归属](collaboration/annealing/README.md) · [两条路线逐题结果](collaboration/puzzle-bounds.csv)

## 2026 年 11 月 20 日 · 晚间恢复

独立候选为 **141,240 条**，公开辅助候选为 **134,487 条**。相比暂停时，分别省 198 和 590 条。20:04 的官方榜首是 128,330 条，相差 6,157 条。两份候选均由两套解释器重放 1,000 道题。[逐题结果](collaboration/puzzle-bounds.csv) · [官方榜单快照](collaboration/leaderboard.json)

Asterios 第 113 版原始总长 134,508 条；与暂停时相比，354 题合计省 569 条。先保留已有上界和署名，再逐题采用更短程序。对这 354 题重新优化又有 7 题各省 1 条。独立父程序使用 Wang Jakie 的模拟退火后，150 道题共省 194 条。[公开版本记录](collaboration/evidence/release-v113.json) · [模拟退火对照](collaboration/annealing/README.md)

协作者提交的 20 项新下界经 544 个分片、205,599,815 个节点复核，合并下界从 36,731 升至 **36,751**。第 149 题已有 16 条程序，已证最短。第 882 题第五档 15,504 种组合均已排除，若存在 22 条解，10 个辅助值中至少 6 个不在五份已知程序的 20 个辅助值中；整题仍为 22 至 23 条。[外部证明](collaboration/evidence/upstream-d642a22.json) · [第 882 题第五档](collaboration/puzzle-0882-diversity/five-new.md)

## 2026 年 11 月 20 日 · 18 题同预算对照

独立 **141,438 条**，公开辅助 **135,077 条**。两份均已回放 1,000 题。用相同的随机种子和轮数比较，在 18 道题上单父本、双父本各胜 1 题，另 16 题平局。择短后，独立第 29 题从 40 降到 39 条，第 84 题从 44 降到 43 条。14 道题上另试了允许更多候选整数的布尔约束求解，42 次均未得到确定判定。[逐题对照与复跑](collaboration/short-program-comparison/README.md)

优化已暂停。第 882 题第五档共 15,504 组，已排除 15,503 组，尚余索引 482。整题边界仍为 22 至 23 条。[各题的暂停进度](collaboration/evidence/ongoing-at-checkpoint.json)

## 2026 年 11 月 20 日 · 复用寄存器的 10 题对照

独立候选为 **141,440 条**，公开辅助候选为 **135,077 条**。在此前短题筛查之外的 10 道题上，每道题给两种来源各 96 轮。仅重排原程序没有缩短；搜索新算式后，第 541 题独立从 55 条减至 54 条，第 773 题公开辅助从 43 条减至 42 条。两个结果分别使用 24 和 18 个寄存器。[逐题结果、对照和复现](collaboration/register-search/README.md)

## 2026 年 11 月 20 日 · 重建共享中间值

独立方案为 **141,441 条**，公开辅助方案为 **135,078 条**。与 15:37 的两份文件相比，分别在 26 和 20 题共省 34 和 28 条。正式得分文件对全部 1,000 题使用两套解释器回放。当前用作比较的 Asterios 第 99 版原始总长是 135,761 条。[逐题上下界](collaboration/puzzle-bounds.csv) · [逐题公开署名](public-assisted/origins.csv)

针对多个后续操作共用的整数，先精确求解这些整数的构造，再将算式装回整题。第 649 题前段从 29 条变为 28 条，后段 90 条算式逐条相同。第 25 题在保留大部分原辅助数的条件下，从 124 条减为 123 条。第 134 题从三个独立程序中共同选算式，从 29 条减至 28 条。对得到的新程序再做成组搜索，达到 27 条。第 517 题先从 141 条降到 140 条，接着成组搜索和全程序替换各省一条，最终为 138 条。[第 649 题验证](collaboration/exact-boundary/README.md) · [第 25 题与精确搜索档案](collaboration/window-search/README.md) · [第 134 题消融对照](collaboration/three-parents/README.md)

从官方初始值和独立父本重新组合算式，第 711 题由 22 条缩至 21 条，第 250 题由 23 条缩至 20 条，第 387 题由 24 条缩至 23 条，第 818 题由 23 条缩至 21 条。[第 711 题的生成器与回放](collaboration/puzzle-0711/README.md)

在另外 80 道短题上各搜索 350 轮后，10 道独立程序合计再省 12 条。第 19、393、401 题各比此前公开辅助程序少 1 条，第 455 题少 2 条，两份候选均已采用这些独立生成的算式。[80 个父本、10 道改进和复现方法](collaboration/puzzle-0711/wide/README.md)

第 882 题的整题上下界仍为 22 至 23 条。五份独立父本用过 20 个不同辅助值；若存在 22 条的解，其中至少五个辅助值必须来自这 20 个整数之外。最近一档指定六个旧辅助值，并允许再选任意四个辅助值，38,760 种组合全部无解。[完整条件证明](collaboration/puzzle-0882-diversity/README.md)

## 2026 年 11 月 20 日 · 第 99 版公开算式与多父本重组

独立候选 **141,474 条**，公开辅助候选 **135,087 条**。Asterios 第 99 版原始总长 135,761 条，与原候选逐题比较，11 题合计省 17 条，使总长降至 135,089 条。对新版本变动的 30 题再做改写，第 72 题从 104 降至 103，第 929 题从 110 降至 109。第 72 题只使用新公开父本，第 929 题同时使用新旧父本。每份完整文件都通过两套解释器的 1,000 题重放。[上游版本与逐题来源](collaboration/evidence/release-v99.json) · [实验记录](collaboration/evidence/sibling-experiments.json)

独立第 134 题由 29 条缩至 28 条。用当前程序分别和两份历史独立程序组合，都只能得到 29 条；三份程序共同提供可选算式时得到了 28 条。该结果是可行上界。[逐题上下界](collaboration/puzzle-bounds.csv)

反推一对能同时生成两个输出的操作数，在 96 个专门构造的例子中均能省一步。扩大搜索后，64 道真实留出题的两份父本均无收益。用其他题生成过的小整数重写同一程序的多个目标，在留出组和另外挑选的辅助数较多的程序段中也没有缩短。后续转向对这些程序段本身做有明确范围的精确重建。[已试范围](collaboration/evidence/sibling-experiments.json) · [当前分工](collaboration/STATUS.md)

## 2026 年 11 月 20 日 · 公开协作快照

独立候选 **141,475 条**，公开辅助候选 **135,106 条**。从当天 14:42 的冻结程序起，两条路线分别在 132 题和 40 题省下 194 条和 55 条。已用两套解释器重放全部 2,000 行程序。北京时间 15:23 的官方榜首为 128,831 条。两份本地候选均尚未提交 Kaggle。[当前开发进度](collaboration/STATUS.md) · [榜单记录](collaboration/leaderboard.json)

第 334 题的一处新分解少用了 3 个辅助数，独立程序从 249 条降到 246 条。近期已有改进的 131 道独立题，串行运行不同改写方法共省 18 条，其中 6 条来自在前一方法的结果上继续搜索。另抽取此前程序未变的独立、辅助题各 48 道，独立省 1 条，辅助持平，两组均未出现超过最佳单法的串行收益。[因数分解复现](collaboration/factor/README.md) · [组合改写案例](collaboration/polish/) · [方法及对照](collaboration/methods.md)

与仓库 fde4f22 的最新 27 份证明逐片核对后，远端已证下界 33,668 全部被本地逐题证明覆盖。当前可核对的全题下界为 36,731，有 19 题已达下界。第 882 题已证至少 22 条，现有 23 条的可行程序，22 条的完整搜索仍在进行。[分片与证书](collaboration/proof-status.md)

截至 **2026 年 11 月 19 日暂停时**，本地最好候选为 **137,442 条指令**。当日北京时间 21:38 记录的 Kaggle 榜首为 **130,600 条**，相差 **6,842 条**。两个候选均已重放全部 1,000 题，均未提交 Kaggle，目前没有官方名次。计分越低越好。[榜单快照](work/leaderboard.json) · [官方排行榜](https://www.kaggle.com/competitions/santa-2026/leaderboard)

| 候选 | 程序来源 | 已验证指令数 | 逐题记录 |
| --- | --- | ---: | --- |
| [独立求解](submission.csv) | 求解器从官方初值和目标生成算式，并在本地逐题改写、择优 | 146,435 | [验证结果](result.json) · [每题采用的来源](origins.csv) |
| [公开辅助](public-assisted/submission.csv) | 合并公开许可的算式、本地独立解及对这些算式的改写 | 137,442 | [验证结果](public-assisted/result.json) · [逐题署名](public-assisted/origins.csv) |

与此仓库上一次发布的结果相比，公开辅助候选从 138,845 条降至 137,442 条，减少 1,403 条。独立候选从 172,469 条降至 146,435 条，减少 26,034 条。旧版代码和练习集记录可在此前的提交中查阅。[上一次发布的检查点](https://github.com/Hansen0223/Santa_2026/tree/cb565d787be6b6d0055fea6aa1d9cf484b5558da)

独立求解使用的部分求解器代码来自公开实现，相关作者、版本和本地修改记在[求解器来源声明](generative/NOTICE.md)。公开辅助版本中的 856 题直接采用 Asterios 第 13 版的程序，92 题采用本地独立生成的程序，另 52 题采用进一步改写的程序。第 13 版原样重放共 138,356 条，最终组合少 914 条。Kaggle 下载版本号为 13，压缩包内作者变更表的末条标记为 v11。[公开汇总固定版本](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/13) · [原版变更表](public-assisted/Asterios-history.csv) · [许可及上游出处](public-assisted/NOTICE.md)

## 哪些方法带来了改进

第 `scored_0006` 题从 16、29、33 出发，要算出 32 个目标。目标中的 68,324,209,308 和 68,324,209,381 可以写成同一个平方 261,389² 分别减 13、加 60。继续检查其余目标，可以用 **261,389、327,190、571,027、835,418** 四个整数解释全部 32 个目标，每个都有 `k × a × b + r` 的表示。先构造多个目标共用的整数，便有机会少做运算。比较候选时仍然计入从初值构造这四个整数的成本。这一题当前独立解为 **118 条**，公开辅助解为 **112 条**。[结构识别](solvers/matrix/matrix_scan.py) · [算式构造](solvers/matrix/matrix_construct.py)

对其余题，每个目标通常有多条可行计算路径。把几份程序中的计算路径放在一起，检查去掉某个中间值后是否仍能从初值到达全部目标，可以保留共同需要的运算，删去同一题内的重复工作。选出更短的计算图之后，再排入 48 个寄存器并重放。下表摘取独立求解的几个检查点，同一轮可能合并多种方法的结果。[计算图求解](generative/component_select.py) · [全部 29 次检查点及逐轮收益](result.json)

| 北京时间（11 月 19 日） | 当时的独立指令数 | 该轮记录的部分改进 |
| --- | ---: | --- |
| 19:19 | 155,612 | 合并多种求解器生成的候选 |
| 20:53 | 150,114 | 恢复共同乘法结构后重构程序，两组结构候选分别贡献 636 和 155 条降幅 |
| 21:11 | 148,665 | 按依赖关系拆分后选择可共用的计算，该项在此轮贡献 224 条 |
| 21:30 | 147,052 | 把结构识别得到的等式纳入选择，并试删可替换的中间值 |
| 21:44 | 146,435 | 合并成组删减等候选，其中成组删减比上一检查点再省 124 条 |

## 可验证的范围

两套整数解释器对每条指令检查操作数是否存在、整除是否精确、结果是否落在题目值域内，以及程序是否覆盖全部目标。提交文件、对应输入和输出哈希保存在验证记录中。取得官方数据后，可以在普通 CPU 上重放最终成绩。重跑完整优化过程还需要各阶段的候选池、编译器及部分方法使用的求解库和 GPU 环境。[复核命令与依赖](README.md#校验与复跑) · [第一套解释器](elf.py) · [独立复核实现](checkpoint.py)

截至 11 月 19 日已证明 **16 道计分题** 达到最少指令数，合计 **57 条**。全体 1,000 题可证明的总下界是 **33,331 条**，距离当前可行解仍远，全局最优尚未证明。逐题证书中的可行解长度对应生成证书时的旧快照，下界由官方题目本身决定。[逐题证书](work/virtual/certificates.csv) · [证书对应的输入哈希](work/virtual/certificates.json) · [下界计算](lower_bounds.py)

暂停时，提取共享常数后分别求解子题的试验仍只覆盖了部分题目。在小整数值域内精确选择中间值的实验也已产出逐题候选，尚待合并。上表与两份提交只统计暂停前已完成全量重放并正式合并的结果。

## 11 月 20 日 · 最短性证明

对 `scored_0892`，已穷尽不超过 15 条指令所对应的全部辅助数选择。34 个分片全部无解，现有 16 条程序完成八个目标，因此最短长度为 16。已证最优的计分题增至 17 道。全体下界从 33,331 提高到 33,586，公开辅助提交仍为 137,442 条。[证明方法与复核命令](proofs/README.md) · [逐题上下界](proofs/bounds.csv)
