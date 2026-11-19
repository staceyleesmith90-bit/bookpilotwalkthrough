"""Reelmate has no licence keys: people pay once on the website and download it. Nothing to check, ever.

Kept as a tiny module so older code that asks "is Reelmate allowed to run?" always gets yes.
"""
import hashlib, platform, uuid


def machine_id():
    raw = f"{platform.node()}|{uuid.getnode()}|{platform.system()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def status(home=None, key=None, now=None):
    """-> (ok, message). Always ok: Reelmate is theirs forever, no key, works offline."""
    return True, "Reelmate is yours forever — no key, no subscription, updates included."
