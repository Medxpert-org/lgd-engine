# EVIDENCE-INDEX — lgd-engine 的证据分级

判定口径：等级看**谁能复现**，不看作者自我评价。没有取得的等级写 `0`，并写清缺什么才能升。
本表由仓库内现存文件支撑，文件名可逐个点开核对。

## 现状

| 级 | 结果 | 证据位置 | 说明 |
|---|---|---|---|
| L1 自我复现 | **有** | `demo1/test_demo1.py`、`demo2/test_demo2.py`、`lgd_engine/mcp_smoke.py`、`review/redteam_probe.py`、`.github/workflows/gate.yml` | clone 后 `python -m demo1.change_gate --all` 与 `python -m unittest discover demo1` 可离线复跑；CI `gate.yml` 每次 push 跑 |
| L2 异体审查 | **有限** | `review/evidence/pre_release_latest.json`、`review/evidence/redteam_before.json`、`review/evidence/redteam_after.json`、`review/report.html` | 存在评审与红队前后快照，但**评审者身份与是否为异体需在回执内可核**；本表不把"有脚本"当成"有异体审查" |
| L3 第二实现 | **部分** | `lgd-engine-ts/`（TypeScript SDK，`test/smoke.mjs`） | 是独立语言的另一份实现，但仅 smoke，**未在同一批 conformance 向量上与 Python 版逐条对账**，故不计为完整 L3 |
| L3.5 外部语料 | **0** | — | 引擎自身未接真实监管语料；该项在 `lcas`（同门仓）里做：50 条冻结 510(k) 语料、指纹已公开、可判定率 0/50 如实报告 |
| L4 外部节点 | **0** | — | 无本生态之外的第三方系统/组织实际采用并可指认 |

## 已知不硬的地方

1. **判定域覆盖 2/13。** `lgd_engine/judges/` 现只有 `judge_510k.py` 与 `judge_postmarket.py`；`framework/13domains-mapping.md` 是**规划**，不是已实现。README 的 `status-MVP draft` 与此一致。
2. **无第二实现的符合性对账。** `lgd-engine-ts` 只有 smoke，不能证明两版同判。
3. **规则锚点未逐条核到原文。** 条文级核验发生在 `lcas/ANCHORS.md`（36 条已核、4 条 `unverified`）；引擎侧沿用同一批规则但未单独复核。
4. **无可指认的外部采用者。** 星标、下载量、口头引用都不计 L4。

## 为什么 `lcas` 的等级不能被继承

`lcas` 有 L3.5（外部语料）与四轮异体外审回执，但那是**另一个仓的证据**。本仓引用它时必须写成"见 lcas"，不能写成"本仓已有 L3.5"。跨仓借用证据是最常见的夸大方式。

## 维护约定

- 每次合并改变结论的 PR，同步本表；未更新的 PR 视为未测。
- 等级只降不升，除非新证据落盘。
- 第 3 行（L3）升为"有"的唯一条件是：`lgd-engine-ts` 与 Python 版在同一批向量上给出相同 verdict 并留下对账文件。
