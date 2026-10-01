# HyperFrames components

The files in this folder come unmodified from HyperFrames by HeyGen
(https://github.com/heygen-com/hyperframes, `registry/components/`), commit in `UPSTREAM_COMMIT`.
Copyright (c) HeyGen and the HyperFrames contributors. Licensed under the Apache License 2.0 (`LICENSE`).
Reel Studio does not modify these files on disk; at render time it swaps in the reel's own words,
timings and length (engine/hyperframes.py).

`gsap.min.js` — GSAP 3.14.2 by GreenSock (https://gsap.com), used under the GreenSock standard
"no charge" licence (https://gsap.com/standard-license); its licence header is kept inside the file.
Bundled so effects render offline (the components normally load it from a CDN).
