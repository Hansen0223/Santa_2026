# 还原 128,501 条候选

本轮 700 道题共省 3976 条。[逐题来源与指纹](portfolio.json) · [上一版 132,477 条候选](https://github.com/Hansen0223/Santa_2026/blob/5b76ad0/public-assisted/releases/portfolio.md)

| 题号（节选） | 步数 | 改进来源 |
| --- | --- | --- |
| 182 | 143 → 118 | Ishan Karnick, Santa 2026 \| Frontier Programs \| 130,131 (programs read from the notebook code or its own dataset) |
| 932 | 226 → 203 | wilan, Santa 2026: Claude Coding \| LB: 128524 |
| 174 | 138 → 117 | wilan, Santa 2026: Claude Coding \| LB: 128524 |
| 759 | 196 → 175 | wilan, Santa 2026: Claude Coding \| LB: 128524 |
| 819 | 225 → 204 | wilan, Santa 2026: Claude Coding \| LB: 128524 |
| 203 | 214 → 194 | tkm2261, Sorry for my leakage!!! It’s all my AI’s fault! |
| 264 | 213 → 193 | wilan, Santa 2026: Claude Coding \| LB: 128524 |
| 328 | 228 → 208 | wilan, Santa 2026: Claude Coding \| LB: 128524 |
| 403 | 230 → 210 | wilan, Santa 2026: Claude Coding \| LB: 128524 |
| 208 | 226 → 207 | tkm2261, Sorry for my leakage!!! It’s all my AI’s fault! |
| 349 | 183 → 164 | wilan, Santa 2026: Claude Coding \| LB: 128524 |
| 594 | 224 → 205 | wilan, Santa 2026: Claude Coding \| LB: 128524 |

将官方题目保存为 `data/puzzles.csv`，将以下原件放入 `archives/`。

| 文件名 | 下载来源 |
| --- | --- |
| `asteriospanoras-370.zip` | [asteriospanoras-370](https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/370) |

在有 Git 历史的仓库根目录运行以下命令。

```sh
python -B public-assisted/releases/portfolio.py --puzzles data/puzzles.csv --archives archives --out combined
```

输出 `combined/submission.csv` 包含 1,000 道题，SHA-256 为 `e05fafed6121b06044b41e7ae7e9ebfdd693f4aa790bd312da868161510fb88e`。等长时保留清单中较早的来源。[仓库逐题署名](../origins.csv)
