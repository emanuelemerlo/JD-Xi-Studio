#!/usr/bin/env bash
# JD-Xi Studio installer for Linux and macOS.
#
# Works with the bash 3.2 of macOS (no negative indexes, no mapfile).
#
# Installs the newest release (or the one given) in its own Python environment
# and adds it to the applications: the menu on Linux, ~/Applications on macOS.
# Nothing is installed system-wide and nothing needs sudo; the libraries the
# system must provide are checked and, if missing, the command to install them
# is shown.
#
#   ./install.sh                      newest release (alpha and beta included)
#   ./install.sh --version v1.0.0-beta.1
#   ./install.sh --wheel path/to/jdxi_editor-X-py3-none-any.whl
#   ./install.sh --uninstall          remove the app (settings and patches stay)
#
# Or without cloning:
#   curl -fsSL https://raw.githubusercontent.com/emanuelemerlo/JD-Xi-Studio/main/install.sh | bash

set -euo pipefail

REPO="emanuelemerlo/JD-Xi-Studio"
APP="JD-Xi Studio"

say() { printf '\033[1m%s\033[0m\n' "$*"; }
fail() { printf '\033[31m%s\033[0m\n' "$*" >&2; exit 1; }

version="" wheel="" uninstall=0
while [ $# -gt 0 ]; do
    case "$1" in
        --version) version="${2:?--version needs a tag, e.g. v1.0.0-beta.1}"; shift 2 ;;
        --wheel) wheel="${2:?--wheel needs a file}"; shift 2 ;;
        --uninstall) uninstall=1; shift ;;
        -h|--help) echo "Usage: install.sh [--version TAG] [--wheel FILE] [--uninstall]"; exit 0 ;;
        *) fail "Unknown option: $1 (see --help)" ;;
    esac
done

case "$(uname -s)" in
    Linux)
        OS=linux
        HOME_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/jdxi-studio"
        BIN_LINK="$HOME/.local/bin/jdxi-studio"
        DESKTOP="${XDG_DATA_HOME:-$HOME/.local/share}/applications/jdxi-studio.desktop"
        ;;
    Darwin)
        OS=macos
        HOME_DIR="$HOME/Library/Application Support/JD-Xi-Studio"
        BIN_LINK="$HOME/.local/bin/jdxi-studio"
        APP_BUNDLE="$HOME/Applications/$APP.app"
        ;;
    *) fail "This script is for Linux and macOS; on Windows use the installer of the release." ;;
esac
VENV="$HOME_DIR/venv"

if [ "$uninstall" = 1 ]; then
    rm -rf "$VENV" "$BIN_LINK"
    if [ "$OS" = linux ]; then rm -f "$DESKTOP"; else rm -rf "$APP_BUNDLE"; fi
    rmdir "$HOME_DIR" 2>/dev/null || true
    say "$APP removed (your settings and patches are kept)."
    exit 0
fi

# --- Python 3.10 to 3.13 -----------------------------------------------------
python=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1 &&
        "$candidate" -c 'import sys; sys.exit(not ((3, 10) <= sys.version_info[:2] <= (3, 13)))' 2>/dev/null &&
        "$candidate" -c 'import venv, ensurepip' 2>/dev/null; then
        python="$(command -v "$candidate")"
        break
    fi
done
if [ -z "$python" ]; then
    if [ "$OS" = macos ]; then
        fail "Python 3.10-3.13 is needed: brew install python@3.12 (https://brew.sh)"
    fi
    fail "Python 3.10-3.13 with venv is needed, e.g.: sudo apt install python3 python3-venv python3-dev"
fi
say "Python: $python ($("$python" -c 'import platform; print(platform.python_version())'))"

# --- System libraries ----------------------------------------------------------
# PortAudio (with its headers) to build PyAudio; a C compiler; ALSA headers for
# python-rtmidi on Linux. FluidSynth is optional (the SoundFont player).
missing=() hints=()
if [ "$OS" = linux ]; then
    have_pc() { command -v pkg-config >/dev/null 2>&1 && pkg-config --exists "$1"; }
    command -v cc >/dev/null 2>&1 || missing+=("C compiler")
    have_pc portaudio-2.0 || missing+=("PortAudio")
    have_pc alsa || missing+=("ALSA headers")
    if command -v apt-get >/dev/null 2>&1; then
        hints+=("sudo apt install build-essential pkg-config portaudio19-dev libasound2-dev python3-dev python3-venv fluidsynth")
    elif command -v dnf >/dev/null 2>&1; then
        hints+=("sudo dnf install gcc pkgconf portaudio-devel alsa-lib-devel python3-devel fluidsynth")
    elif command -v pacman >/dev/null 2>&1; then
        hints+=("sudo pacman -S --needed base-devel pkgconf portaudio alsa-lib fluidsynth")
    elif command -v zypper >/dev/null 2>&1; then
        hints+=("sudo zypper install gcc pkg-config portaudio-devel alsa-devel python3-devel fluidsynth")
    else
        hints+=("install with your package manager: a C compiler, pkg-config, PortAudio and ALSA development files")
    fi
    fluid_ok() { ldconfig -p 2>/dev/null | grep -q libfluidsynth; }
