from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import json
from typing import Dict, List


class SafetyState(str, Enum):
    SAFE = "SAFE"
    ATTENTION = "ATTENTION"
    GUARDIAN = "GUARDIAN"
    RECOVERY = "RECOVERY"


class Decision(str, Enum):
    PERMIT = "PERMIT"
    HOLD = "HOLD"
    REJECT = "REJECT"


@dataclass(frozen=True)
class Invariants:
    time: bool
    continuity: bool
    alignment: bool
    genesis: bool
    boundary: bool
    reference: bool
    causality: bool
    consciousness: bool

    def all_true(self) -> bool:
        return all(asdict(self).values())


@dataclass(frozen=True)
class Context:
    device_id: str
    safety_state: SafetyState
    gnss_fresh: bool
    route_deviation: bool = False
    guardian_present: bool = True
    child_says_lost: bool = False
    sos_pressed: bool = False
    tamper_detected: bool = False
    recipient_authorized: bool = False
    trusted_safe_destination: bool = False
    wifi_available: bool = False
    terrestrial_link: bool = False
    satellite_link: bool = False
    direct_radio_link: bool = False


@dataclass(frozen=True)
class Transition:
    action: str
    decision: Decision
    next_state: SafetyState
    reason: str
    receipt_hash: str


def _canonical(payload: Dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _receipt(device_id: str, action: str, decision: Decision, state: SafetyState, reason: str) -> str:
    body = {
        "device_id": device_id,
        "action": action,
        "decision": decision.value,
        "state": state.value,
        "reason": reason,
        "wifi_dependency": False,
    }
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def derive_invariants(ctx: Context, action: str) -> Invariants:
    emergency = ctx.sos_pressed or ctx.child_says_lost or ctx.safety_state == SafetyState.GUARDIAN
    return Invariants(
        time=ctx.gnss_fresh,
        continuity=True if ctx.sos_pressed else (
            ctx.guardian_present or ctx.route_deviation or ctx.safety_state != SafetyState.SAFE
        ),
        alignment=action in {"observe", "guide", "share_location", "close_incident"},
        genesis=bool(ctx.device_id),
        boundary=(ctx.recipient_authorized if action == "share_location" else True),
        reference=(ctx.trusted_safe_destination if action == "guide" else True),
        causality=(emergency if action in {"guide", "share_location"} else True),
        consciousness=(
            ctx.sos_pressed
            or ctx.child_says_lost
            or action == "observe"
            or action == "close_incident"
        ),
    )


def evaluate(ctx: Context, action: str) -> Transition:
    if ctx.tamper_detected and action != "observe":
        d, s, r = Decision.REJECT, SafetyState.GUARDIAN, "tamper_detected_fail_closed"
        return Transition(action, d, s, r, _receipt(ctx.device_id, action, d, s, r))

    if not ctx.gnss_fresh and action in {"guide", "share_location"}:
        d, s, r = Decision.HOLD, SafetyState.GUARDIAN, "location_reference_stale"
        return Transition(action, d, s, r, _receipt(ctx.device_id, action, d, s, r))

    if ctx.sos_pressed or ctx.child_says_lost:
        current = SafetyState.GUARDIAN
    elif ctx.route_deviation and not ctx.guardian_present:
        current = SafetyState.ATTENTION
    else:
        current = ctx.safety_state

    inv = derive_invariants(Context(**{**asdict(ctx), "safety_state": current}), action)

    if action == "observe":
        d, r = Decision.PERMIT, "local_observation_only"
        return Transition(action, d, current, r, _receipt(ctx.device_id, action, d, current, r))

    if action == "guide":
        if current != SafetyState.GUARDIAN:
            d, r = Decision.HOLD, "guidance_not_needed"
        elif not inv.reference:
            d, r = Decision.HOLD, "no_verified_safe_destination"
        elif not inv.all_true():
            d, r = Decision.HOLD, "invariants_incomplete"
        else:
            d, r = Decision.PERMIT, "verified_local_safety_guidance"
        return Transition(action, d, current, r, _receipt(ctx.device_id, action, d, current, r))

    if action == "share_location":
        if current != SafetyState.GUARDIAN:
            d, r = Decision.HOLD, "not_in_emergency_state"
        elif not ctx.recipient_authorized:
            d, r = Decision.REJECT, "recipient_not_authorized"
        elif not (ctx.direct_radio_link or ctx.terrestrial_link or ctx.satellite_link):
            d, r = Decision.HOLD, "no_outbound_link_available"
        elif not inv.all_true():
            d, r = Decision.HOLD, "invariants_incomplete"
        else:
            d, r = Decision.PERMIT, "authorized_emergency_location_release"
        return Transition(action, d, current, r, _receipt(ctx.device_id, action, d, current, r))

    if action == "close_incident":
        d, s, r = Decision.PERMIT, SafetyState.RECOVERY, "authorized_recovery_transition"
        return Transition(action, d, s, r, _receipt(ctx.device_id, action, d, s, r))

    d, s, r = Decision.REJECT, current, "unknown_action"
    return Transition(action, d, s, r, _receipt(ctx.device_id, action, d, s, r))


def offline_capabilities(ctx: Context) -> List[str]:
    return [
        "boot",
        "local_identity",
        "gnss_position",
        "sensor_observation",
        "scqos_governance",
        "local_speech_interface",
        "offline_map_reference",
        "local_safety_guidance",
        "receipt_generation",
        "direct_radio_attempt",
        "terrestrial_or_satellite_attempt",
    ]
