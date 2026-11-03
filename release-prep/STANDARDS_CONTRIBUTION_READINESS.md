# Standards-contribution readiness — the legal and process gate

**Seat:** 合规官 (S7 合规治理) · **已读灌注包 v1.0**（`D:/Workbuddy/03-方案文档/AI专家团经验灌注包_v1.0_20260921.md`，S7 行：§1 全部 + 章程 §六 红线 + 反模式第 45 条）

**Identity:** 本文件由 AI 席位出具，不是法律意见。凡涉专利声明、CLA 主体资格、许可证与专利冲突的判断，一律上报 CEO 并建议外部执业律师/代理（承本席位「越界提醒」）。

**对象:** `Medxpert-org/lgd-engine` @ branch `fix/s6-review-20261104`
**范围:** 以开源软件形式向 ITU-T / W3C 社区组提交**贡献**前的法务与流程要件。

---

## 0. 判定口径与检索范围（反模式第 45 条）

下面的「通过 / 风险 / 拦截」是**判定**，不是印象。凡否定性结论都写明查了哪里：

- 检索范围：`lgd-engine` 仓库工作树全部**受版本控制**的文件（`git ls-files` → 98 个文件），含 `release-prep/`、`docs/`、`.github/`、`pyproject.toml`、`NOTICE`、`LICENSE`、`CITATION.cff`、`CONTRIBUTING.md`、`SECURITY.md`
- 检索方法：全文正则 `CLA|DCO|Signed-off-by|patent|copyright|license|contribut`（不区分大小写），逐命中读上下文；`LICENSE` 202 行全文读（确认 §3 专利授权段在 L74）
- 覆盖度：**1194 处命中，分布在 98 个文件中的 75 个**；`®` 符号全仓 **0 命中**
- **未查**：GitHub 组织层设置（是否有 org-wide CLA bot）、Zenodo/DataCite 账号后台、ITU/W3C 会员或参与资格 —— 不在本机可读范围内，故本文件不对其下结论

## 1. 逐项体检

| # | 要件 | 依据 | 现状（可核） | 判定 | 材料位置 |
|---|---|---|---|---|---|
| 1 | 材料可无限制再分发 | ITU-T A.1 §3.1.6 | Apache-2.0 明示允许再分发与衍生，`NOTICE` 保留归属与理论署名 | **通过** | `LICENSE` L1–202，`NOTICE` |
| 2 | 软件版权与许可声明 | ITU-T A.1 §3.1.7 | 版权人、许可、第三方组件三段齐全；但**提交时随稿附的书面声明**尚未成文 | **风险** | `NOTICE`；缺"提交声明"模板 |
| 3 | 开会前 12 个日历天提交 | ITU-T A.1 §3.1.8 | 无排期，无提交日历 | **拦截（流程）** | — |
| 4 | 专利政策（早披露 / 声明表） | Common Patent Policy ITU-T/ITU-R/ISO/IEC | Apache-2.0 §3 已含明示专利授权与终止条款；但**未向标准组织提交 Patent Statement**，也未做"是否含必要专利"的检索 | **风险·上报** | `LICENSE` L74 起 |
| 5 | W3C 社区组 CLA | W3C CG 参与规则 | 仓库无 CLA 机器人，未加入任何 CG | **拦截（主体决策）** | — |
| 6 | 贡献的入站许可（inbound = outbound） | Apache-2.0 惯例 + §3.1.6 再分发前提 | 本轮前：`CONTRIBUTING.md` 只讲**出站**许可与理论归属，**没有**入站授权语句 —— 第三方 PR 无明示许可，再分发链在此断掉 | **已修复** | `CONTRIBUTING.md` § Contribution licensing |
| 7 | DCO / Signed-off-by | 常见开源治理 | 不强制，CI 不校验 | **风险（不得声称已强制）** | `CONTRIBUTING.md` 已如实声明"不要求" |
| 8 | 唯一持久标识（DOI） | FORCE11 六原则 | `CITATION.cff` 与 `pyproject.toml` 版本一致 0.1.0；**无 DOI**，且正确地在拿到 DOI 前不编造 | **风险（待 Zenodo）** | `CITATION.cff` |
| 9 | 归档元数据优先级 | Zenodo 规则 | 当前**无** `.zenodo.json`，故 `CITATION.cff` 生效 —— 状态正确；若日后新增会静默覆盖 | **通过（含陷阱提示）** | `release-prep/PRE_RELEASE_REVIEW.md` §3 |
| 10 | 第三方代码 | 许可兼容 | `pyproject.toml` 无 vendored 代码，依赖各自持证 | **通过** | `pyproject.toml`，`NOTICE` 第三段 |
| 11 | 无患者数据 / 无敏感外发 | 中国《个人信息保护法》+ 通用最小化 | 示例与判例均为**公开召回记录**（FDA/NMPA 公告类），无患者标识；`security/security_scan.py` 对密钥/邮箱/主机路径做扫描，本轮 0 findings | **通过** | `lgd_engine/config/` 判例引用；`security/security_scan.py` 输出 |
| 12 | 商标使用口径 | 未确权期用标红线 | 全文无 ®、无"官方/已注册"字样 | **通过** | 全仓检索 `®` 0 命中 |
| 13 | 医疗内容边界 | 本席位红线 | 只给注册/合规判定，不给诊断或治疗建议；`README.md` 与 `SECURITY.md` 均有免责边界 | **通过** | `README.md`、`SECURITY.md` |

## 2. 上报 CEO 的三件事（本席位不自行拍板）

1. **专利声明要不要交、按哪一档交**（"无必要专利" vs "有且愿意按 RAND 授权"）。这需要一次针对 `lgd_engine/` 实现与 LGD 理论的必要专利检索，超出本机可读范围。
2. **CLA 的主体资格**：W3C CG 的 CLA 由个人还是由主体（公司/基金会）签署，决定后续贡献的归属与再许可能力。
3. **提交形态**：走"文稿贡献"（A.1 全流程、12 天窗口）还是"软件贡献"（§3.1.7 声明 + 仓库链接）。两者材料清单不同。

## 3. 与工程门的关系（不重复，只引用）

工程侧的 10 项自动检查、20 个探针与其自检，见 `release-prep/PRE_RELEASE_REVIEW.md`；其中 `legal` 检查把本文件第 1、2、6、7 项做成了可失败的门：

```bash
python review/pre_release_review.py --only legal
```

## 4. 红线自检（章程 §六）

- 红线 1「验证者不得是作者」：**本轮不满足**。探针台由实现者编写，属**内部独立**（作者自查 + 机器可证伪），**不是第三方独立**。本文件与审查文档均按"内部独立"表述，不冒充机构级独立。
- 红线 4「宣称闸」：本文件所有"通过"均附材料位置；无输出的结论不写"通过"。
- 红线 5 / 反模式 45：否定性结论已在 §0 声明检索范围与覆盖度。

## 5. 结论

**工程可交付，法务流程未闭环。** 第 1、6、9–13 项通过；第 2、4、7、8 项为风险（有材料、缺一份对外声明或一个标识）；第 3、5 项是**主体决策级拦截**，不是代码问题。在 §2 三件事有结论前，本仓库可以作为**公开可引用的开源实现**被引用，但不应对外表述为"已完成向某标准组织的贡献"。
