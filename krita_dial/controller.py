from __future__ import annotations

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from .actions import ACTIONS
from .ai_bridge import AIBridge
from .input_source import InputSource
from .log import app_data_dir, log
from .mapping import Mapping


def user_mapping_path():
    return app_data_dir() / "krita_dial.json"


class Controller(QObject):
    """Receives control events from input sources and runs the mapped actions."""

    event_handled = pyqtSignal(str)  # human readable description, for the docker

    def __init__(self):
        super().__init__()
        self.bridge = AIBridge()
        self.mapping: Mapping
        self.mapping_errors: list[str] = []
        self._sources: list[QObject] = []
        self.reader = None  # HidReader, created by start_device()
        self._ring_pos = 0
        self._ring_timer = QTimer(self)
        self._ring_timer.timeout.connect(self._ring_tick)
        self.reload_mapping()

    def reload_mapping(self):
        self.mapping, errors = Mapping.load(user_mapping_path())
        errors += self.mapping.validate(set(ACTIONS))
        self.mapping_errors = errors
        for e in errors:
            log.warning(f"mapping: {e}")
        log.info(f"Mapping loaded ({user_mapping_path()}, {len(errors)} errors)")

    def start_device(self):
        from .hid_reader import HidReader

        self.reader = HidReader(self)
        self.attach(self.reader)
        self.reader.start()

    def shutdown(self):
        self._ring_timer.stop()
        if self.reader is not None:
            self.reader.stop()

    def attach(self, source: InputSource | QObject):
        source.button.connect(self.on_button)
        source.jog.connect(self.on_jog)
        source.ring.connect(self.on_ring)
        self._sources.append(source)

    # --- events ---

    def on_button(self, index: int, pressed: bool):
        if pressed:
            ws = self.bridge.workspace()
            self._run(self.mapping.button(ws, index), None, f"button {index}")

    def on_jog(self, delta: int):
        if delta:
            ws = self.bridge.workspace()
            self._run(self.mapping.jog(ws), delta, f"jog {delta:+d}")

    def on_ring(self, position: int):
        self._ring_pos = position
        binding = self.mapping.ring(self.bridge.workspace())
        repeat_ms = int(binding.get("repeat_ms", 0)) if binding else 0
        if position == 0:
            self._ring_timer.stop()
            if binding and repeat_ms == 0:
                self._run(binding, 0, "ring 0")
            return
        if repeat_ms == 0:
            self._run(binding, position, f"ring {position:+d}")
        elif not self._ring_timer.isActive():
            # Run once on leaving the center, then only on timer ticks with the current position.
            # Position changes while held don't run the action: when released, the ring springs back
            # through every position in ~20 ms, and each would otherwise add its own step.
            self._run(binding, position, f"ring {position:+d}")
            self._ring_timer.start(repeat_ms)

    def _ring_tick(self):
        binding = self.mapping.ring(self.bridge.workspace())
        if self._ring_pos == 0 or not binding:
            self._ring_timer.stop()
            return
        self._run(binding, self._ring_pos, None)

    def _run(self, binding: dict | None, value, label: str | None):
        if not binding:
            return
        name = binding.get("action")
        fn = ACTIONS.get(name)
        if fn is None:
            log.warning(f"{label}: unknown action '{name}'")
            return
        try:
            fn(self.bridge, binding, value)
        except Exception:
            log.exception(f"{label or 'ring repeat'}: action '{name}' failed")
            return
        if label:  # repeats are not reported, they would flood the docker
            self.event_handled.emit(f"{label} → {name}")


_controller: Controller | None = None


def get_controller() -> Controller:
    global _controller
    if _controller is None:
        _controller = Controller()
    return _controller
