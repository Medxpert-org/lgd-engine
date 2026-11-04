# 适配器路线图（已实现 2 个 / 待建 9 个）

> ⑬ 产出：环节 × 监管依据 × 判定逻辑来源 × 优先级 × 依赖数据 × 工作量。

| 环节 | 适配器 | 监管依据（公开法规事实） | 判定逻辑来源 | 优先级 | 依赖数据 | 工作量 |
|---|---|---|---|---|---|---|
| #7 变更控制 | `judge_510k` | 21 CFR 807.81(a)；NMPA 47号令 | P2 判例集 10 例 | ✅ **已实现** | P2 判例集 | — |
| #5/#6 上市后+警戒 | `judge_postmarket` | 21 CFR 803/806；NMPA 召回办法 | B1 案例库 7 例召回 + P2 4 例 Class 1 | ✅ **已实现** | B1 + P2 召回记录 | — |
| #2 注册申报 | `judge_reg_dossier` | 21 CFR 807 subpart；NMPA 47号令；MDR Art.52 | B1-C05/C07 无许可上市反例 | **P0** | FDA 510(k) DB、NMPA 注册证查询 | M |
| #10 SaMD | `judge_samd` | FDA PCCP 指南；IMDRF SaMD；NMPA AI 指导原则 | B1 案例库 7/14（C02/C04/C06/C09/C10/C11/C12/C14） | **P0** | B1 SaMD 子集 + PMC12274014 统计 | M-L |
| #3 临床评价 | `judge_clinical_eval` | 21 CFR 860/812；MDR Art.61 | 待补：临床评价案例 | P1 | 临床评价文献 | M |
| #4 QMS/GMP | `judge_qms_gmp` | 21 CFR 820；ISO 13485；GMP | P2 MAJ-01 过程变更失控反例 | P1 | FDA 483/警告信数据（待接） | L |
| #8 UDI | `judge_udi` | 21 CFR 830；GUDID；NMPA UDI 规则 | 待补 | P1 | GUDID API（公开） | S |
| #9 标签/IFU | `judge_label_ifu` | 21 CFR 801；NMPA 标签规定；MDR Annex I Ch.2 | P2 MIN-01/02/03 标签修正 3 例 | P1 | P2 MIN 子集 | S |
| #1 设计开发 | `judge_design_controls` | 21 CFR 820.30；ISO 13485 §7.3 | P2 MAJ-04 设计缺陷反例 | P2 | 设计历史文件样例（待脱敏） | M |
| #11 退役 | `judge_retirement` | 21 CFR 806 discontinuance；NMPA 注册证注销 | B1-C01/C06/C07/C12 退役 4 例 | P2 | B1 退役子集 | S |

## 优先级说明

- **P0**（下一迭代必做）：#2 注册申报（reg-dossier）、#10 SaMD —— 这两块案例库覆盖最厚（B1 14 例里 9 例相关），也是现行判据最密集、最容易验证的两块。
- **P1**（3-6 个月）：临床评价、QMS、UDI、标签 —— 规则相对稳定，可快速复用现有 judge 骨架。
- **P2**（6 个月+）：设计开发、退役 —— 案例薄，需先补案例。

工作量量级：S = 1-2 天；M = 3-5 天；L = 1-2 周。
