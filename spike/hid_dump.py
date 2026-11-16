"""Spike HID: list Contour devices and dump raw input reports.
Usage: python spike/hid_dump.py [seconds]   (default 40)
Prints a line only when the report changes."""

import importlib.util
import sys
import time
from pathlib import Path

_path = Path(__file__).parent.parent / "krita_dial" / "hid_device.py"
_spec = importlib.util.spec_from_file_location("hid_device", _path)
hid = importlib.util.module_from_spec(_spec)
sys.modules["hid_device"] = hid
_spec.loader.exec_module(hid)

CONTOUR_VID = 0x0B33
seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 40

devices = hid.enumerate_devices(CONTOUR_VID)
print(f"Contour devices: {len(devices)}", flush=True)
for d in devices:
    print(
        f"  PID {d.product_id:04X} '{d.product}' usage {d.usage_page:04X}:{d.usage:04X} "
        f"input report {d.input_report_length} bytes\n  {d.path}",
        flush=True,
    )
if not devices:
    sys.exit(1)

with hid.HidDevice(devices[0]) as dev:
    print(f"Opened. Reading for {seconds:.0f}s...", flush=True)
    t0 = time.monotonic()
    last = None
    count = 0
    while time.monotonic() - t0 < seconds:
        report = dev.read(100)
        if report is None:
            continue
        count += 1
        if report != last:
            print(f"{time.monotonic() - t0:6.2f}s  {report.hex(' ')}", flush=True)
            last = report
    print(f"Done: {count} reports", flush=True)
