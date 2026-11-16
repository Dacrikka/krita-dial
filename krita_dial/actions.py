"""Actions that a binding can name in the mapping file.

Each action is called as fn(bridge, binding, value):
- buttons: value is None (called on press)
- jog: value is the number of ticks turned (negative = left)
- ring: value is the ring position -7..7, repeated every binding["repeat_ms"] while held
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .ai_bridge import AIBridge

ActionFn = Callable[[AIBridge, dict, Any], None]


def _strength(bridge: AIBridge, binding: dict, value):
    bridge.add_strength(float(binding.get("step", 0.01)) * (value or 0))


def _krita_action(bridge: AIBridge, binding: dict, value):
    bridge.trigger(binding["name"])


ACTIONS: dict[str, ActionFn] = {
    "ai.generate": lambda b, _, __: b.generate(),
    "ai.apply": lambda b, _, __: b.apply(),
    "ai.cancel": lambda b, _, __: b.cancel(),
    "ai.new_seed": lambda b, _, __: b.new_seed(),
    "ai.toggle_live": lambda b, _, __: b.toggle_live(),
    "ai.strength": _strength,
    "ai.history": lambda b, _, value: b.history_step(int(value or 0)),
    "ai.seed_scroll": lambda b, _, value: b.seed_scroll(int(value or 0)),
    "krita.action": _krita_action,
}
