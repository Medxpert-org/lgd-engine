"""DomainJudge Protocol + JudgeVerdict data structures.

Fixed schema (shared with parallel Demo2 line):
    JudgeVerdict = {
        "verdict": "go" | "hold" | "reject",
        "reasons": [{"rule": str, "level": "critical|major|minor", "detail": str}],
        "evidence": [{"kind": str, "ref": str}],
    }
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Protocol, runtime_checkable


VALID_VERDICTS = ("go", "hold", "reject")
VALID_LEVELS = ("critical", "major", "minor")


@dataclass
class Reason:
    rule: str
    level: str
    detail: str

    def __post_init__(self) -> None:
        if self.level not in VALID_LEVELS:
            raise ValueError(f"invalid reason level: {self.level}")


@dataclass
class Evidence:
    kind: str   # e.g. "fda_recall", "fda_510k", "nmpa_recall", "internal_verification"
    ref: str    # e.g. "Z-1924-2025", "K190204", URL, or local doc id


@dataclass
class JudgeVerdict:
    verdict: str                       # go | hold | reject
    reasons: List[Reason] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.verdict not in VALID_VERDICTS:
            raise ValueError(f"invalid verdict: {self.verdict}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "reasons": [asdict(r) for r in self.reasons],
            "evidence": [asdict(e) for e in self.evidence],
        }

    @property
    def has_critical(self) -> bool:
        return any(r.level == "critical" for r in self.reasons)


def is_unusable(ctx: Dict[str, Any], contract: Dict[str, type]) -> List[str]:
    """Keys the judge cannot use, spelled as absent, blank, or of the wrong type.

    Deleting a key was only the first spelling of absence (PR #40). A key that is
    present but null, "", [] or {} reads to a rule as "nobody objected" exactly
    as a missing one did, and a 0 in a boolean slot slips past `is False`. The
    contract therefore says what a usable value looks like, not just that the key
    exists.
    """
    bad: List[str] = []
    for key, want in contract.items():
        if key not in ctx:
            bad.append(key)
            continue
        value = ctx[key]
        if value is None:
            bad.append(key)
            continue
        if isinstance(value, str) and not value.strip():
            bad.append(key)
            continue
        if isinstance(value, (list, dict, tuple)) and len(value) == 0:
            bad.append(key)
            continue
        if want is bool:
            if not isinstance(value, bool):
                bad.append(key)
        elif not isinstance(value, want):
            bad.append(key)
    return bad


@runtime_checkable
class DomainJudge(Protocol):
    """Every domain adapter implements this. ctx is an input JSON dict."""

    domain: str

    def evaluate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover - protocol
        ...

def canonicalize(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """The same fact, spelled differently, must reach the judge as one fact.

    Absence was the first attack surface. This is the second: every value present,
    only its spelling changed -- "Class1" for "class1", "  class1  " for "class1".
    Rules compare exact tokens, so without this a record that says the same thing
    in different casing can answer `go` where it should answer `reject`.

    Only strings are touched: strip, collapse internal whitespace, casefold. No
    field is dropped, no value is coerced, and a wrong type is not silently
    repaired -- that stays `is_unusable`/`misused`'s job, because a boolean written
    as "false" is not a spelling of False, it is a fact the record failed to state.
    """
    def walk(node):
        if isinstance(node, str):
            return " ".join(node.split()).casefold()
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node
    return walk(ctx)


def misused(ctx: Dict[str, Any], contract: Dict[str, type]) -> List[str]:
    """Keys that are present but carry the wrong type.

    A different question from `is_unusable`, on purpose. An optional boolean that
    is absent is a fact nobody stated -- rules may still judge the record. The same
    boolean written as "false" is not an absence and not a fact: it is a value that
    reads as truthy to every plain `if` downstream. Omitting it keeps the old
    behaviour; spelling it wrongly blocks the verdict.
    """
    bad: List[str] = []
    for key, want in contract.items():
        if key not in ctx:
            continue
        value = ctx[key]
        if value is None:
            continue
        if isinstance(value, bool) != (want is bool):
            bad.append(key)
    return bad
