from krita import DockWidgetFactory, DockWidgetFactoryBase, Krita

from . import log
from .docker import DialDocker
from .extension import DialExtension

__version__ = "0.1.0"

log.setup()
Krita.instance().addExtension(DialExtension(Krita.instance()))
Krita.instance().addDockWidgetFactory(
    DockWidgetFactory("kritaDial", DockWidgetFactoryBase.DockRight, DialDocker)
)
