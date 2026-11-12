# Working on JD-Xi Studio on Windows (Visual Studio 2026, VS Code)

## Once

1. Install **Python 3.11 (64-bit)** from python.org (tick "Add python.exe to PATH" and the `py` launcher).
2. Install **Git** (or GitHub Desktop) and clone `emanuelemerlo/JDXI-Editor`.
3. In the repository folder create the environment and install the editor with the test tools:

   ```powershell
   py -3.11 -m venv .venv
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
powershell -ExecutionPolicy Bypass -File building\windows\local_build.ps1             # exe in dist\jdxi_editor
powershell -ExecutionPolicy Bypass -File building\windows\local_build.ps1 -Installer  # and dist\installer
```

It does what the GitHub workflow does, in its own environment (`.venv-build`, a normal install:
the wheel build puts the resources inside the package that the exe bundles).

## Useful switches

- `JDXI_LANGUAGE=it` or `en`: the interface language, whatever the system one.
- `QT_SCALE_FACTOR=1.5`: try the interface at another display scale.
- Settings are in the registry under `HKEY_CURRENT_USER\Software\mabsoft\JD-Xi Editor`; the log and
  recipes in `%USERPROFILE%\.jdxi_editor`.
