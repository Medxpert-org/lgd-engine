> **本文件为 2026-11-18 时点快照，数字不代表当前状态。** 当前基线以 `docs/methods/Eval_Report_v1.md` 与仓库根目录 `README.md` 为准。

# 法规条文核验 — NMPA 判定器（2026-11-18）

**目的：** 补上方法说明中自认的盲区「未做法律核验」。做法是把 `judge_nmpa.py` 里每一条
字段归类、每一条罚则引用，回到**条文原文**逐条对照，而不是对照二手解读。

**核验方法：** 用法规条文检索引擎取《医疗器械注册与备案管理办法》《医疗器械监督管理条例
（2024 年修订）》的现行条文原文（中国司法大数据研究院收录的现行有效版本），逐句比对规则表
的编码；凡规则表与条文措辞不一致、或条文有而规则表没有的，记为 finding 并改代码。

**核验范围声明：** 仅中国 NMPA 两张表。EU MDR（MDCG 2020-3 rev.1）与 FDA PCCP
（21 CFR 892.2055）**本次未核验**，仍属盲区。

---

## 1. 条文原文（核验依据）

### 47 号令 第七十九条

> 已注册的第二类、第三类医疗器械产品，其设计、原材料、生产工艺、适用范围、使用方法等发生
> **实质性变化**，有可能影响该医疗器械安全、有效的，注册人应当向原注册部门申请办理**变更
> 注册**手续；发生其他变化的，应当在变化之日起 **30 日内**向原注册部门**备案**。
>
> 注册证载明的**产品名称、型号、规格、结构及组成、适用范围、产品技术要求、进口医疗器械的
> 生产地址**等，属于前款规定的需要办理**变更注册**的事项。**注册人名称和住所、代理人名称和
> 住所**等，属于前款规定的需要**备案**的事项。**境内医疗器械生产地址变更的，注册人应当在
> 办理相应的生产许可变更后办理备案。**

### 47 号令 第八十条 / 第八十一条 / 第八十八条

- 第八十条：变更注册技术审评**重点针对变化部分**；必要时组织质量管理体系核查。
- 第八十一条：变更注册文件与原注册证**合并使用，有效期相同**。
- 第八十八条：**已备案**的医疗器械，备案信息表登载内容及备案的产品技术要求发生变化 →
  **变更备案**。

### 条例（国务院令第 797 号，2024 修订）

- 第二十一条：与 47 号令同口径（实质性变化 → 变更注册；其他 → 备案或报告）。
- 第八十一条(一)：**生产、经营未取得医疗器械注册证的第二类、第三类医疗器械** → 没收违法
  所得、违法生产经营的器械及工具设备原材料；货值 < 1 万并处 5–15 万罚款，≥ 1 万并处货值
  15–30 倍罚款；情节严重责令停产停业、10 年内不受理许可申请、终身禁业；并可吊销许可证。
- 第五十五条：经营企业、使用单位**不得经营、使用未依法注册或者备案**、无合格证明文件以及
  过期、失效、淘汰的医疗器械。
- 第八十四条 / 第八十五条：一类未备案、二类应备案未备案、备案资料不符要求等 → 较轻罚则档。

---

## 2. 逐条对照结果

