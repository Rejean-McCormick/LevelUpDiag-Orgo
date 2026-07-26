"""Verdict constants and aggregation rules."""

from __future__ import annotations

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
SKIP = "SKIP"
BLOCKED = "BLOCKED"
PARTIAL = "PARTIAL"
ERROR = "ERROR"
INFRA_ERROR = "INFRA_ERROR"
CONFIG_ERROR = "CONFIG_ERROR"

_ORDER = {
    PASS: 0,
    SKIP: 1,
    WARN: 2,
    PARTIAL: 3,
    FAIL: 4,
    BLOCKED: 4,
    INFRA_ERROR: 5,
    CONFIG_ERROR: 5,
    ERROR: 6,
}

def normalize(value: str | None) -> str:
    raw = str(value or PASS).strip().upper()
    return raw if raw in _ORDER else ERROR

def worst(values: list[str]) -> str:
    if not values:
        return PASS
    return max((normalize(v) for v in values), key=lambda v: _ORDER[v])

def exit_code(status: str, *, strict_warn: bool = False) -> int:
    status = normalize(status)
    if status == PASS or status == SKIP:
        return 0
    if status in {WARN, PARTIAL}:
        return 1 if strict_warn else 0
    if status in {FAIL, BLOCKED}:
        return 2
    if status == INFRA_ERROR:
        return 3
    if status == CONFIG_ERROR:
        return 4
    return 5
