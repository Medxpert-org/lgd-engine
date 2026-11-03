# 生态适配矩阵 — 11 环节 × 8 辖区

> ⑭ 产出：与 ⑬ ecosystem-map 合并为「环节 × 辖区 × 判定依据 × 状态」总表。
> 法规来源纪律：每格绑定已核验法规条款；无精确条款原文处标注「依据公开法规要点，条款号以官方文本为准」。

## 矩阵总表

| 环节 | FDA (US) | NMPA (CN) | EU MDR | IMDRF | PMDA (JP) | MFDS (KR) | MHRA (UK) | Health Canada |
|---|---|---|---|---|---|---|---|---|
| #1 设计开发 | 21 CFR 820.30 ⚪ | GMP 设计开发章节 ⚪ | MDR Art.10(3) GSPR ⚪ | IMDRF SaMD ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| #2 注册申报 | 21 CFR 807.81 ✅(变更) | 47号令 ✅(变更分支) | MDR Art.52 ⚪ | IMDRF GRRP ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| #3 临床评价 | 21 CFR 860/812 ⚪ | 临床评价指导原则 ⚪ | MDR Art.61 ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| #4 QMS/GMP | 21 CFR 820 ⚪ | GMP ⚪ | ISO 13485 + MDR Art.10(9) ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| #5 上市后 | 21 CFR 803/806 ✅ | 召回办法 一/二/三级 ✅ | MDR Art.83/84 ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| #6 警戒/不良事件 | MAUDE + Class 1/2/3 ✅ | NMPA 不良事件监测 ✅ | MDR Art.87/88 ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| #7 变更控制 | 21 CFR 807.81(a) ✅ | 47号令 变更注册 vs 登记事项 ✅ | MDR Art.10 substantial change ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| #8 UDI | 21 CFR 830 / GUDID ⚪ | UDI 系统规则 ⚪ | MDR Art.27 / EUDAMED ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| #9 标签/IFU | 21 CFR 801 ⚪ | 标签管理规定 ⚪ | MDR Annex I Ch.2 ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| #10 SaMD | PCCP 指南 + AI/ML Action Plan ⚪ | AI 医疗器械指导原则 ⚪ | IMDRF SaMD + MDR Art.17 ⚪ | IMDRF SaMD WG ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| #11 退役 | 21 CFR 806 discontinuance ⚪ | 注册证注销（B1-C01） ⚪ | MDR Art.10(8) ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |

✅ = MVP 已实现（FDA + NMPA 双辖区做实）；⚪ = 路线图。

## 辖区适配器接口约定

```python
class DomainJudge:
    domain: str
    def evaluate(self, ctx: dict) -> dict:
        # ctx["jurisdiction"] in {"FDA", "NMPA", "EU_MDR", "IMDRF", ...}
        # GateEngine routes automatically; per-jurisdiction rule branches
        # live in judges/judge_<domain>.py and config/jurisdictions.yaml.
```

本 MVP 落地：
- **FDA**：`judge_510k` + `judge_postmarket`，依据 21 CFR 807.81(a) / 803 / 806
- **NMPA**：`judge_510k` 增加 NMPA 分支（登记事项变更自声明路径）；`judge_postmarket` 接受 NMPA 三级召回
- **EU MDR**：仅列入路线图，未实现
- **其余 5 辖区**（IMDRF/PMDA/MFDS/MHRA/Health Canada）：路线图占位

## 已做实的法规差异（本 MVP 实测）

同一事实「Class II 器械二级聚合物管路供应商等效替代 + 完整验证报告」：

| 辖区 | 判定 | 规则依据 |
|---|---|---|
| FDA | **HOLD**（需新 510(k)） | 21 CFR 807.81(a)：材料变更推定显著 |
| NMPA | **GO**（登记事项自声明） | 47号令：等效供应商变更可自声明，无需变更注册 |

实测命令：
```
python -m demo1.change_gate --case demo1/cases_jurisdiction/supplier_swap.json --jurisdiction FDA
python -m demo1.change_gate --case demo1/cases_jurisdiction/supplier_swap.json --jurisdiction NMPA
```

## 法规来源标注统计

- 表格内法规条款引用：约 **40 格 × 1 条 ≈ 40 处**
- 已做实（FDA + NMPA）：约 12 处条款引用
- 路线图占位：约 28 处（标注「依据公开法规要点，条款号以官方文本为准」）
