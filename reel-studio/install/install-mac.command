#!/bin/bash
# Reel Studio installer for Mac — double-click this file.
cd "$(dirname "$0")/.."
echo "Setting up Reel Studio (by Systems Pilot)…"
if ! command -v brew >/dev/null 2>&1; then
  echo "Installing Homebrew (Apple's popular free package manager)…"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
fi
brew list python@3.12 >/dev/null 2>&1 || brew install python@3.12
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
PY="$(brew --prefix)/bin/python3.12"
"$PY" -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python scripts/fetch_icons.py >/dev/null 2>&1 || true
./.venv/bin/python -m engine setup-check
echo ""
echo "✅ Done. Double-click 'Reel Studio.command' to open the app."
read -n 1 -s -r -p "Press any key to close."
