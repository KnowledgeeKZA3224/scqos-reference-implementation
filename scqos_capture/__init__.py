"""Fail-closed primitives for governing durable state transitions.

These functions prepare and inspect transitions. They do not themselves grant
production authority or write to a database.
"""

from .boundary import (authority_decision, blast_radius, compare_shadow,
                       freeze_intent, precommit_decision, witness_effect)

__all__ = ["authority_decision", "blast_radius", "compare_shadow",
           "freeze_intent", "precommit_decision", "witness_effect"]