| # | 条文要点 | 规则表编码（核验前状态） | 判定 |
|---|---|---|---|
| 1 | 产品名称/型号/规格/结构及组成/适用范围/产品技术要求/进口生产地址 → 变更注册 | `LICENCE_FIELDS` 六项，含 `import_manufacturing_site` | **符合** |
| 2 | 注册人名称和住所、代理人名称和住所 → 备案 | `REGISTRATION_FIELDS` 四项 | **符合** |
| 3 | 实质性变化（设计/原材料/生产工艺/适用范围/使用方法）可能影响安全有效 → 变更注册 | `safety_effectiveness_assessed` + 字段归类 | **符合**（判断入口保留为必填评估项，未评估即 hold） |
| 4 | 其他变化 → 30 日内备案 | 不建模为时限，仅建模为"须走备案" | **符合但部分**：无 30 日时限字段，见 §4 未覆盖项 |
| 5 | **境内**生产地址变更 → 先办生产许可变更后备案 | 仅把 `production_address_textual` 归入登记事项 | **偏离 → 已修（L3）** |
| 6 | **一类器械实行备案管理**，同类变更走变更备案 | 未建模产品类别，一律按二/三类变更注册输出 | **缺失 → 已修（L1）** |
| 7 | 未注册二/三类生产销售 → 处罚（第八十一条(一)） | 引用写作「条例 739」 | **引用过时 → 已修（L2）** |
| 8 | 经营/使用未依法注册或备案器械 → 禁止（第五十五条） | `N-CRIT-01` 理由文本 | **已补引用** |
| 9 | 已备案产品备案信息表及技术要求变化 → 变更备案（第八十八条） | 用于支撑一类路径 | **已补引用** |

---

## 3. 三处 finding 与处置

### L1 — 未建模产品类别（一类走备案制，不是变更注册）

条文把「已注册的第二类、第三类」与「已备案的」分列。规则表只有一个 `LICENCE_FIELDS` 集合，
一律输出「须变更注册」：对一类器械这是**指向一个对其不存在的行政许可**。

处置：新增 `device_class` 字段与规则 `N-MAJ-13-class1-filed-not-registered`；`N-MAJ-01` 与
`N-CRIT-02` 都加类别门，避免把一类的备案路径读成"把许可事项当登记事项逃避审评"。
未声明类别时，仍按二/三类处理并给出 hold —— 保守方向，不放松。

### L2 — 罚则引用版本过时

原文为 **国务院令第 797 号（2024 修订）**，前身是 739 号。规则与文档仍写 739。引用过时在监管
材料里是最容易被抓的硬伤：条文可能已被修订，读者无法确认我们核过。

处置：`judge_nmpa.py` 全部引用改 797，并写明 739 为前身；罚则条目细化到「第八十一条(一)」
与「第五十五条」。

### L3 — 「生产地址文字性更正」与「境内生产地址变更」被同一个字段名吞掉

条文对两者的要求不同：前者不是地址变更；后者必须先办**生产许可变更**再备案，只做备案就
**跳过了法定前置条件**。原表把两者合为 `production_address_textual` 一个字段，并按"登记事项"
处理——意味着真实迁址只要写成"文字性更正"就能拿到 go。

处置：拆成 `DOMESTIC_SITE_FIELDS = {domestic_manufacturing_site}` 与
`TEXTUAL_FIELDS = {production_address_textual}`；新增
`N-MAJ-14-domestic-site-change-prerequisite`，理由文本直接点明前置条件。

---

## 4. 仍未覆盖（不假装已核）

1. **30 日备案时限**未建模：表里没有 `days_since_change`，无法对超期做判断。
2. **"实质性变化"的实体判断**仍由调用方的 `safety_effectiveness_assessed` 承担，表只承接
   结论，不承接论证。
3. **第八十条**的"重点针对变化部分审评"未转化为任何规则——它约束监管方审评范围，不约束
   申报方路径，属正确地未建模。
4. **EU MDR / FDA PCCP 未核验**：MDCG 2020-3 rev.1 的重大变更清单、21 CFR 892.2055 原文
   均未取，条文级比对未做。
5. **地方性实施规定**未覆盖（如各省对一类备案的具体要求）。

---

## 6. EU MDR 部分（同日补做）

**依据：** MDCG 2020-3 rev.1（2023-09 版，由 Regulation (EU) 2023/607 对齐）§4.1–§4.2 与
CAMD FAQ 17（MDR 过渡期条款）。

### 条文原文要点

> A significant change in the design or intended purpose consists of **two cumulative
> elements**: there is a change in the design or intended purpose, and the change is
> significant. Changes that do not concern design or intended purpose are **out of scope**
> of Article 120(3).（§4.1）

