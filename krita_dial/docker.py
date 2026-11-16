from krita import DockWidget
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .controller import get_controller, user_mapping_path
from .input_source import InputSource
from .mapping import BUTTON_COUNT

RING_RANGE = 7


class SimulatorWidget(QGroupBox):
    """On-screen stand-in for the xPress: 5 buttons, jog wheel, spring-loaded ring."""

    def __init__(self, source: InputSource, parent=None):
        super().__init__("Simulator", parent)
        self.source = source
        layout = QVBoxLayout(self)

        buttons = QHBoxLayout()
        for i in range(1, BUTTON_COUNT + 1):
            b = QPushButton(str(i))
            b.setFixedWidth(32)
            b.pressed.connect(lambda i=i: source.button.emit(i, True))
            b.released.connect(lambda i=i: source.button.emit(i, False))
            buttons.addWidget(b)
        layout.addLayout(buttons)

        jog = QHBoxLayout()
        jog.addWidget(QLabel("Jog"))
        for text, delta in (("◀◀", -5), ("◀", -1), ("▶", 1), ("▶▶", 5)):
            b = QPushButton(text)
            b.setAutoRepeat(True)  # hold to keep turning
            b.setAutoRepeatInterval(150)
            b.clicked.connect(lambda _=False, d=delta: source.jog.emit(d))
            jog.addWidget(b)
        layout.addLayout(jog)

        ring = QHBoxLayout()
        ring.addWidget(QLabel("Ring"))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(-RING_RANGE, RING_RANGE)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.setPageStep(1)
        self.slider.valueChanged.connect(source.ring.emit)
        self.slider.sliderReleased.connect(lambda: self.slider.setValue(0))  # spring back like the real ring
        ring.addWidget(self.slider)
        layout.addLayout(ring)


class DialDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Krita Dial")
        self.controller = get_controller()

        root = QWidget(self)
        layout = QVBoxLayout(root)

        status = QGridLayout()
        self.labels = {}
        for row, (key, title) in enumerate(
            [("device", "Controller"), ("ai", "AI Diffusion"), ("workspace", "Workspace"), ("strength", "Strength"),
             ("seed", "Seed"), ("history", "Result"), ("event", "Last input")]
        ):
            status.addWidget(QLabel(title), row, 0)
            self.labels[key] = QLabel("–")
            status.addWidget(self.labels[key], row, 1)
        layout.addLayout(status)

        self.source = InputSource(self)
        self.controller.attach(self.source)
        layout.addWidget(SimulatorWidget(self.source))

        config = QHBoxLayout()
        reload_button = QPushButton("Reload mapping")
        reload_button.clicked.connect(self._reload)
        open_button = QPushButton("Open folder")
        open_button.clicked.connect(self._open_folder)
        config.addWidget(reload_button)
        config.addWidget(open_button)
        layout.addLayout(config)

        self.errors = QLabel()
        self.errors.setWordWrap(True)
        self.errors.setStyleSheet("color: #d66;")
        layout.addWidget(self.errors)
        layout.addStretch()
        self.setWidget(root)

        self.controller.event_handled.connect(lambda text: self.labels["event"].setText(text))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(250)
        self._show_errors()

    def canvasChanged(self, canvas):
        pass

    def _refresh(self):
        if not self.isVisible():
            return
        reader = self.controller.reader
        self.labels["device"].setText(reader.status_text if reader else "–")
        s = self.controller.bridge.state()
        if not s.get("available"):
            self.labels["ai"].setText("not found (Krita fallback)")
            return
        self.labels["ai"].setText(s.get("version") or "?")
        self.labels["workspace"].setText(
            f"{s.get('workspace', '–')}" + (" ● live on" if s.get("live_active") else "")
        )
        strength = s.get("strength")
        self.labels["strength"].setText(f"{strength * 100:.0f}%" if strength is not None else "–")
        self.labels["seed"].setText(str(s.get("seed", "–")))
        history = s.get("history")
        self.labels["history"].setText(f"{history[0]} / {history[1]}" if history else "–")

    def _reload(self):
        self.controller.bridge.reset()
        self.controller.reload_mapping()
        self._show_errors()

    def _show_errors(self):
        self.errors.setText("\n".join(self.controller.mapping_errors))

    def _open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(user_mapping_path().parent)))
