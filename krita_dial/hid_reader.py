"""Background thread that reads the xPress and emits the InputSource signals.

Hotplug: if the device is missing or unplugged, it retries every RETRY_S seconds.
Signals are emitted from the reader thread; Qt queues them to the receivers in the main thread.
"""

from __future__ import annotations

import sys

from PyQt5.QtCore import QThread, pyqtSignal

from .log import log
from .xpress_report import Decoder

CONTOUR_VID = 0x0B33
XPRESS_PID = 0x0020
RETRY_S = 2.0
READ_TIMEOUT_MS = 100


class HidReader(QThread):
    # Same signals as InputSource, so Controller.attach works with both
    button = pyqtSignal(int, bool)
    jog = pyqtSignal(int)
    ring = pyqtSignal(int)
    status = pyqtSignal(str)  # human readable device status, for the docker

    def __init__(self, parent=None):
        super().__init__(parent)
        self.status_text = "starting"
        self.status.connect(self._remember_status)

    def _remember_status(self, text: str):
        self.status_text = text

    def stop(self):
        self.requestInterruption()
        self.wait(2000)

    def run(self):
        if sys.platform != "win32":
            self.status.emit("not supported on this platform (Windows only)")
            return
        try:
            from . import hid_device
        except Exception as e:
            log.exception("hid_device import failed")
            self.status.emit(f"error: {e}")
            return

        reported_missing = False
        while not self.isInterruptionRequested():
            try:
                devices = hid_device.enumerate_devices(CONTOUR_VID, XPRESS_PID)
            except Exception as e:
                log.warning(f"HID enumeration failed: {e!r}")
                devices = []
            if not devices:
                if not reported_missing:
                    log.info("xPress not found, waiting")
                    self.status.emit("not connected")
                    reported_missing = True
                self._sleep(RETRY_S)
                continue
            reported_missing = False
            self._read_device(hid_device, devices[0])

        self.status.emit("stopped")

    def _read_device(self, hid_device, info):
        decoder = Decoder()
        try:
            device = hid_device.HidDevice(info)
        except Exception as e:
            log.warning(f"Cannot open controller: {e!r}")
            self.status.emit(f"cannot open: {e}")
            self._sleep(RETRY_S)
            return

        log.info(f"Controller opened: {info.product} ({info.path})")
        self.status.emit("connected")
        try:
            while not self.isInterruptionRequested():
                report = device.read(READ_TIMEOUT_MS)
                if report is None:
                    continue
                try:
                    events = decoder.feed(report)
                except ValueError as e:
                    log.warning(f"Bad report {report.hex(' ')}: {e}")
                    continue
                for event in events:
                    getattr(self, event[0]).emit(*event[1:])
        except hid_device.HidError as e:
            log.info(f"Controller disconnected: {e}")
            self.status.emit("disconnected")
        except Exception:
            log.exception("Controller reader failed")
            self.status.emit("error, see log")
        finally:
            device.close()
            self.ring.emit(0)  # never leave the ring "held": the controller would keep repeating

    def _sleep(self, seconds: float):
        for _ in range(int(seconds * 10)):
            if self.isInterruptionRequested():
                return
            self.msleep(100)
