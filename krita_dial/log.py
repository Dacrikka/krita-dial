import logging
from pathlib import Path

from krita import Krita

log = logging.getLogger("krita_dial")


def app_data_dir() -> Path:
    """%APPDATA%\\krita on Windows: user config and log live here, not in the plugin folder."""
    return Path(Krita.instance().getAppDataLocation())


def setup():
    if log.handlers:
        return
    log.setLevel(logging.DEBUG)
    try:
        handler = logging.FileHandler(app_data_dir() / "krita_dial.log", "w", encoding="utf-8")
    except OSError:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
