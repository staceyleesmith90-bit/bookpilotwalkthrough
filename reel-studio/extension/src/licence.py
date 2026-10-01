"""Monthly subscription check for Reel Studio (runs on the customer's computer).

The key comes from the extension settings (REEL_LICENSE_KEY). It's checked against the Systems
Pilot licence service at most once a day; an active subscription is remembered for 7 days so a
flaky connection never blocks someone mid-edit. Nothing about their videos is ever sent — only
the key and an anonymous machine id.

Service contract (any backend can implement it, e.g. a small worker fed by PayFast/PayPal):
  POST {REEL_LICENSE_URL}  {"key": "...", "machine": "..."}
  ->   {"valid": true, "plan": "monthly", "renews": "2026-11-01", "message": "optional"}
"""
import hashlib, json, os, platform, time, urllib.request, uuid

LICENSE_URL = os.environ.get("REEL_LICENSE_URL", "https://reelstudio.systemspilot.co.za/api/licence/validate")
CHECK_EVERY = 24 * 3600            # ask the service at most once a day
GRACE = 7 * 24 * 3600              # keep working offline for a week after the last good check


def machine_id():
    raw = f"{platform.node()}|{uuid.getnode()}|{platform.system()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _cache_path(home):
    return os.path.join(home, ".licence.json")


def status(home, key=None, now=None):
    """-> (ok: bool, message: str). Never raises."""
    key = (key if key is not None else os.environ.get("REEL_LICENSE_KEY", "")).strip()
    now = now or time.time()
    if (not key or key.startswith("${")) and not os.environ.get("REEL_TESTER_UNTIL"):
        return False, ("No licence key yet. Open Claude → Settings → Extensions → Reel Studio and paste "
                       "the key from your Reel Studio account.")
    if os.environ.get("REEL_DEV") == "1" and key == "DEV":
        return True, "Developer mode."
    until = os.environ.get("REEL_TESTER_UNTIL", "")         # private tester builds only (never sold)
    if until and not until.startswith("${"):
        try:
            if now < time.mktime(time.strptime(until, "%Y-%m-%d")):
                return True, f"Tester build — works until {until}."
        except ValueError:
            pass
    cache = {}
    try:
        cache = json.load(open(_cache_path(home), encoding="utf-8"))
    except Exception:
        pass
    same_key = cache.get("key_hash") == hashlib.sha256(key.encode()).hexdigest()
    if same_key and cache.get("valid") and now - cache.get("checked", 0) < CHECK_EVERY:
        return True, cache.get("message") or "Subscription active."
    try:
        req = urllib.request.Request(LICENSE_URL, data=json.dumps({"key": key, "machine": machine_id()}).encode(),
                                     headers={"Content-Type": "application/json"})
        res = json.loads(urllib.request.urlopen(req, timeout=8).read().decode())
        valid = bool(res.get("valid"))
        msg = res.get("message") or ("Subscription active." if valid else
                                     "Your Reel Studio subscription isn't active. Renew it in your account to keep editing.")
        try:
            os.makedirs(home, exist_ok=True)
            json.dump({"key_hash": hashlib.sha256(key.encode()).hexdigest(), "valid": valid, "checked": now,
                       "message": msg, "renews": res.get("renews")}, open(_cache_path(home), "w", encoding="utf-8"))
        except Exception:
            pass
        return valid, msg
    except Exception:
        # offline / service hiccup: honour a recent good check
        if same_key and cache.get("valid") and now - cache.get("checked", 0) < GRACE:
            return True, "Subscription active (checked recently; offline right now)."
        return False, "Couldn't check your subscription. Connect to the internet and try again."
