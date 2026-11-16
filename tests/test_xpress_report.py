"""Report decoder tests, based on real reports from spike/hid_dump.log.
Run from the project root: python -m unittest discover tests"""

import importlib.util
import sys
import unittest
from pathlib import Path

_path = Path(__file__).parent.parent / "krita_dial" / "xpress_report.py"
_spec = importlib.util.spec_from_file_location("xpress_report", _path)
sr = importlib.util.module_from_spec(_spec)
sys.modules["xpress_report"] = sr
_spec.loader.exec_module(sr)


def r(text: str) -> bytes:
    return bytes.fromhex(text)


class ParseTest(unittest.TestCase):
    def test_buttons(self):
        for i, report in enumerate(
            ["00 00 00 00 10 00", "00 00 00 00 20 00", "00 00 00 00 40 00",
             "00 00 00 00 80 00", "00 00 00 00 00 01"]
        ):
            buttons = sr.parse(r(report)).buttons
            self.assertEqual([b for b in range(5) if buttons[b]], [i])

    def test_ring_signed(self):
        self.assertEqual(sr.parse(r("00 07 00 00 00 00")).ring, 7)
        self.assertEqual(sr.parse(r("00 f9 00 00 00 00")).ring, -7)
        self.assertEqual(sr.parse(r("00 ff 00 00 00 00")).ring, -1)

    def test_short_report(self):
        with self.assertRaises(ValueError):
            sr.parse(b"\x00\x01")

    def test_jog_wrap(self):
        self.assertEqual(sr.jog_delta(255, 0), 1)
        self.assertEqual(sr.jog_delta(0, 255), -1)
        self.assertEqual(sr.jog_delta(3, 6), 3)
        self.assertEqual(sr.jog_delta(6, 3), -3)


class DecoderTest(unittest.TestCase):
    def test_first_report_is_baseline(self):
        d = sr.Decoder()
        self.assertEqual(d.feed(r("00 00 2a 00 00 00")), [])  # jog counter starts at 42: no event
        self.assertEqual(d.feed(r("00 00 2b 00 00 00")), [("jog", 1)])

    def test_first_report_with_button_held(self):
        d = sr.Decoder()
        self.assertEqual(d.feed(r("00 00 00 00 10 00")), [("button", 1, True)])

    def test_button_press_release(self):
        d = sr.Decoder()
        d.feed(r("00 00 00 00 00 00"))
        self.assertEqual(d.feed(r("00 00 00 00 00 01")), [("button", 5, True)])
        self.assertEqual(d.feed(r("00 00 00 00 00 00")), [("button", 5, False)])

    def test_ring_spring_back(self):
        d = sr.Decoder()
        d.feed(r("00 00 00 00 00 00"))
        events = [d.feed(r(f"00 {p:02x} 00 00 00 00")) for p in (1, 2, 1, 0)]
        self.assertEqual(events, [[("ring", 1)], [("ring", 2)], [("ring", 1)], [("ring", 0)]])

    def test_button_held_while_jogging(self):
        d = sr.Decoder()
        d.feed(r("00 00 00 00 00 00"))
        self.assertEqual(d.feed(r("00 00 00 00 10 00")), [("button", 1, True)])
        self.assertEqual(d.feed(r("00 00 01 00 10 00")), [("jog", 1)])
        self.assertEqual(d.feed(r("00 00 06 00 00 00")), [("button", 1, False), ("jog", 5)])


if __name__ == "__main__":
    unittest.main()
