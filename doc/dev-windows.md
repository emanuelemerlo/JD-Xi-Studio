# Working on JD-Xi Studio on Windows (Visual Studio 2026, VS Code)

## Once

1. Install **Python 3.11 or 3.12 (64-bit)** from python.org (tick "Add python.exe to PATH" and the `py` launcher).
   The same steps work on macOS and Linux with `python3 -m venv .venv` and `.venv/bin/python`.
2. Install **Git** (or GitHub Desktop) and clone `emanuelemerlo/JD-Xi-Studio`.
3. In the repository folder create the environment and install the editor with the test tools:

   ```powershell
   py -3 -m venv .venv
   .venv\Scripts\python -m pip install --upgrade pip
   .venv\Scripts\python -m pip install -e ".[soundfont,dev]" pyinstaller
   ```

   In VS Code the same is the task **Setup: create .venv and install** (Terminal → Run Task).
4. For the installer only: **Inno Setup 6** (https://jrsoftware.org/isdl.php).

## Visual Studio Code

Open the repository folder. The settings in `.vscode/` use `.venv`:

- **Run and Debug** (F5): *JD-Xi Studio*, *JD-Xi Studio (Italian)*, *JD-Xi Studio (English)*,
  *Tests: current file*.
- **Testing** panel: every pytest test, run or debug one at a time.
- **Terminal → Run Task**: *Run JD-Xi Studio*, *Tests: all*, *Translations: update, compile, check*,
  *Build: Windows exe (PyInstaller)*, *Build: installer (Inno Setup)*.
- Suggested extensions: Python, Python Debugger, Pylance, Black Formatter.

## Visual Studio 2026

Install the **Python development** workload, then open `JD-Xi-Studio.sln`.

- The project uses the `.venv` environment (Solution Explorer → Python Environments); create it
  first as above.
- **F5** starts JD-Xi Studio (`run_editor.py`); **Test Explorer** lists the pytest tests.
- For the exe or the installer use the PowerShell script below (Tools → Command Line →
  Developer PowerShell).

## The Windows exe and the installer on your PC

```powershell
powershell -ExecutionPolicy Bypass -File building\windows\local_build.ps1             # exe in dist\JD-Xi-Studio
powershell -ExecutionPolicy Bypass -File building\windows\local_build.ps1 -Installer  # and dist\installer
```

It does what the GitHub workflow does, in its own environment (`.venv-build`, a normal install:
the wheel build puts the resources inside the package that the exe bundles).

## Running from a terminal

Always from the repository folder, with the project's environment:

```powershell
.venv\Scripts\python -m jdxi_editor.main      # Windows
.venv/bin/python -m jdxi_editor.main            # macOS, Linux
```

Running the file (`python jdxi_editor/main.py`, VS Code's "Run Python File") also works: it uses
this folder's code even when another copy of the editor is installed.

## UI audit

`python scripts/ui_audit.py` (VS Code task *UI audit*) opens the app without a JD-Xi and checks, with no
clicking by hand: every panel button and menu entry opens the right tab, brings the editors window up
and lights the right button; no text on the panel is cut, no control overlaps another or sticks out;
showing an editor stays fast. One line per problem. Try it at another scale:
`$env:QT_SCALE_FACTOR=1.5; $env:QT_FONT_DPI=120; python scripts\ui_audit.py`. The tests run it at
100% and 150% on every push (Windows, macOS, Linux).

## Useful switches

- `JDXI_LANGUAGE=it` or `en`: the interface language, whatever the system one.
- `QT_SCALE_FACTOR=1.5`: try the interface at another display scale.
- `JDXI_PROFILE=1`: profile the session and print the report when the app closes (off by default:
  Python allows one profiler, and a debugger counts as one).
- Settings are in the registry under `HKEY_CURRENT_USER\Software\mabsoft\JD-Xi Editor`; the log and
  recipes in `%USERPROFILE%\.jdxi_editor`.
