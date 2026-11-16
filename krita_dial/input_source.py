from PyQt5.QtCore import QObject, pyqtSignal


class InputSource(QObject):
    """Common interface for the real device (HID reader, later) and the simulator.

    Signals must be emitted in the Qt main thread, or connected with a queued connection
    (default for cross-thread signals), because actions touch Krita and AI Diffusion state.
    """

    button = pyqtSignal(int, bool)  # index 1-5, pressed
    jog = pyqtSignal(int)  # ticks since last event, negative = left
    ring = pyqtSignal(int)  # ring position -7..7, 0 = released