else
    xcode-select -p >/dev/null 2>&1 || missing+=("Xcode command line tools")
    if command -v brew >/dev/null 2>&1; then
        brew --prefix portaudio >/dev/null 2>&1 && [ -d "$(brew --prefix portaudio)/include" ] || missing+=("PortAudio")
        hints+=("xcode-select --install   (if the command line tools are missing)")
        hints+=("brew install portaudio fluid-synth")
    else
        missing+=("Homebrew (for PortAudio)")
        hints+=("install Homebrew from https://brew.sh, then: brew install portaudio fluid-synth")
    fi
    fluid_ok() { command -v brew >/dev/null 2>&1 && [ -d "$(brew --prefix fluid-synth 2>/dev/null)/lib" ]; }
fi
if [ ${#missing[@]} -gt 0 ]; then
    printf '\033[31mMissing: %s\033[0m\nInstall them with:\n' "$(IFS=,; echo "${missing[*]}" | sed 's/,/, /g')" >&2
    for hint in "${hints[@]}"; do printf '  %s\n' "$hint" >&2; done
    exit 1
fi
fluid_ok || say "Note: FluidSynth not found; the editor works, the SoundFont player needs it (${hints[${#hints[@]}-1]})"

# --- The wheel -----------------------------------------------------------------
if [ -z "$wheel" ]; then
    if [ -n "$version" ]; then api="https://api.github.com/repos/$REPO/releases/tags/$version"
    else api="https://api.github.com/repos/$REPO/releases?per_page=1"; fi
    wheel=$(curl -fsSL "$api" | "$python" -c '
import json, sys
data = json.load(sys.stdin)
release = data[0] if isinstance(data, list) else data
urls = [a["browser_download_url"] for a in release["assets"] if a["name"].endswith(".whl")]
print(urls[0] if urls else "")
') || fail "Could not read the releases on GitHub (no network?)"
    [ -n "$wheel" ] || fail "No wheel in the release ${version:-(newest)}"
fi
say "Installing $(basename "$wheel")"

# --- Environment and package ---------------------------------------------------
mkdir -p "$HOME_DIR"
"$python" -m venv --clear "$VENV"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet "jdxi_editor[soundfont] @ $wheel" ||
    "$VENV/bin/python" -m pip install --quiet "$wheel" ||
    fail "pip could not install $APP (see the messages above)"
"$VENV/bin/python" -I -c "import jdxi_editor.main" || fail "$APP is installed but does not import"
version_installed=$("$VENV/bin/python" -I -c "from jdxi_editor.project import __version__; print(__version__)")

# -I: the installed package, never a source tree in the current folder
icon() {  # the app's icon inside the installed package ($1: png or icns)
    "$VENV/bin/python" -I - "$1" <<'PY'
import sys
from pathlib import Path
import jdxi_editor
root = Path(jdxi_editor.__file__).parent
found = sorted(root.rglob(f"jdxi_icon*.{sys.argv[1]}"), key=lambda p: -p.stat().st_size)
print(found[0] if found else "")
PY
}

# --- Launchers -----------------------------------------------------------------
mkdir -p "$(dirname "$BIN_LINK")"
ln -sf "$VENV/bin/jdxi-editor" "$BIN_LINK"

if [ "$OS" = linux ]; then
    mkdir -p "$(dirname "$DESKTOP")"
    cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=$APP
Comment=Editor for the Roland JD-Xi
Exec="$VENV/bin/jdxi-editor"
Icon=$(icon png)
Terminal=false
Categories=AudioVideo;Audio;Midi;Music;
StartupWMClass=jdxi-editor
EOF
    command -v update-desktop-database >/dev/null 2>&1 &&
        update-desktop-database "$(dirname "$DESKTOP")" >/dev/null 2>&1 || true
    where="the applications menu"
else
    # A small app bundle that starts the installed editor. Made here, so it has
    # no quarantine flag and opens without Gatekeeper's warning.
    rm -rf "$APP_BUNDLE"
    mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"
    cat > "$APP_BUNDLE/Contents/MacOS/JD-Xi-Studio" <<EOF
#!/bin/bash
exec "$VENV/bin/jdxi-editor" "\$@"
EOF
    chmod +x "$APP_BUNDLE/Contents/MacOS/JD-Xi-Studio"
    icns=$(icon icns)
    [ -n "$icns" ] && cp "$icns" "$APP_BUNDLE/Contents/Resources/JD-Xi-Studio.icns"
    cat > "$APP_BUNDLE/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>$APP</string>
  <key>CFBundleDisplayName</key><string>$APP</string>
  <key>CFBundleIdentifier</key><string>io.github.emanuelemerlo.jdxi-studio</string>
  <key>CFBundleVersion</key><string>$version_installed</string>
  <key>CFBundleShortVersionString</key><string>$version_installed</string>
  <key>CFBundleExecutable</key><string>JD-Xi-Studio</string>
  <key>CFBundleIconFile</key><string>JD-Xi-Studio</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
EOF
    where="~/Applications"
fi

say "$APP $version_installed installed: open it from $where, or run: jdxi-studio"
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) say "(add ~/.local/bin to PATH to use the jdxi-studio command)";; esac
if [ -f "$0" ]; then self="$0"; else self="curl -fsSL https://raw.githubusercontent.com/$REPO/main/install.sh | bash -s --"; fi
say "Update: run this script again. Remove: $self --uninstall"
