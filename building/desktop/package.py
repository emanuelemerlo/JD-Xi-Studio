"""
The packages for macOS and Linux, from what PyInstaller built with
building/desktop/jdxi_studio.spec:

    python -m building.desktop.package dmg   # dist/JD-Xi Studio.app -> dist/JD-Xi-Studio-<v>-macos-<arch>.dmg
    python -m building.desktop.package deb   # dist/JD-Xi-Studio/    -> dist/jd-xi-studio_<v>_amd64.deb

Options: --dist (default: dist), --out (default: the same folder).
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from jdxi_editor.project import __program__, __version__, package_version  # noqa: E402

DEB_NAME = "jd-xi-studio"
APP_FOLDER = "JD-Xi-Studio"
SUMMARY = "Editor and librarian for the Roland JD-Xi synthesizer"
HOMEPAGE = "https://github.com/emanuelemerlo/JD-Xi-Studio"
MAINTAINER = "Emanuele Merlo <emanuelemerlo@users.noreply.github.com>"
# What the bundle does not carry: ALSA (MIDI), and the libraries Qt's xcb
# platform plugin and OpenGL take from the system. libasound2 was renamed
# libasound2t64 in Ubuntu 24.04 / Debian 13.
DEB_DEPENDS = (
    "libasound2 | libasound2t64, libegl1, libgl1, libfontconfig1, libdbus-1-3, "
    "libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, "
    "libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-xinerama0, libxcb-xkb1"
)


def run(*cmd: str) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def make_dmg(dist: Path, out: Path) -> Path:
    """A disk image with the app and a link to Applications (drag to install)."""
    app = dist / "JD-Xi Studio.app"
    if not app.is_dir():
        raise SystemExit(f"{app} not found: build it first with building/desktop/jdxi_studio.spec")
    arch = platform.machine() or "arm64"
    image = out / f"{APP_FOLDER}-{__version__}-macos-{arch}.dmg"
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "JD-Xi Studio"
        stage.mkdir()
        # ditto keeps the bundle's symlinks, permissions and signature
        run("ditto", str(app), str(stage / app.name))
        os.symlink("/Applications", stage / "Applications")
        image.unlink(missing_ok=True)
        run("hdiutil", "create", "-volname", f"{__program__} {__version__}", "-srcfolder", str(stage),
            "-fs", "HFS+", "-format", "UDZO", "-ov", str(image))
    print(f"Disk image: {image}")
    return image


def _desktop_entry() -> str:
    return (
        "[Desktop Entry]\n"
        f"Name={__program__}\n"
        f"Comment={SUMMARY}\n"
        f"Exec=/opt/{DEB_NAME}/{APP_FOLDER} %F\n"
        f"Icon={DEB_NAME}\n"
        "Terminal=false\n"
        "Type=Application\n"
        "Categories=AudioVideo;Audio;Midi;Music;\n"
        "Keywords=MIDI;Synthesizer;Roland;JD-Xi;Editor;\n"
        f"StartupWMClass={APP_FOLDER}\n"
    )


def make_deb(dist: Path, out: Path) -> Path:
    """A .deb that installs the app in /opt/jd-xi-studio, with a launcher in
    /usr/bin, a menu entry and its icon."""
    folder = dist / APP_FOLDER
    if not (folder / APP_FOLDER).is_file():
        raise SystemExit(f"{folder}/{APP_FOLDER} not found: build it first with building/desktop/jdxi_studio.spec")
    from PIL import Image

    version = package_version(__version__)
    package = out / f"{DEB_NAME}_{version}_amd64.deb"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "root"
        shutil.copytree(folder, root / "opt" / DEB_NAME, symlinks=True)
        bin_dir = root / "usr" / "bin"
        bin_dir.mkdir(parents=True)
        os.symlink(f"/opt/{DEB_NAME}/{APP_FOLDER}", bin_dir / DEB_NAME)
        apps = root / "usr" / "share" / "applications"
        apps.mkdir(parents=True)
        (apps / f"{DEB_NAME}.desktop").write_text(_desktop_entry(), encoding="utf-8")
        icon = Image.open(ROOT / "resources" / "jdxi_icon_512.png").convert("RGBA")
        for size in (48, 64, 128, 256, 512):
            target = root / "usr" / "share" / "icons" / "hicolor" / f"{size}x{size}" / "apps"
            target.mkdir(parents=True)
            icon.resize((size, size), Image.LANCZOS).save(target / f"{DEB_NAME}.png")
        size_kb = sum(f.stat().st_size for f in root.rglob("*") if f.is_file() and not f.is_symlink()) // 1024
        debian = root / "DEBIAN"
        debian.mkdir()
        (debian / "control").write_text(
            f"Package: {DEB_NAME}\n"
            f"Version: {version}\n"
            "Section: sound\n"
            "Priority: optional\n"
            "Architecture: amd64\n"
            f"Installed-Size: {size_kb}\n"
            f"Depends: {DEB_DEPENDS}\n"
            f"Maintainer: {MAINTAINER}\n"
            f"Homepage: {HOMEPAGE}\n"
            f"Description: {SUMMARY}\n"
            " JD-Xi Studio edits the sounds of the Roland JD-Xi (Digital, Analog,\n"
            " Drums, effects, arpeggio, vocal effects), its programs and patterns,\n"
            " and plays MIDI files on it.\n",
            encoding="utf-8",
        )
        for script, body in (
            ("postinst", "update-desktop-database -q /usr/share/applications 2>/dev/null || true\n"
                         "gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true\n"),
            ("postrm", "update-desktop-database -q /usr/share/applications 2>/dev/null || true\n"),
        ):
            path = debian / script
            path.write_text("#!/bin/sh\nset -e\n" + body, encoding="utf-8")
            path.chmod(0o755)
        package.unlink(missing_ok=True)
        run("dpkg-deb", "--build", "--root-owner-group", "-Zxz", str(root), str(package))
    print(f"Package: {package}")
    return package


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=("dmg", "deb"))
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    out = args.out or args.dist
    out.mkdir(parents=True, exist_ok=True)
    (make_dmg if args.kind == "dmg" else make_deb)(args.dist.resolve(), out.resolve())


if __name__ == "__main__":
    main()
