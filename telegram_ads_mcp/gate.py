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

_SECRET_WOULD_SEND = frozenset(
    {
        "confirm_hash",
        "stel_token",
        "stel_ssid",
        "stel_adowner",
        "api_hash",
        "cookie",
        "cookies",
        "media_base64",
        "password",
        "token",
        "ssid",
    }
)


def write_gate() -> str:
    raw = (os.environ.get("TG_ADS_WRITE_GATE") or DEFAULT).strip().lower()
    return raw if raw in VALID else DEFAULT


def attach_gate(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    g = write_gate()
    out["write_gate"] = g
    out["write_gate_hint"] = HINTS[g]
    return out


def sanitize_would_send(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Intended args for a gated call. Drops secrets and empty values. Not a dry-run result."""
    if not payload:
        return {}
    out: dict[str, Any] = {}
    for key, value in payload.items():
        low = str(key).lower()
        if low in _SECRET_WOULD_SEND or low.startswith("stel_"):
            if low == "media_base64" and value:
                out["has_media_base64"] = True
            continue
        if key in {"confirm", "confirm_hash"}:
            continue
        if value is None or value == "":
            continue
        out[key] = value
    return out


def gated(
    *,
    cls: str,
    confirm: bool = False,
    tool: str = "",
    would_send: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return a write_gated payload, or None if the call may proceed.

    ok is always False. This is not a platform dry-run and nothing was sent.
    """
    if cls in {"read", "auth"}:
        return None
    g = write_gate()
    needed = NEEDS_CONFIRM.get(g, NEEDS_CONFIRM[DEFAULT])
    if confirm or cls not in needed:
        return None
    payload: dict[str, Any] = {
        "ok": False,
        "code": "write_gated",
        "write_gate": g,
        "class": cls,
        "tool": tool,
        "sent": False,
        "error": f"{tool or 'this tool'} is gated ({g}/{cls}). {HINTS[g]}",
        "hint": "Re-call with confirm=true after the operator agrees, or set TG_ADS_WRITE_GATE in .env.",
        "would_send": sanitize_would_send(would_send),
    }
    return payload
