"""Pure SC Mail governance core. No cloud/provider dependency."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json, re
from typing import Iterable

HARD_OUTLOOK_CEILING = 9_950
SAFE_MESSAGES_PER_MINUTE = 28
INVARIANTS = (
    "Time","Continuity","Alignment","Genesis",
    "Boundary","Reference","Causality","Consciousness",
)
_BLOCKED_SOURCES = {"scraped","purchased","bought","unknown","mystery"}
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

@dataclass(frozen=True)
class Decision:
    decision: str
    checks: dict[str, bool]
    reasons: tuple[str, ...]
    receipt_sha256: str

def _receipt(payload: dict) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",",":")).encode()).hexdigest()

def evaluate_contact(contact: dict, campaign: dict) -> Decision:
    email = str(contact.get("email","")).strip().lower()
    source = str(contact.get("source","")).strip().lower()
    suppressed = any(bool(contact.get(k)) for k in ("unsubscribed","hard_bounce","complaint"))
    checks = {
        "Time": True,
        "Continuity": not suppressed,
        "Alignment": bool(_EMAIL_RE.match(email)),
        "Genesis": bool(source) and source not in _BLOCKED_SOURCES,
        "Boundary": not suppressed,
        "Reference": bool(campaign.get("id") or campaign.get("subject")),
        "Causality": bool(contact.get("purpose") or contact.get("relationship") or source),
        "Consciousness": bool(campaign.get("authorized", False)),
    }
    reasons = tuple(k for k,v in checks.items() if not v)
    payload = {"email": email, "campaign": campaign.get("id"), "checks": checks}
    return Decision("PERMIT" if not reasons else "HOLD", checks, reasons, _receipt(payload))

def compile_batch(contacts: Iterable[dict], campaign: dict, requested: int) -> dict:
    requested = min(max(int(requested), 0), HARD_OUTLOOK_CEILING)
    seen, permitted, held = set(), [], []
    for contact in contacts:
        email = str(contact.get("email","")).strip().lower()
        if email in seen:
            held.append({"email": email, "reason": "duplicate"})
            continue
        seen.add(email)
        d = evaluate_contact(contact, campaign)
        (permitted if d.decision == "PERMIT" else held).append(
            {"email": email, "receipt": d.receipt_sha256, "reasons": list(d.reasons)}
        )
    selected = permitted[:requested]
    state = {
        "requested": requested,
        "selected": selected,
        "held": held,
        "ceiling": HARD_OUTLOOK_CEILING,
        "safe_messages_per_minute": SAFE_MESSAGES_PER_MINUTE,
        "invariants": INVARIANTS,
    }
    state["batch_receipt_sha256"] = _receipt(state)
    state["decision"] = "PERMIT" if requested and len(selected) == requested else "HOLD"
    return state
