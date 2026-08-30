"""Write permission gate from TG_ADS_WRITE_GATE in .env."""

from __future__ import annotations

import os
from typing import Any

VALID = ("strict", "confirm", "open")
DEFAULT = "confirm"

HINTS = {
    "strict": "Every write needs confirm=true (or set TG_ADS_WRITE_GATE=confirm|open in .env).",
    "confirm": "Spend/destructive needs confirm=true. Pause, CPM, and on_hold create with budget 0 are free. Or TG_ADS_WRITE_GATE=open.",
    "open": "Writes allowed. Stars still refused. Cookies stay in .env.",
}

# Which classes require confirm=true at each gate.
NEEDS_CONFIRM = {
    "strict": frozenset({"write", "spend", "danger"}),
    "confirm": frozenset({"spend", "danger"}),
    "open": frozenset(),
}


def write_gate() -> str:
    raw = (os.environ.get("TG_ADS_WRITE_GATE") or DEFAULT).strip().lower()
    return raw if raw in VALID else DEFAULT


def attach_gate(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    g = write_gate()
    out["write_gate"] = g
    out["write_gate_hint"] = HINTS[g]
    return out


def gated(*, cls: str, confirm: bool = False, tool: str = "") -> dict[str, Any] | None:
    """Return a write_gated payload, or None if the call may proceed."""
    if cls in {"read", "auth"}:
        return None
    g = write_gate()
    needed = NEEDS_CONFIRM.get(g, NEEDS_CONFIRM[DEFAULT])
    if confirm or cls not in needed:
        return None
    return {
        "ok": False,
        "code": "write_gated",
        "write_gate": g,
        "class": cls,
        "tool": tool,
        "error": f"{tool or 'this tool'} is gated ({g}/{cls}). {HINTS[g]}",
        "hint": "Re-call with confirm=true after the operator agrees, or set TG_ADS_WRITE_GATE in .env.",
    }
