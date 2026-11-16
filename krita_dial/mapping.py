"""Mapping configuration: which action each control triggers, optionally per AI workspace.

Pure Python (no Krita/Qt imports) so it can be unit tested outside Krita.

File format (JSON):
{
  "version": 1,
  "default": {
    "buttons": {"1": {"action": "ai.generate"}, ...},
    "jog": {"action": "ai.history"},
    "ring": {"action": "ai.strength", "step": 0.01, "repeat_ms": 100}
  },
  "workspaces": {
    "live": {"jog": {"action": "ai.seed_scroll"}}
  }
}

A binding is a dict with an "action" key plus action parameters, or null to disable a control.
Workspace sections override the default section control by control (and button by button).
A binding always replaces the previous one entirely: parameters are never mixed between bindings.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

BUTTON_COUNT = 5
DEFAULT_PATH = Path(__file__).with_name("default_mapping.json")

Binding = dict[str, Any]


def _is_binding(value: Any) -> bool:
    return value is None or (isinstance(value, dict) and "action" in value)


def _is_binding_slot(key: str, parent: str | None) -> bool:
    return key in ("jog", "ring") or parent == "buttons"


def _merge(base: dict, override: dict, parent: str | None = None) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        replace = _is_binding_slot(key, parent) or not isinstance(value, dict)
        if not replace and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value, key)
        else:
            result[key] = copy.deepcopy(value)
    return result


class Mapping:
    def __init__(self, data: dict):
        self.data = data

    @staticmethod
    def load(user_path: Path | None = None) -> tuple[Mapping, list[str]]:
        """Load the bundled default, then overlay the user file if it exists.
        Errors in the user file are returned, not raised: the default mapping stays usable."""
        data = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        errors: list[str] = []
        if user_path is not None and user_path.exists():
            try:
                user = json.loads(user_path.read_text(encoding="utf-8"))
                if not isinstance(user, dict):
                    raise ValueError("top level must be a JSON object")
                data = _merge(data, user)
            except Exception as e:
                errors.append(f"{user_path}: {e}")
        mapping = Mapping(data)
        errors += mapping.validate()
        return mapping, errors

    def resolve(self, workspace: str | None) -> dict:
        section = copy.deepcopy(self.data.get("default", {}))
        if workspace:
            override = self.data.get("workspaces", {}).get(workspace)
            if isinstance(override, dict):
                section = _merge(section, override)
        return section

    def button(self, workspace: str | None, index: int) -> Binding | None:
        return self.resolve(workspace).get("buttons", {}).get(str(index))

    def jog(self, workspace: str | None) -> Binding | None:
        return self.resolve(workspace).get("jog")

    def ring(self, workspace: str | None) -> Binding | None:
        return self.resolve(workspace).get("ring")

    def bindings(self):
        """All (location, binding) pairs, for validation and display."""
        sections = [("default", self.data.get("default", {}))]
        sections += [(f"workspaces.{k}", v) for k, v in self.data.get("workspaces", {}).items()]
        for name, section in sections:
            if not isinstance(section, dict):
                continue
            for index, binding in section.get("buttons", {}).items():
                yield f"{name}.buttons.{index}", binding
            for control in ("jog", "ring"):
                if control in section:
                    yield f"{name}.{control}", section[control]

    def validate(self, known_actions: set[str] | None = None) -> list[str]:
        errors = []
        for location, binding in self.bindings():
            if not _is_binding(binding):
                errors.append(f"{location}: binding must be null or an object with an 'action' key")
            elif binding is not None and known_actions is not None:
                if binding["action"] not in known_actions:
                    errors.append(f"{location}: unknown action '{binding['action']}'")
        if "default" in self.data:
            for index in self.data["default"].get("buttons", {}):
                if not (index.isdigit() and 1 <= int(index) <= BUTTON_COUNT):
                    errors.append(f"default.buttons.{index}: buttons are numbered 1-{BUTTON_COUNT}")
        return errors
