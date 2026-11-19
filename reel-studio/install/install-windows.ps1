# Reelmate installer for Windows 10/11.
# Easiest: double-click "Install Reelmate.bat" (it runs this file for you).
$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")
Write-Host ""
Write-Host "  Setting up Reelmate - your reel-editing buddy" -ForegroundColor Green
Write-Host "  This takes 10-20 minutes the first time. Go grab a coffee." -ForegroundColor Green
Write-Host ""
$env:PYTHONUTF8 = "1"
[System.Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")   # emoji and accents work everywhere

function Refresh-Path { $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User") }
function Has($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Winget($id, $what) {
  Write-Host "Installing $what..." -ForegroundColor Cyan
  winget install -e --id $id --silent --accept-source-agreements --accept-package-agreements | Out-Host
  Refresh-Path
}
# A real Python 3.12 (Windows' own "python" can be a shortcut that only opens the Microsoft Store)
function Find-Python {
  foreach ($c in @("py -3.12", "py -3.11", "python")) {
    $parts = $c.Split(" ")
    try {
      $v = & $parts[0] $parts[1..9] -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
      if ($LASTEXITCODE -eq 0 -and $v -match '^3\.(1[0-3])$') { return $c }
    } catch {}
  }
  return $null
}
if (-not (Has "winget")) {
  Write-Host "This needs 'App Installer' from the Microsoft Store (it gives Windows the winget tool)." -ForegroundColor Yellow
  Start-Process "ms-windows-store://pdp/?ProductId=9NBLGGH4NNS1"
  Read-Host "Install it, then press Enter to continue"
  Refresh-Path
}
$py = Find-Python
if (-not $py) { Winget "Python.Python.3.12" "Python 3.12"; $py = Find-Python }
if (-not $py) { Write-Host "Python didn't install. Restart the computer and run this again." -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }
if (-not (Has "ffmpeg")) { Winget "Gyan.FFmpeg" "FFmpeg (video tools)" }
if (-not (Has "git"))    { Winget "Git.Git" "Git for Windows (Claude Code needs it)" }

Write-Host "Setting up Reelmate's own Python..." -ForegroundColor Cyan
$parts = $py.Split(" ")
& $parts[0] $parts[1..9] -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
Write-Host "Installing the editing tools (the long part)..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe scripts\fetch_icons.py
.\.venv\Scripts\python.exe -m engine setup-check
Write-Host ""
Write-Host "  All set!" -ForegroundColor Green
Write-Host "  Open the Claude app -> Code -> pick this Reelmate folder -> say 'hi Reelmate'." -ForegroundColor Green
Write-Host "  Or double-click 'Reelmate.bat' to open the Studio." -ForegroundColor Green
Read-Host "Press Enter to close"
