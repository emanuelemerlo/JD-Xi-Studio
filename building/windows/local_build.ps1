# Build the Windows exe (and the installer, with -Installer) on your PC, as the
# GitHub workflow does. Run from the repository folder:
#   powershell -ExecutionPolicy Bypass -File building\windows\local_build.ps1 [-Installer]
# Uses its own environment (.venv-build) with a normal (not editable) install:
# the wheel build puts the resources inside the package, which the spec bundles.
param([switch]$Installer)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $repo
$version = (Select-String -Path jdxi_editor/project.py -Pattern '__version__ = "([^"]+)"').Matches[0].Groups[1].Value

if (-not (Test-Path .venv-build)) { py -3 -m venv .venv-build }
$py = "$repo\.venv-build\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install ".[soundfont]" pyinstaller
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# From outside the checkout, so the spec imports the installed package
Push-Location $env:TEMP
& "$repo\.venv-build\Scripts\pyinstaller.exe" --noconfirm --clean `
    --distpath "$repo\dist" --workpath "$env:TEMP\jdxi-pyi-build" "$repo\building\windows\jdxi_editor.spec"
$code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { exit $code }
Write-Host "Exe: $repo\dist\jdxi_editor\jdxi_editor.exe"

if ($Installer) {
    $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (-not (Test-Path $iscc)) { Write-Error "Inno Setup 6 not found: install it from https://jrsoftware.org/isdl.php"; exit 1 }
    & $iscc /DMyAppVersion=$version jdxi_editor.iss
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Installer: $repo\dist\installer"
}
