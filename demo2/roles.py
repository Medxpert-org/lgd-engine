"""Five seat roles for the gate review meeting.

Each seat is a rule-based mock (no external LLM calls).
Adapter replacement point: replace comment() / final() / hold() internals
with real AI API calls while keeping the same interface.

席位：
  - 理论官 (Theorist): LGD 三律对照
  - 门禁官 (Gatekeeper): LGD-Eval，持一票 hold 权
  - 红队   (RedTeam): 挑刺
  - 终审   (FinalReviewer): Muse，终审裁决
  - 执行席 (Executor): 落地决议
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_critical(reasons: list[str]) -> bool:
    """Check if any reason mentions critical / 严重 / 阻断."""
    keywords = ("critical", "严重", "阻断", "block", "veto", "致命")
    return any(any(k in r.lower() for k in keywords) for r in reasons)


def _verdict_strength(verdict: str) -> int:
    v = (verdict or "").lower()
    if "pass" in v or "通过" in v:
        return 3
    if "warn" in v or "condit" in v or "有条件" in v:
        return 2
    if "fail" in v or "reject" in v or "不通过" in v:
        return 1
    return 0


# ---------------------------------------------------------------------------
# Seat base
# ---------------------------------------------------------------------------

class BaseSeat:
    """Common interface for all seats."""
    name: str = "base"
    display_name: str = "Base Seat"

    def comment(self, item: dict[str, Any]) -> str:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 1. 理论官 — LGD 三律对照
# ---------------------------------------------------------------------------

class Theorist(BaseSeat):
    name = "theorist"
    display_name = "理论官"

    def comment(self, item: dict[str, Any]) -> str:
        case = item.get("case", "未知案例")
        verdict = item.get("verdict", "未知")
        reasons = item.get("reasons", [])
        evidence = item.get("evidence", [])

        lines = [f"[理论官] 案例「{case}」LGD 三律对照："]
        # 律一：有籍
        has_evidence = len(evidence) > 0
        lines.append(f"  律一·有籍：{'✓ 证据链已附 (' + str(len(evidence)) + ' 条)' if has_evidence else '✗ 缺证据，需补'}")
        # 律二：有证
        has_reasons = len(reasons) > 0
        lines.append(f"  律二·有证：{'✓ 评审理由 (' + str(len(reasons)) + ' 条)' if has_reasons else '✗ 理由空泛'}")
        # 律三：有门禁
        gate_ok = _verdict_strength(verdict) >= 2
        lines.append(f"  律三·有门禁：{'✓ 门禁已触发并给出裁决' if gate_ok else '✗ 门禁未生效'}")

        if _has_critical(reasons):
            lines.append("  ⚠ 检出 critical 级理由，三律中「有门禁」被突破，建议门禁官介入。")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. 门禁官 — LGD-Eval，持一票 hold 权
# ---------------------------------------------------------------------------

class Gatekeeper(BaseSeat):
    name = "gatekeeper"
    display_name = "门禁官"

    def comment(self, item: dict[str, Any]) -> str:
        case = item.get("case", "未知案例")
        reasons = item.get("reasons", [])
        critical = _has_critical(reasons)
        lines = [f"[门禁官] 案例「{case}」门禁扫描："]
        if critical:
            lines.append("  🚫 检出 critical 级理由 — 行使一票 hold 权。")
            for r in reasons:
                if any(k in r.lower() for k in ("critical", "严重", "阻断", "block", "veto", "致命")):
                    lines.append(f"     · {r}")
        else:
            lines.append("  ✓ 无 critical 阻断项，门禁放行。")
            if reasons:
                lines.append(f"  附注 {len(reasons)} 条普通理由，已记录但不阻断。")
        return "\n".join(lines)

    def hold(self, item: dict[str, Any]) -> bool:
        """Return True if this item must be held (veto / block)."""
        return _has_critical(item.get("reasons", []))


# ---------------------------------------------------------------------------
# 3. 红队 — 挑刺
# ---------------------------------------------------------------------------

class RedTeam(BaseSeat):
    name = "redteam"
    display_name = "红队"

    def comment(self, item: dict[str, Any]) -> str:
        case = item.get("case", "未知案例")
        verdict = item.get("verdict", "未知")
        reasons = item.get("reasons", [])
        evidence = item.get("evidence", [])

        lines = [f"[红队] 案例「{case}」挑刺："]
        # 挑刺 1：证据是否充分
        if len(evidence) < 2:
            lines.append("  🔍 证据链偏薄（<2 条），建议补充实测数据或外部引用。")
        else:
            lines.append(f"  ✓ 证据 {len(evidence)} 条，基本充分。")
        # 挑刺 2：理由是否可操作
        vague = [r for r in reasons if len(r) < 10]
        if vague:
            lines.append(f"  🔍 {len(vague)} 条理由过短，可能流于口号，建议细化。")
        # 挑刺 3：裁决与理由是否匹配
        strength = _verdict_strength(verdict)
        if strength == 3 and len(reasons) > 3:
            lines.append("  🔍 裁决为 Pass 但理由 >3 条，是否过于宽松？")
        if strength == 1 and not _has_critical(reasons):
            lines.append("  🔍 裁决为 Fail 但无 critical 理由，是否应降级为 Conditional？")
        if not lines or len(lines) == 1:
            lines.append("  （未发现明显刺点）")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. 终审 — Muse，终审裁决
# ---------------------------------------------------------------------------

class FinalReviewer(BaseSeat):
    name = "final"
    display_name = "终审"

    def comment(self, item: dict[str, Any]) -> str:
        case = item.get("case", "未知案例")
        return f"[终审] 案例「{case}」已登记，待五席发言完毕后给出终审裁决。"

    def final(self, comments: dict[str, str], item: dict[str, Any], gated: bool) -> str:
        """Produce the final decision string."""
        case = item.get("case", "未知案例")
        original_verdict = item.get("verdict", "未知")

        if gated:
            decision = "HOLD"
            basis = "门禁官行使一票 hold 权，存在 critical 阻断项，需补充材料后重审。"
        elif _verdict_strength(original_verdict) >= 3:
            decision = "PASS"
            basis = "五席意见一致，无阻断项，原裁决通过。"
        elif _verdict_strength(original_verdict) == 2:
            decision = "CONDITIONAL_PASS"
            basis = "有条件通过，需跟进普通理由中的整改项。"
        else:
            decision = "REJECT"
            basis = "终审不支持原裁决，需退回重做。"

        return f"[终审·Muse] 案例「{case}」终审裁决：{decision}\n  依据：{basis}"


# ---------------------------------------------------------------------------
# 5. 执行席 — 落地决议
# ---------------------------------------------------------------------------

class Executor(BaseSeat):
    name = "executor"
    display_name = "执行席"

    def comment(self, item: dict[str, Any]) -> str:
        case = item.get("case", "未知案例")
        return f"[执行席] 案例「{case}」已就绪，待终审裁决后落库执行。"

    def execute(self, decision_str: str, item: dict[str, Any]) -> str:
        """Return an execution note."""
        case = item.get("case", "未知案例")
        if "PASS" in decision_str:
            return f"[执行席] 案例「{case}」决议已落库，进入下一流程。"
        if "HOLD" in decision_str:
            return f"[执行席] 案例「{case}」已挂起（HOLD），通知提交方补材料。"
        return f"[执行席] 案例「{case}」已退回（REJECT），通知提交方重做。"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def all_seats() -> list[BaseSeat]:
    """Return all five seats in speaking order."""
    return [Theorist(), Gatekeeper(), RedTeam(), FinalReviewer(), Executor()]
