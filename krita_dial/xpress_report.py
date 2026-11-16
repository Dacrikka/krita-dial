"""Decode xPress input reports into control events. Pure Python, unit tested.

Report layout (6 bytes with report ID, verified 27/10/2026 on PID 0020, see spike/hid_dump.log):
  [0] report ID (0)
  [1] ring, signed -7..7 (0 = released)
  [2] jog counter 0..255, wraps around; one step per detent
  [3] unused
  [4] buttons 1-4 in bits 0x10, 0x20, 0x40, 0x80
  [5] button 5 in bit 0x01
The device sends a report only when something changes.
"""

from __future__ import annotations

from dataclasses import dataclass

BUTTON_BITS = [(4, 0x10), (4, 0x20), (4, 0x40), (4, 0x80), (5, 0x01)]  # (byte, mask) for buttons 1-5


@dataclass(frozen=True)
class State:
    ring: int
    jog: int
    buttons: tuple[bool, ...]


def parse(report: bytes) -> State:
    if len(report) < 6:
        raise ValueError(f"report too short: {len(report)} bytes")
    ring = report[1] - 256 if report[1] > 127 else report[1]
    buttons = tuple(bool(report[b] & mask) for b, mask in BUTTON_BITS)
    return State(ring, report[2], buttons)


def jog_delta(previous: int, current: int) -> int:
    """Signed difference of the 8-bit counter, handling wrap-around (255 -> 0 is +1)."""
    d = (current - previous) & 0xFF
    return d - 256 if d > 127 else d


class Decoder:
    """Turns successive reports into events: ("button", index, pressed), ("jog", delta), ("ring", pos).
    The first report only sets the baseline: the jog counter has an arbitrary starting value."""

    def __init__(self):
        self._state: State | None = None

    def reset(self):
        self._state = None

    def feed(self, report: bytes) -> list[tuple]:
        new = parse(report)
        old = self._state
        self._state = new
        if old is None:
            old = State(0, new.jog, (False,) * len(new.buttons))

        events: list[tuple] = []
        for i, (was, now) in enumerate(zip(old.buttons, new.buttons), start=1):
            if was != now:
                events.append(("button", i, now))
        if d := jog_delta(old.jog, new.jog):
            events.append(("jog", d))
        if old.ring != new.ring:
            events.append(("ring", new.ring))
        return events
