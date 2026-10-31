# Vendored: claude-video-effects

- Upstream: https://github.com/Vibha-Ramprakash/claude-video-effects, commit 99c9a3393ee14d39bea155a05c73dc069f02f16f
- Author: Vibha Ramprakash (@vibha.in.progress) — MIT licence (LICENSE in this folder)
- Changes for Reel Studio: paths (fonts/models next to fx.py, segmenter from library/models),
  the optional private-effects loader removed, headline-wall reads the `handle` option, todo takes `side`, `y` and `front`. Effects run through engine/scenefx.py.
- Fonts: SIL OFL / Apache 2.0, licences in fonts/. YuNet face model: MIT (models/NOTICE.md).

- Updates: `python -m engine effects-update` (engine/vfx45/update.py) fetches the newest version and re-applies the changes above; upstream.json records the commit in use.
