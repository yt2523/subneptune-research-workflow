# 实验与论文复现 / Experiments and paper reproduction

从 [首个论文复现](huang2022-fig4/README.md) 开始。它核对 Huang、Rice 与 Steffen (2022) 图 4 的默认双层模型。

- [结课实验原始归档](archive/20261018/capstone/README.md)：300/1000 K 温度对照及容差敏感性。
- [亚海王星构成原始归档](archive/20261018/literature-cases/README.md)：16 组运行，包括收紧容差、气体 EOS 对照及被标记的蒸汽试算。这些是文献配方试算，不是原论文的完整复现。
- [归档 SHA256 清单](archive/20261018/inventory.json)：117 个文件，保留原配置、脚本、日志、数据、报告、PNG/SVG/PDF。只排除网站发布压缩包和部署元数据；不上传编译二进制、缓存、虚拟机磁盘或账户信息。

论文复现及全部原始数值都在这个分支；科学求解器源码未改动。原始归档里的脚本和配置保留当时的 D 盘绝对路径，用下方入口可在其他 Ubuntu 路径重跑。

## 在 Ubuntu / WSL 重跑

仓库需要 g++、make、GSL 开发文件、Python 3。运行和验证只用 Python 标准库；绘图另外需要 NumPy/Matplotlib。

```bash
cd /mnt/d/GPT/projects/Sub-Neptune/Magrathea
PYTHONDONTWRITEBYTECODE=1 python3 experiments/huang2022-fig4/reproduce.py \
  --output /mnt/d/GPT/projects/Sub-Neptune/outputs/huang2022-rerun-001
python3 experiments/huang2022-fig4/verify.py \
  /mnt/d/GPT/projects/Sub-Neptune/outputs/huang2022-rerun-001

# 回放之前的某个配置；省略 --case 则回放该组全部配置。
PYTHONDONTWRITEBYTECODE=1 python3 experiments/replay.py capstone \
  --case baseline_300K --output /mnt/d/GPT/projects/Sub-Neptune/outputs/capstone-replay-001
PYTHONDONTWRITEBYTECODE=1 python3 experiments/replay.py literature-cases \
  --case water30 --output /mnt/d/GPT/projects/Sub-Neptune/outputs/water30-replay-001
```

每次指定尚不存在的输出目录。原程序会追加剖面，入口会拒绝覆盖旧目录。数值状态为 0 不足以判断 EOS 选支和物理有效性；之前蒸汽试算与 Hycean 模型差异见归档说明。

## English

The first quantitative reproduction targets the default two-layer planet in Huang et al. (2022), Fig. 4. Historical capstone and literature-recipe experiments are archived without changing their raw results, including flagged trials. Their original scripts/configs retain historical absolute paths; `replay.py` rewrites only the output path for portable Linux replay. Use a fresh output directory on each run. Diagnostic builds add read-only logging to a temporary copy of main.cpp; solver and EOS sources are unchanged. Model convergence alone does not certify physical validity.

- [Prescribed TP2026-10-28, audited2026-10-29](prescribed-tp-20261028/README.md): forward numerical comparison passed; recovery overallFAILED,8/20 fits, no inferred composition.

- [Stage4 reciprocal recovery](prescribed-tp-reciprocal-20261030/README.md): oneconditionalA→Blocal recoveryPASS; originaloppositedirectionFAILEDretained;6new/14cumulativefits,0newAPI.
