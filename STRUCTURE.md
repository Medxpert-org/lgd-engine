# STRUCTURE — lgd-engine 的结构地图

依赖方向单向：契约 → 判定 → 门禁/适配 → 检验 → 治理。下层不得反向依赖上层。

## 五层

| 层 | 文件 | 内容 |
|---|---|---|
| L1 契约 | `framework/skill-manifest-spec.md`、`lgd-core`/manifest schema（见 `uibc-core/lgd-core/MANIFEST.schema.json` 同源口径）、`docs/openapi.yaml` | 技能清单、manifest 字段、MCP 接口形状 |
| L2 判定 | `lgd_engine/judges/judge_510k.py`、`judge_postmarket.py`、`lgd_engine/config/jurisdictions.yaml`、`lgd_engine/theory/laws.yaml` | 规则与法域配置；**当前只覆盖 2/13 域** |
| L3 门禁与适配 | `lgd_engine/gate/engine.py`、`lgd_engine/cli.py`、`lgd_engine/mcp_server.py`、`framework/adapter-roadmap.md`、`lgd-engine-ts/` | 三态出口（exit 0/1/2 = go/hold/reject）、MCP 适配、TS SDK |
| L4 检验 | `demo1/test_demo1.py`、`demo2/test_demo2.py`、`lgd_engine/mcp_smoke.py`、`review/redteam_probe.py`、`docs/validate_openapi.py`、`.github/workflows/{gate,codeql,version-gate}.yml` | 黄金案例、红队探针、OpenAPI 校验、CI |
| L5 治理 | `EVIDENCE-INDEX.md`（本仓）、`review/evidence/*`、`release-prep/PRE_RELEASE_REVIEW.md`、`contributions/itu-fg-tida/` | 证据分级、评审快照、对外贡献件 |

## 改动代价

| 你想做 | 改哪里 | 必须重跑 | 必须同步 |
|---|---|---|---|
| 加一个判定域 | `judges/` 新文件 + `config/jurisdictions.yaml` | `demo1/test_demo1.py`、`gate.yml` | README 覆盖域声明、`EVIDENCE-INDEX.md` 第 1 条 |
| 改三态出口语义 | `gate/engine.py` + `cli.py` | demo1/demo2 全量 | README 的 exit code 段（**退出码就是裁决**，改了会打断所有 CI 包装器） |
| 提升第二实现等级 | `lgd-engine-ts/` + 向量对账脚本 | `test/smoke.mjs` + 对账 | `EVIDENCE-INDEX.md` L3 行 |
| 改 MCP 接口 | `mcp_server.py` + `docs/openapi.yaml` | `docs/validate_openapi.py`、`mcp_smoke.py` | `framework/skill-manifest-spec.md` |

## 与 lcas 的边界

- 本仓：判定**引擎本体**（多域、三态、MCP）。
- `lcas`：**变更是否越界**这一件事的规范与符合性套件（含法规锚点、真实语料、外审回执）。
- 两边共用规则口径，但**证据不互借**；引用对方必须写"见对方仓"。

## 入口约定

新人顺序：`README.md`（怎么跑）→ 本文件（改哪会坏哪）→ `EVIDENCE-INDEX.md`（能信到什么程度）。