> Changes concerning the manufacturer's organisation (administrative changes) or changes
> concerning the manufacturing process should generally **not** be considered changes in
> the design or intended purpose … This includes … relocation or addition of new
> manufacturing sites … changing the supplier of a material, substance or component,
> provided the specifications … do not change.（§4.2）

> However, **limitations of the intended purpose** and **design changes related to
> corrective actions assessed and accepted by the Competent Authority** are **not**
> considered "significant" in the sense of Art. 120(3) MDR.（CAMD FAQ 17）

### 对照结果

| # | 条文要点 | 核验前编码 | 判定 |
|---|---|---|---|
| 10 | 重大变更需**两个要件同时成立**（涉及设计/预期用途 + 重大） | 用布尔字段分别承接，未显式要求两要件 | **符合**（字段层已隐含） |
| 11 | 行政变更、生产场地迁移、供应商替换（规格不变）不属设计/预期用途变更 | `administrative`/`labeling_clarification` 有专门 minor 规则；`supplier_swap` 靠"无 major 命中"落到 go | **符合但欠显式** |
| 12 | **限制预期用途**不构成重大变更 | `affects_intended_purpose=True` 直接命中 `M-MAJ-01`；若同时声明非重大则 `M-CRIT-02` 直接 reject | **偏离 → 已修（L4）** |
| 13 | **主管部门已评估接受的纠正措施**所致设计变更不构成重大变更 | `M-CRIT-01`（FSCA 未关闭）无豁免；`M-MAJ-03` 仍会拦 | **偏离 → 已修（L5）** |
| 14 | 过渡期终点 2027-12-31（III 类/IIb 植入）与 2028-12-31（其余） | 未建模日期 | **未覆盖**（表不判日期，只判显著性） |

### 两处 finding 与处置

**L4 — 把"限制适用范围"判成重大变更（过拦）**

原文明确：收窄宣称不是重大变更。我们的表只要 `affects_intended_purpose` 为真就要求
公告机构介入，甚至在同一案件里把"声明非重大"判成 `reject`——等于**惩罚厂商缩小自己的
适应症**。这与"过拦"型错误同源：朴素判定器把该放的拦住，我们的表也犯了同一类错。

处置：新增字段 `intended_purpose_direction`（`expansion` / `limitation` / 缺省），
`M-MAJ-01` 与 `M-CRIT-02` 均加方向门；新增 `M-MIN-02-intended-purpose-limitation`。
缺省方向仍按重大处理（保守方向不放松）。另加一条测试钉住**同一字段、相反方向**的
非对称性：`limitation` → go，`expansion` → hold。

**L5 — 主管部门已接受的纠正措施被双重拦截**

`M-CRIT-01` 在 FSCA 未关闭时否决一切涉及安全性能的变更；`M-MAJ-03` 又把同一变更判为
重大。但 FAQ 17 明确这类变更不构成重大变更：监管机构已经评估接受过它。结果是**我们
拒绝了监管机构刚批准的那条路**。

处置：`M-CRIT-01` 增加 `corrective_action_accepted_by_authority` 豁免；评估层面在豁免
成立时整体跳过 major 规则（否则每一条显著性标准都会把同一变更重新拦一遍）；新增
`M-MIN-03-corrective-action-accepted`。

### 仍未覆盖

- MDR 过渡期**日期**（2027/2028）未建模：表判显著性，不判"证书是否还在期内"。
- **软件变更子图谱（Chart C）**的细节（如操作系统/架构大改、算法影响诊疗输出）未逐项
  编码，仅由 `software_algorithm` + `affects_safety_or_performance` 粗粒度承接。
- **FDA PCCP 条文级核验仍未做**（21 CFR 892.2055 / FD&C 515C 原文未取），仍是盲区。

---

## 6.5 FDA PCCP 部分（同日补做，最后一张表）

**依据：** FD&C Act §515C（21 U.S.C. 360e-4，由 FDORA §3308 于 2022-12-29 加入）；21 CFR 892.2055
（放射类机器学习定量影像软件 + PCCP，2026-11-19 现行有效）；FDA 终版指南（2024-12-04 发布）。

