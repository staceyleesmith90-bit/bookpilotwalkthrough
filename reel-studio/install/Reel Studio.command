#!/bin/bash
# Opens Reel Studio in your browser. Keep this window open while you use it.
cd "$(dirname "$0")/.."
./.venv/bin/python -m engine studio
