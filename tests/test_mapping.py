"""Mapping tests. Run from the project root: python -m unittest discover tests"""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

# Load mapping.py directly: importing the package would import krita
_path = Path(__file__).parent.parent / "krita_dial" / "mapping.py"
_spec = importlib.util.spec_from_file_location("mapping", _path)
mapping = importlib.util.module_from_spec(_spec)
sys.modules["mapping"] = mapping
_spec.loader.exec_module(mapping)
Mapping = mapping.Mapping


def write_user(data) -> Path:
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    if isinstance(data, str):
        f.write(data)
    else:
        json.dump(data, f)
    f.close()
    return Path(f.name)


class DefaultMappingTest(unittest.TestCase):
    def setUp(self):
        self.m, self.errors = Mapping.load(None)

    def test_default_is_valid(self):
        self.assertEqual(self.errors, [])

    def test_buttons(self):
        self.assertEqual(self.m.button(None, 1), {"action": "ai.generate"})
        self.assertEqual(self.m.button("generation", 2), {"action": "ai.apply"})
        self.assertIsNone(self.m.button(None, 9))

    def test_workspace_override(self):
        self.assertEqual(self.m.jog("generation")["action"], "ai.history")
        self.assertEqual(self.m.jog("live")["action"], "ai.seed_scroll")
        # Not overridden in live: inherited from default
        self.assertEqual(self.m.ring("live")["action"], "ai.strength")
        self.assertEqual(self.m.button("live", 1), {"action": "ai.generate"})

    def test_unknown_workspace_uses_default(self):
        self.assertEqual(self.m.jog("nonexistent")["action"], "ai.history")


class UserMappingTest(unittest.TestCase):
    def test_binding_replaced_not_merged(self):
        path = write_user({"default": {"ring": {"action": "ai.history"}}})
        m, errors = Mapping.load(path)
        self.assertEqual(errors, [])
        self.assertEqual(m.ring(None), {"action": "ai.history"})  # no leftover "step"

    def test_single_button_override_keeps_others(self):
        path = write_user({"default": {"buttons": {"3": {"action": "ai.cancel"}}}})
        m, _ = Mapping.load(path)
        self.assertEqual(m.button(None, 3), {"action": "ai.cancel"})
        self.assertEqual(m.button(None, 1), {"action": "ai.generate"})

    def test_null_disables(self):
        path = write_user({"workspaces": {"live": {"ring": None}}})
        m, errors = Mapping.load(path)
        self.assertEqual(errors, [])
        self.assertIsNone(m.ring("live"))
        self.assertIsNotNone(m.ring("generation"))

    def test_broken_json_falls_back_to_default(self):
        path = write_user("{ not json")
        m, errors = Mapping.load(path)
        self.assertEqual(len(errors), 1)
        self.assertEqual(m.button(None, 1), {"action": "ai.generate"})

    def test_invalid_binding_reported(self):
        path = write_user({"default": {"jog": {"step": 1}, "buttons": {"7": {"action": "ai.apply"}}}})
        _, errors = Mapping.load(path)
        self.assertEqual(len(errors), 2)

    def test_unknown_action_reported(self):
        m, _ = Mapping.load(write_user({"default": {"jog": {"action": "ai.nope"}}}))
        errors = m.validate({"ai.generate", "ai.apply"})
        self.assertTrue(any("ai.nope" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