### 条文原文要点

> (b) CLEARED DEVICES. … a premarket notification shall not be required for a change to a
> device cleared under section 510(k), if such change is consistent with an established
> predetermined change control plan granted pursuant to paragraph (2) — **provided (A) the
> device remains safe and effective without any such change; and (B) the device would
> remain substantially equivalent to the predicate.**

> (c) PREDICATE DEVICES. … the Secretary **shall not compare** a device to changed
> versions of a device implemented in accordance with an established PCCP as a predicate
> device. **Only the version of the device cleared or approved, prior to changes** made
> under the PCCP, may be used by a sponsor as a predicate device.

> (a)(3)/(b)(3) SCOPE. — The Secretary may require that a change control plan include
> labeling …, notification requirements if the device does not function as intended
> pursuant to such plan, and performance requirements for changes made under the plan.

### 对照结果

| # | 条文要点 | 核验前编码 | 判定 |
|---|---|---|---|
| 15 | 510(k) 路径需**两个条件同时成立**：保持安全有效（A）+ 保持与 predicate 实质等同（B） | 只承接"A/B 类"的 `acceptance_criteria_met` / `affects_intended_use`，无 SE 字段 | **缺失 → 已修（L6）** |
| 16 | **PCCP 修改后的版本不得作 predicate**，只可用清关/批准时的原始版本 | 完全未建模 | **缺失 → 已修（L7）** |
| 17 | 指南日期 | 写作 "Aug 2025" | **错误 → 已修（L8）**：终版指南 2024-12-04 发布 |
| 18 | 892.2055 要求标注含版本历史、独立测试集上的客观性能证据 | `labeling_version_history` / `acceptance_criteria_met` | **符合** |
| 19 | FDA 可要求"设备未按计划运行时须通知" | 未建模 | **未覆盖**（属可选项，非义务） |

### 三处 finding 与处置

**L6 — 只承接了一半的法定条件（缺能力）**

§515C(b)(2) 是**两个并列条件**。我们只判"安全有效"一侧（`acceptance_criteria_met`、
`affects_intended_use`），从不判"是否仍与 predicate 实质等同"。于是一个在计划范围内、但已
偏离 predicate 基础的更新会被判 `go`——而法条明确它拿不到 510(k) 路径。新增
`remains_se_to_predicate` 与 `P-CRIT-04`。

**L7 — 一条属于"没人"的禁止条款（独家覆盖）**

§515C(c) 禁止以 PCCP 修改后的版本作 predicate。这条规则不属于任何一家厂商，所以在竞品里
通常无人编码；但它决定了"我这个新版本能不能被别人当 predicate"——对做 510(k) 策略的人
是硬事实。新增 `pccp_modified_version_used_as_predicate` 与 `P-CRIT-05`。

**L8 — 指南日期错**

终版指南 2024-12-04 发布（Federal Register 2024-28361），草稿 2023-04-03。原文写 "Aug 2025"，
属日期错误。已改。同类问题：892.2055 的"final order 2026-06-17"无法从公开源确认，改为
"2026-11-19 现行有效"，不再声称发布日期。

### 仍未覆盖

- "设备未按计划运行须通知"（§515C(a)(3)/(b)(3)）未建模：FDA **可以**要求，非必然义务。
- 持续学习 / 自动更新型 PCCP 的 Q-Sub 建议未建模（属指南建议，非条文）。
- 892.2055 之外的其它 PCCP 器械类型（各分类法规特殊控制不同）未逐类编码。

---

## 7. 复跑

```bash
python -m lgd_engine.cli --all demo1/cases_mdr --domain mdr     # 7/7
python -m lgd_engine.cli --all demo1/cases_nmpa --domain nmpa   # 7/7
python -m unittest discover -s tests                            # 43 assertions
python benchmarks/build_demo_page.py                            # 28 cases · 28/28
```

