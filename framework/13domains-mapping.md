# 13 域判定器 → 11 环节适配器族映射

> ⑬ 产出：把现有 13 个 LGD 域与 11 环节适配器对齐，说明哪些直接对应、哪些需拆分/合并。
> 现有 13 域（按用户 profile 与已有 skill 体系列出）。

| # | 现有 13 域 | 对应 11 环节 | 处理方式 | 备注 |
|---|---|---|---|---|
| 1 | medical-device-clinical-evaluation | #3 临床评价 | **直接对应** | 未来实现 `judge_clinical_eval` |
| 2 | compliance-grader | 跨环节（合规总评） | **拆分为 #2+#5+#9 组合** | 不作为独立 judge，改为聚合报告 |
| 3 | label-ifu | #9 标签/IFU | **直接对应** | `judge_label_ifu` |
| 4 | postmarket | #5 上市后 + #6 警戒 | **合并为一个 judge**（本 MVP 已实现 `judge_postmarket`） | 召回等级 + 不良事件同判 |
| 5 | qms-gmp | #4 QMS/GMP | **直接对应** | `judge_qms_gmp` |
| 6 | reg-dossier | #2 注册申报 | **直接对应** | `judge_reg_dossier` |
| 7 | reg-hub | 跨环节（监管路由） | **合并到 GateEngine 的 jurisdiction 路由**（⑭） | 不作为 judge，改为辖区路由器 |
| 8 | risk-management | 跨环节（ISO 14971） | **拆为每个 judge 的 risk_impact 字段** | 不独立成 judge，作为输入维度 |
| 9 | samd | #10 SaMD | **直接对应**（P0 高优） | B1 案例库 7/14 是 SaMD |
| 10 | supplier-compliance | #4 QMS 子项 + #7 变更子项 | **拆分**：供应商资质走 QMS；供应商变更走 #7 变更控制（本 MVP 已含 supplier_substitution 分支） |
| 11 | techfile-sted | #2 注册申报（EU MDR 技术文档） | **合并到 reg-dossier 的 EU 辖区分支** | 不单列 |
| 12 | udi-validator | #8 UDI | **直接对应** | `judge_udi` |
| 13 | change-control | #7 变更控制 | **直接对应**（本 MVP `judge_510k`） | 已实现 |

## 映射结论

- **直接对应（10 个）**：clinical-evaluation, label-ifu, postmarket, qms-gmp, reg-dossier, samd, techfile-sted（并入 reg-dossier EU 分支）, udi-validator, change-control, supplier-compliance 拆半
- **合并/拆分（3 个）**：
  - `compliance-grader` → 降级为聚合报告，不再是独立 judge
  - `reg-hub` → 改为 GateEngine 的 `--jurisdiction` 路由（⑭已落地）
  - `risk-management` → 作为输入字段 `safety_impact` / `harm_severity`，不独立
- **新增环节**：#1 设计开发、#11 退役 在现有 13 域外，需新增 `judge_design_controls` / `judge_retirement`

行数：13 行映射表。
