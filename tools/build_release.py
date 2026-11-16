"""Build the release zip for Krita's "Import Python Plugin from File".

Layout expected by Krita: the .desktop file and the package folder at the top level of the zip.
The license goes inside the package folder, because Krita installs only the package and the .desktop file.

Usage: python tools/build_release.py   ->   dist/krita_dial-<version>.zip
"""

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "krita_dial"
EXCLUDE_DIRS = {"__pycache__"}
EXCLUDE_SUFFIXES = {".pyc", ".log"}


def version() -> str:
    text = (ROOT / PACKAGE / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"', text, re.MULTILINE)
    if not match:
        sys.exit(f"__version__ not found in {PACKAGE}/__init__.py")
    return match.group(1)


def package_files():
    for path in sorted((ROOT / PACKAGE).rglob("*")):
        rel = path.relative_to(ROOT)
        if path.is_file() and not EXCLUDE_DIRS & set(rel.parts) and path.suffix not in EXCLUDE_SUFFIXES:
            yield path, rel.as_posix()


def main():
    out = ROOT / "dist" / f"{PACKAGE}-{version()}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(ROOT / f"{PACKAGE}.desktop", f"{PACKAGE}.desktop")
        for path, name in package_files():
            z.write(path, name)
        z.write(ROOT / "LICENSE", f"{PACKAGE}/LICENSE")
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    print(f"{out} ({out.stat().st_size} bytes, {len(names)} files)")
    for name in names:
        print(f"  {name}")


if __name__ == "__main__":
    main()
