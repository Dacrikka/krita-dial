from krita import Extension, Krita

from .controller import get_controller
from .log import log


class DialExtension(Extension):
    def setup(self):
        log.info("Krita Dial starting")
        controller = get_controller()
        controller.start_device()
        notifier = Krita.instance().notifier()
        notifier.setActive(True)
        notifier.applicationClosing.connect(controller.shutdown)

    def createActions(self, window):
        pass
