@echo off
REM Opens Reel Studio in your browser. Keep this window open while you use it.
cd /d "%~dp0.."
.venv\Scripts\python.exe -m engine studio
