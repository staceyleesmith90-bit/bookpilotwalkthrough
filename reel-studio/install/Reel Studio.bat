@echo off
REM Opens Reel Studio in your browser. Keep this window open while you use it.
cd /d "%~dp0.."
set PYTHONUTF8=1
chcp 65001 >nul
.venv\Scripts\python.exe -m engine studio
