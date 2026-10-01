# Reel Studio installer for Windows 10/11.
# Right-click this file -> "Run with PowerShell".
Set-Location (Join-Path $PSScriptRoot "..")
Write-Host "Setting up Reel Studio (by Systems Pilot)..."
$env:PYTHONUTF8 = "1"
[System.Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")   # emoji and accents work everywhere
function Has($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
if (-not (Has "python")) { winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements }
if (-not (Has "ffmpeg")) { winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements }
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe scripts\fetch_icons.py
.\.venv\Scripts\python.exe -m engine setup-check
Write-Host ""
Write-Host "Done. Double-click 'Reel Studio.bat' to open the app."
Read-Host "Press Enter to close"
