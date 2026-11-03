# Ecosystem Map — 医械全生命周期 11 环节 × lgd-engine 适配器族

> ⑬ 产出：产业环节全景映射。每环节判定逻辑来源标注到已核验判例集 / 案例库 / 监管数据库；禁止凭空造规则。
> 状态图例：✅ MVP 已实现 · 🟡 路线图 P0（下一迭代） · ⚪ 路线图 P1/P2

## 11 环节总表

| # | 环节 | FDA 监管要点 | NMPA 监管要点 | EU MDR / IMDRF | 适配器包名 | 状态 |
|---|---|---|---|---|---|---|
| 1 | 设计开发 (Design & Development) | 21 CFR 820.30 设计控制；Design History File (DHF) | 《医疗器械生产质量管理规范》设计开发章节 | MDR Art.10(3) + GSPR；IMDF/IMDRF SaMD | `judge_design_controls` | ⚪ P2 |
| 2 | 注册申报 (Premarket Submission) | 510(k) / PMA / De Novo / Q-Sub；21 CFR 807.81 | 注册证 / 备案；《注册与备案管理办法》(47号令) | MDR Art.52 符合性评估 + Notified Body | `judge_reg_dossier` | 🟡 P0 |
| 3 | 临床评价 (Clinical Evaluation) | 21 CFR 860/812 IDE；Clinical Investigation | 《医疗器械临床评价技术指导原则》 | MDR Art.61 + MDCG 临床评价指南 | `judge_clinical_eval` | ⚪ P1 |
| 4 | 生产质量体系 (QMS / GMP) | 21 CFR 820 QSR；ISO 13485 对齐 | 《医疗器械生产质量管理规范》+ 现场检查 | ISO 13485:2016 + MDR Art.10(9) | `judge_qms_gmp` | ⚪ P1 |
| 5 | 上市后监管 (Postmarket Surveillance) | 21 CFR 803 MDR；21 CFR 806 Corrections & Removals | 《医疗器械召回管理办法》一/二/三级 | MDR Art.83/84 PMS + Vigilance | `judge_postmarket` | ✅ **MVP 已实现**（本 MVP） |
| 6 | 警戒/不良事件 (Vigilance / Adverse Event) | MAUDE 数据库；Class 1/2/3 recall | NMPA 不良事件监测 + 召回公告 | MDR Art.87/88 严重 incident 报告 | `judge_postmarket`（与 #5 合并） | ✅ **MVP 已实现** |
| 7 | 变更控制 (Change Control) | 21 CFR 807.81(a) 显著变更；Special/Traditional 510(k)；PMA supplement | 《注册与备案管理办法》变更注册 vs 登记事项 | MDR Art.10 — substantial change → re-assessment | `judge_510k_change` | ✅ **MVP 已实现**（本 MVP Demo1） |
| 8 | UDI (Unique Device Identification) | 21 CFR 830；GUDID 提交 | 《医疗器械唯一标识系统规则》 | MDR Art.27 + UID database (EUDAMED) | `judge_udi` | ⚪ P1 |
| 9 | 标签 / IFU (Labeling & IFU) | 21 CFR 801 通用标签；21 CFR 809 IVD 标签 | 《医疗器械说明书和标签管理规定》 | MDR Annex I Ch.2 — IFU/label | `judge_label_ifu` | ⚪ P1 |
| 10 | SaMD 软件 (Software as a Medical Device) | 21 CFR 820.30(g) 设计变更；PCCP 指南；AI/ML Action Plan | 《人工智能医疗器械注册审查指导原则》 | IMDRF SaMD risk categorization; MDR Art.17 | `judge_samd` | ⚪ P0（B1 案例库 7/14 是 SaMD） |
| 11 | 退役 (End-of-Life / Discontinuation) | 21 CFR 806 discontinuance；GUDID 下架 | 注册证注销（如 B1-C01 商汤 2025年第15号） | MDR Art.10(8) — discontinuation notice | `judge_retirement` | ⚪ P2 |

## 判定知识来源纪律

每环节规则必须绑定到以下已核验来源之一，禁止凭印象造规则：

- **P2 判例集（10 例 VERIFIED，2026-11-03）**：`P2_医械变更判例分级样本集_20261103.md`
  - 支撑：#7 变更控制（4 RED + 3 YELLOW + 3 GREEN 阈值）、#5/#6 召回分级映射
- **B1 案例库（14 例 VERIFIED，2026-11-03）**：`B1_case_library_expanded_20261103.md`
  - 支撑：#5/#6 警戒（B1-C02/C04/C08/C09/C11/C12/C14）、#10 SaMD（7/14）、#11 退役（B1-C01/C06/C07/C12）、#2 无许可上市（B1-C05/C07）
- **FDA 公开数据库**：510(k) 库（accessdata.fda.gov/cdrh_docs）+ Recall DB（res.cfm）
- **NMPA 公开公告**：召回公告页 + 注册证查询
- **法规条款原文**：21 CFR 807.81 / 820.30 / 803 / 806 / 830；NMPA 47 号令；MDR 2017/745 条款

> 没有精确条款原文时，规则注释必须标注「依据公开法规要点，条款号以官方文本为准」。
