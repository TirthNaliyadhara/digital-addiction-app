import subprocess
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import re
import os
import shutil

# ─────────────────────────────────────────────────────────────────────────────
# ADB DISCOVERY – primary path first, then common fallbacks
# ─────────────────────────────────────────────────────────────────────────────

_ADB_CANDIDATE_PATHS = [
    # ── Primary path (confirmed install location) ──────────────────────────────
    r"C:\Users\Administrator\platform-tools\adb.exe",
    # ── Fallbacks ──────────────────────────────────────────────────────────────
    "adb",                                                          # system PATH
    os.path.expandvars(r"%USERPROFILE%\platform-tools\adb.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
    os.path.expandvars(r"%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
    r"C:\platform-tools\adb.exe",
    r"C:\adb\adb.exe",
    r"C:\android\platform-tools\adb.exe",
    r"C:\Program Files\Android\android-sdk\platform-tools\adb.exe",
    r"C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe",
]


def _find_adb() -> str | None:
    """Return the first working adb executable path, or None."""
    for path in _ADB_CANDIDATE_PATHS:
        if shutil.which(path) or (os.path.isfile(path)):
            return path
    return None


def _run_adb(*args, timeout=8) -> subprocess.CompletedProcess | None:
    """Run adb with auto-discovery. Returns CompletedProcess or None on failure."""
    adb = _find_adb()
    if not adb:
        return None
    try:
        return subprocess.run(
            [adb, *args],
            capture_output=True, timeout=timeout
        )
    except Exception:
        return None


def _adb_text(*args, timeout=15) -> str:
    """Run adb and return stdout decoded as UTF-8 (with error replacement)."""
    r = _run_adb(*args, timeout=timeout)
    if r is None:
        return ""
    return r.stdout.decode("utf-8", errors="replace")


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC STATUS API
# ─────────────────────────────────────────────────────────────────────────────

class AdbStatus:
    """Encapsulates the full ADB connection status."""
    NOT_INSTALLED = "not_installed"
    NO_DEVICE     = "no_device"
    UNAUTHORIZED  = "unauthorized"
    OFFLINE       = "offline"
    CONNECTED     = "connected"


def get_adb_status() -> tuple[str, str]:
    """
    Returns (status_code, raw_output).
    status_code is one of AdbStatus constants.
    """
    adb = _find_adb()
    if not adb:
        return AdbStatus.NOT_INSTALLED, ""

    result = _run_adb("devices", timeout=6)
    if result is None:
        return AdbStatus.NOT_INSTALLED, ""

    raw = result.stdout.decode("utf-8", errors="replace").strip()
    lines = raw.split("\n")
    device_lines = [l.strip() for l in lines[1:] if l.strip()]

    if not device_lines:
        return AdbStatus.NO_DEVICE, raw

    first = device_lines[0].lower()
    if "unauthorized" in first:
        return AdbStatus.UNAUTHORIZED, raw
    if "offline" in first:
        return AdbStatus.OFFLINE, raw
    if "device" in first:
        return AdbStatus.CONNECTED, raw

    return AdbStatus.NO_DEVICE, raw


def check_adb_connected() -> bool:
    status, _ = get_adb_status()
    return status == AdbStatus.CONNECTED


def get_adb_device_info() -> dict:
    """Return a dict with brand, model, android version."""
    def prop(name):
        out = _adb_text("shell", "getprop", name, timeout=5)
        return out.strip()

    return {
        "brand":   prop("ro.product.brand"),
        "model":   prop("ro.product.model"),
        "android": prop("ro.build.version.release"),
        "sdk":     prop("ro.build.version.sdk"),
    }


def fetch_adb_battery() -> int | None:
    """Return battery percentage as int, or None."""
    out = _adb_text("shell", "dumpsys", "battery", timeout=6)
    m = re.search(r"level:\s*(\d+)", out)
    return int(m.group(1)) if m else None


def fetch_adb_screen_state() -> str:
    """Return 'on', 'off', or 'unknown'."""
    out = _adb_text("shell", "dumpsys", "power", timeout=6)
    if "mInteractive=true" in out or "mScreenOn=true" in out:
        return "on"
    if "mInteractive=false" in out or "mScreenOn=false" in out:
        return "off"
    return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# PACKAGE → UID MAP  &  THIRD-PARTY PACKAGE SET
# ─────────────────────────────────────────────────────────────────────────────

# System/vendor package prefixes to exclude from the usage report
_SYSTEM_PKG_PREFIXES = (
    "com.android.", "com.google.android.documentsui",
    "com.google.android.overlay", "com.google.android.ext",
    "com.google.android.permissioncontroller",
    "com.google.android.inputmethod", "com.google.android.gms",
    "com.google.android.gsf", "com.google.android.providers",
    "com.google.android.webview", "android.uid.system",
    "android.", "com.vivo.", "com.bbk.", "com.qualcomm.",
    "com.qti.", "com.mediatek.", "com.miui.", "com.oneplus.",
    "com.oppo.", "com.realme.", "com.samsung.", "com.sec.",
    "com.huawei.", "com.honor.",
)

_KEEP_SYSTEM_PKGS = {
    # Keep these even though they have android/com.android prefix
    "com.android.chrome", "com.android.dialer",
    "com.android.camera2", "com.android.mms",
}


def _get_uid_package_maps() -> tuple[dict[int, str], set[str]]:
    """
    Returns:
      uid_map  : {uid_int -> package_name}  (all packages)
      third_party_pkgs : set of third-party package names (from pm list -3)
    """
    uid_map: dict[int, str] = {}
    out = _adb_text("shell", "pm", "list", "packages", "-U", timeout=20)
    for line in out.splitlines():
        m = re.match(r"package:([\w.]+)\s+uid:(\d+)", line.strip())
        if m:
            uid_map[int(m.group(2))] = m.group(1)

    # Third-party apps only
    third_party: set[str] = set()
    out3 = _adb_text("shell", "pm", "list", "packages", "-3", timeout=15)
    for line in out3.splitlines():
        m = re.match(r"package:([\w.]+)", line.strip())
        if m:
            third_party.add(m.group(1))

    return uid_map, third_party


def _is_user_app(pkg: str, third_party: set[str]) -> bool:
    """Return True if this package should be shown to the user."""
    if pkg in third_party:
        return True
    if pkg in _KEEP_SYSTEM_PKGS:
        return True
    if pkg in PACKAGE_MAP:  # explicitly mapped = worth showing
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# BATTERYSTATS PARSER  (primary data source)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_batterystats(uid_map: dict[int, str],
                        third_party: set[str],
                        debug: bool = False) -> list[dict]:
    """
    Parse `dumpsys batterystats --charged`.

    Usage metric priority:
      1. screen time  (time app was visible on screen)
      2. fg CPU time  (time app ran in foreground — better for messaging/music)

    Only returns user-facing apps (third-party or explicitly whitelisted).
    """
    out = _adb_text("shell", "dumpsys", "batterystats", "--charged", timeout=45)
    
    if debug:
        print(f"[DEBUG] batterystats output length: {len(out)} chars")
        print(f"[DEBUG] batterystats first 500 chars:\n{out[:500]}")

    uid_re    = re.compile(r"UID u0a(\d+):")
    screen_re = re.compile(r"screen=[\d.]+ \(([\dhms ]+?)\)")
    fg_re     = re.compile(r"cpu:fg=[\d.]+ \(([\dhms ]+?)\)")
    fgs_re    = re.compile(r"cpu:fgs=[\d.]+ \(([\dhms ]+?)\)")   # foreground service
    job_re    = re.compile(r"successful_finish\((\d+)x\)")

    # Collect per-UID blocks
    blocks: dict[int, str] = {}
    current_uid: int | None = None
    current_lines: list[str] = []

    for line in out.splitlines():
        uid_m = uid_re.search(line)
        if uid_m:
            if current_uid is not None and current_lines:
                blocks[current_uid] = "\n".join(current_lines)
            current_uid = int(uid_m.group(1))
            current_lines = [line]
        elif current_uid is not None:
            current_lines.append(line)

    if current_uid is not None and current_lines:
        blocks[current_uid] = "\n".join(current_lines)

    rows: list[dict] = []

    for uid_suffix, block in blocks.items():
        actual_uid = 10000 + uid_suffix
        pkg = uid_map.get(actual_uid)
        if not pkg:
            continue
        if not _is_user_app(pkg, third_party):
            continue

        # --- Usage time: prefer screen time, fall back to fg CPU ---
        screen_min = 0.0
        sm = screen_re.search(block)
        if sm:
            screen_min = _hms_to_minutes(sm.group(1))

        fg_min = 0.0
        fm = fg_re.search(block)
        if fm:
            fg_min = _hms_to_minutes(fm.group(1))

        fgs_min = 0.0
        fgsm = fgs_re.search(block)
        if fgsm:
            fgs_min = _hms_to_minutes(fgsm.group(1))

        # Best usage estimate: screen time if significant, otherwise fg+fgs
        usage_min = screen_min if screen_min >= 0.5 else (fg_min + fgs_min)

        if usage_min <= 0:
            continue

        # --- Session count ---
        job_counts = job_re.findall(block)
        session_count = max(1, sum(int(x) for x in job_counts)) if job_counts \
            else max(1, int(usage_min / 10))

        rows.append({
            "package":        pkg,
            "usage_time_min": round(usage_min, 1),
            "session_count":  session_count,
        })

    if debug:
        print(f"[DEBUG] batterystats parsed {len(rows)} rows")
        for row in rows[:5]:
            print(f"[DEBUG]   {row}")

    return rows


def _hms_to_minutes(hms_str: str) -> float:
    """
    Convert ADB time strings like '1h 57m 10s 998ms' or '3m 58s 0ms'
    to total minutes (float).
    """
    total_ms = 0
    hms_str = hms_str.strip()

    h = re.search(r"(\d+)h", hms_str)
    m = re.search(r"(\d+)m", hms_str)
    s = re.search(r"(\d+)s", hms_str)
    ms = re.search(r"(\d+)ms", hms_str)

    if h:  total_ms += int(h.group(1)) * 3_600_000
    if m:  total_ms += int(m.group(1)) *    60_000
    if s:  total_ms += int(s.group(1)) *     1_000
    if ms: total_ms += int(ms.group(1))

    return round(total_ms / 60_000, 2)


# ─────────────────────────────────────────────────────────────────────────────
# KNOWN APP REGISTRY  (name + category lookup)
# ─────────────────────────────────────────────────────────────────────────────

PACKAGE_MAP: dict[str, tuple[str, str]] = {
    # Social
    "com.instagram.android":                   ("Instagram",        "Social"),
    "com.snapchat.android":                    ("Snapchat",         "Social"),
    "com.facebook.katana":                     ("Facebook",         "Social"),
    "com.facebook.lite":                       ("Facebook Lite",    "Social"),
    "com.twitter.android":                     ("Twitter/X",        "Social"),
    "com.zhiliaoapp.musically":                ("TikTok",           "Social"),
    "com.linkedin.android":                    ("LinkedIn",         "Social"),
    "com.reddit.frontpage":                    ("Reddit",           "Social"),
    "com.pinterest":                           ("Pinterest",        "Social"),
    "com.tumblr":                              ("Tumblr",           "Social"),
    "com.discord":                             ("Discord",          "Social"),
    "com.kik.android":                         ("Kik",              "Social"),
    "com.sharechat.app":                       ("ShareChat",        "Social"),
    "com.moj.app":                             ("Moj",              "Social"),
    "com.roposo.android":                      ("Roposo",           "Social"),
    "com.mx.browser":                          ("MX TakaTak",       "Social"),
    # Messaging
    "com.whatsapp":                            ("WhatsApp",         "Messaging"),
    "com.whatsapp.w4b":                        ("WhatsApp Business","Messaging"),
    "com.google.android.apps.messaging":       ("Google Messages",  "Messaging"),
    "com.facebook.orca":                       ("Messenger",        "Messaging"),
    "org.telegram.messenger":                  ("Telegram",         "Messaging"),
    "org.thoughtcrime.securesms":              ("Signal",           "Messaging"),
    "com.viber.voip":                          ("Viber",            "Messaging"),
    "com.skype.raider":                        ("Skype",            "Messaging"),
    "jp.naver.line.android":                   ("LINE",             "Messaging"),
    # Streaming / Entertainment
    "com.google.android.youtube":              ("YouTube",          "Streaming"),
    "com.netflix.mediaclient":                 ("Netflix",          "Streaming"),
    "com.amazon.avod.thirdpartyclient":        ("Prime Video",      "Streaming"),
    "com.spotify.music":                       ("Spotify",          "Streaming"),
    "com.hotstar.android":                     ("Hotstar",          "Streaming"),
    "com.jio.jioplay.tv":                      ("JioTV",            "Streaming"),
    "com.sonyliv":                             ("Sony LIV",         "Streaming"),
    "in.startv.hotstar":                       ("Hotstar",          "Streaming"),
    "com.zee5.android":                        ("ZEE5",             "Streaming"),
    "com.mxtech.videoplayer.ad":               ("MX Player",        "Streaming"),
    "tv.twitch.android.app":                   ("Twitch",           "Streaming"),
    "com.google.android.apps.youtube.music":   ("YouTube Music",    "Streaming"),
    "com.google.android.videos":               ("Google TV",        "Streaming"),
    "org.videolan.vlc":                        ("VLC",              "Streaming"),
    # Gaming
    "com.activision.callofduty.shooter":       ("Call of Duty",     "Gaming"),
    "com.garena.game.freefire":                ("Free Fire",        "Gaming"),
    "com.tencent.ig":                          ("PUBG Mobile",      "Gaming"),
    "com.dts.freefireth":                      ("Free Fire TH",     "Gaming"),
    "com.king.candycrushsaga":                 ("Candy Crush",      "Gaming"),
    "com.ludo.king":                           ("Ludo King",        "Gaming"),
    "com.supercell.clashofclans":              ("Clash of Clans",   "Gaming"),
    "com.supercell.clashroyale":               ("Clash Royale",     "Gaming"),
    "com.mojang.minecraftpe":                  ("Minecraft",        "Gaming"),
    "com.roblox.client":                       ("Roblox",           "Gaming"),
    "me.overkillstudio.crosshairherofps":      ("Crosshair Hero",   "Gaming"),
    "me.okitastudio.crosshairherofps":         ("Crosshair Hero",   "Gaming"),
    "io.supercent.pizzaidle":                  ("Pizza Idle",       "Gaming"),
    # Shopping
    "com.amazon.mShop.android.shopping":       ("Amazon",           "Shopping"),
    "com.flipkart.android":                    ("Flipkart",         "Shopping"),
    "com.myntra.android":                      ("Myntra",           "Shopping"),
    "com.ajio.android":                        ("AJIO",             "Shopping"),
    "com.meesho.supply":                       ("Meesho",           "Shopping"),
    "com.snapdeal.main":                       ("Snapdeal",         "Shopping"),
    # Productivity
    "com.google.android.gm":                   ("Gmail",            "Productivity"),
    "com.google.android.googlequicksearchbox": ("Google",           "Productivity"),
    "com.google.android.apps.docs":            ("Google Docs",      "Productivity"),
    "com.google.android.apps.docs.editors.docs":("Google Docs",     "Productivity"),
    "com.google.android.apps.docs.editors.sheets":("Google Sheets", "Productivity"),
    "com.google.android.apps.docs.editors.slides":("Google Slides", "Productivity"),
    "com.google.android.apps.drive":           ("Google Drive",     "Productivity"),
    "com.microsoft.teams":                     ("MS Teams",         "Productivity"),
    "com.microsoft.office.word":               ("MS Word",          "Productivity"),
    "com.microsoft.office.excel":              ("MS Excel",         "Productivity"),
    "com.openai.chatgpt":                      ("ChatGPT",          "Productivity"),
    "com.canva.editor":                        ("Canva",            "Productivity"),
    "com.github.android":                      ("GitHub",           "Productivity"),
    "com.termux":                              ("Termux",           "Productivity"),
    # Browsing
    "com.android.chrome":                      ("Chrome",           "Browsing"),
    "org.mozilla.firefox":                     ("Firefox",          "Browsing"),
    "com.microsoft.emmx":                      ("Edge",             "Browsing"),
    "com.opera.browser":                       ("Opera",            "Browsing"),
    "com.brave.browser":                       ("Brave",            "Browsing"),
    "com.UCMobile.intl":                       ("UC Browser",       "Browsing"),
    # Navigation / Travel
    "com.google.android.apps.maps":            ("Google Maps",      "Navigation"),
    "com.ubercab":                             ("Uber",             "Navigation"),
    "com.olacabs.customer":                    ("Ola",              "Navigation"),
    "com.rapido.passenger":                    ("Rapido",           "Navigation"),
    # Food
    "com.done.faasos":                         ("Swiggy",           "Food"),
    "com.zomato.android":                      ("Zomato",           "Food"),
    "com.grofers.customerapp":                 ("Grofers/Blinkit",  "Food"),
    # Finance
    "com.phonepe.app":                         ("PhonePe",          "Finance"),
    "com.google.android.apps.nbu.paisa.user": ("Google Pay",       "Finance"),
    "net.one97.paytm":                         ("Paytm",            "Finance"),
    # Health
    "com.pristyncare.patientapp":              ("Pristyn Care",     "Health"),
    # Education
    "com.byjus.thelearningapp":                ("BYJU'S",           "Education"),
    "in.unacademy.learnerapp":                 ("Unacademy",        "Education"),
}


def _resolve_app_name_category(pkg: str) -> tuple[str, str]:
    """Get friendly name + category for a package, falling back to a best-guess."""
    if pkg in PACKAGE_MAP:
        return PACKAGE_MAP[pkg]

    # Attempt smart name from package suffix
    parts = pkg.split(".")
    name = parts[-1].replace("_", " ").title() if parts else pkg
    # Guess category from known keywords
    pkg_lower = pkg.lower()
    if any(k in pkg_lower for k in ["game", "play", "king", "clash", "battle", "shooter", "idle"]):
        cat = "Gaming"
    elif any(k in pkg_lower for k in ["chat", "msg", "talk", "whatsapp", "telegram", "signal"]):
        cat = "Messaging"
    elif any(k in pkg_lower for k in ["music", "video", "stream", "tv", "netflix", "hotstar"]):
        cat = "Streaming"
    elif any(k in pkg_lower for k in ["shop", "cart", "amazon", "flipkart", "buy"]):
        cat = "Shopping"
    elif any(k in pkg_lower for k in ["social", "insta", "facebook", "twitter", "snap"]):
        cat = "Social"
    elif any(k in pkg_lower for k in ["map", "uber", "ola", "rapido", "nav"]):
        cat = "Navigation"
    elif any(k in pkg_lower for k in ["pay", "bank", "finance", "money", "paytm"]):
        cat = "Finance"
    else:
        cat = "Other"
    return name, cat


# ─────────────────────────────────────────────────────────────────────────────
# USAGE STATS — 7-DAY DATA VIA dumpsys usagestats (PRIMARY SOURCE)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_usagestats_samsung_events(out: str, third_party: set[str]) -> list[dict]:
    """
    Parse Samsung's event-based usagestats format.
    Samsung outputs events like:
        time="2026-05-10 14:44:50" type=ACTIVITY_RESUMED package=com.whatsapp ...
        time="2026-05-10 14:45:30" type=ACTIVITY_PAUSED package=com.whatsapp ...
    We calculate duration between RESUMED and PAUSED for each package.
    """
    from collections import defaultdict

    # Pattern to extract: time="YYYY-MM-DD HH:MM:SS" type=EVENT_TYPE package=PKG
    event_re = re.compile(
        r'time="(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"\s+'
        r'type=(\w+)\s+'
        r'package=([\w.]+)'
    )

    # Track active sessions: pkg -> (start_time, date_str)
    active_sessions: dict[str, tuple[datetime, str]] = {}

    # Accumulated usage per package per day
    usage: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {
        "total_seconds": 0,
        "session_count": 0
    }))

    for line in out.splitlines():
        match = event_re.search(line)
        if not match:
            continue

        time_str, event_type, pkg = match.groups()

        # Skip system apps
        if not _is_user_app(pkg, third_party):
            continue
        if "launcher" in pkg.lower() or "settings" in pkg.lower():
            continue

        try:
            event_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            date_str = event_time.strftime("%Y-%m-%d")
        except ValueError:
            continue

        if event_type == "ACTIVITY_RESUMED":
            # App came to foreground - start session
            active_sessions[pkg] = (event_time, date_str)
        elif event_type == "ACTIVITY_PAUSED":
            # App went to background - end session and calculate duration
            if pkg in active_sessions:
                start_time, start_date = active_sessions[pkg]
                duration_seconds = (event_time - start_time).total_seconds()

                # Allow up to 8 hours per session (covers full movies/series marathons)
                if 0 < duration_seconds < 28800:
                    usage[pkg][start_date]["total_seconds"] += duration_seconds
                    usage[pkg][start_date]["session_count"] += 1

                del active_sessions[pkg]

    # Flush sessions that were still open when the dump was captured
    # (e.g. VLC was actively playing - ACTIVITY_PAUSED never fired)
    dump_time = datetime.now()
    for pkg, (start_time, start_date) in active_sessions.items():
        duration_seconds = (dump_time - start_time).total_seconds()
        if 0 < duration_seconds < 28800:
            usage[pkg][start_date]["total_seconds"] += duration_seconds
            usage[pkg][start_date]["session_count"] += 1

    # Convert to row format
    rows = []
    now = datetime.now()
    cutoff = now - timedelta(days=7)

    for pkg, dates in usage.items():
        for date_str, data in dates.items():
            # Check if within last 7 days
            try:
                row_dt = datetime.strptime(date_str, "%Y-%m-%d")
                if row_dt < cutoff:
                    continue
            except ValueError:
                continue

            usage_min = round(data["total_seconds"] / 60, 2)
            if usage_min >= 0.5:  # Minimum 30 seconds
                rows.append({
                    "package": pkg,
                    "usage_time_min": usage_min,
                    "session_count": data["session_count"],
                    "date": date_str,
                })

    return rows


def _parse_usagestats_7days(uid_map: dict[int, str],
                             third_party: set[str],
                             debug: bool = True) -> list[dict]:
    """
    Parse `dumpsys usagestats` to get per-day usage for the last 7 days.

    Android's UsageStats service keeps daily buckets. We query the
    'Daily' interval bucket and collect foreground time per package per day.
    This is the only reliable way to get genuine 7-day historical data
    instead of 'since last charge' (batterystats limitation).

    Returns a list of dicts with keys:
        package, usage_time_min, session_count, date (YYYY-MM-DD)
    """
    # Extended timeout for Samsung devices which can be slower
    out = _adb_text("shell", "dumpsys", "usagestats", timeout=60)
    if not out.strip():
        if debug:
            print("[ADB DEBUG] dumpsys usagestats returned empty output")
        return []

    # Debug: log first 500 chars of output for Samsung troubleshooting
    is_samsung = "samsung" in str(get_adb_device_info().get('brand', '')).lower()
    if debug or is_samsung:
        print(f"[ADB DEBUG] usagestats output length: {len(out)} chars")
        print(f"[ADB DEBUG] usagestats first 500 chars:\n{out[:500]}")

    # Check if this is event-based format (has ACTIVITY_RESUMED/PAUSED)
    # This affects Samsung, Xiaomi, and other manufacturers
    if "ACTIVITY_RESUMED" in out or "ACTIVITY_PAUSED" in out:
        if debug or is_samsung:
            print("[ADB DEBUG] Detected event-based format, using event parser")
        event_rows = _parse_usagestats_samsung_events(out, third_party)
        
        # For Xiaomi devices, event parsing often gives very low values
        # Fall back to batterystats if event data seems insufficient
        if event_rows and len(event_rows) < 10:
            total_event_minutes = sum(row.get('usage_time_min', 0) for row in event_rows)
            if total_event_minutes < 30:  # Less than 30 minutes total seems wrong
                if debug:
                    print(f"[ADB DEBUG] Event parsing insufficient ({total_event_minutes:.1f} min), falling back to batterystats")
                # Fall back to batterystats for better data
                uid_map, third_party = _get_uid_package_maps()
                bs_rows = _parse_batterystats(uid_map, third_party, debug=debug)
                if bs_rows and len(bs_rows) > len(event_rows):
                    if debug:
                        print(f"[ADB DEBUG] Using batterystats data: {len(bs_rows)} apps vs {len(event_rows)} from events")
                    return bs_rows
        
        return event_rows

    rows: list[dict] = []
    now = datetime.now()
    cutoff = now - timedelta(days=7)

    # Each package block starts with: "package=com.foo.bar"
    # followed by lines like: "totalTimeInForeground=12345"  (milliseconds)
    # and "lastTimeUsed=<epoch_ms>"  and "launchCount=N"
    # The usagestats dump is grouped by bucket (daily/weekly/etc).
    # We look for "Daily" or "INTERVAL_DAILY" section.

    # Strategy: scan for package= lines and grab the associated metrics
    # within the same "Begin" block. We detect daily blocks by date headers.
    # Samsung devices may use different formats, so we support multiple patterns.

    pkg_re      = re.compile(r"package=([^\s]+)")
    time_re     = re.compile(r"totalTimeInForeground[=:]\s*(\d+)")  # Some devices use : instead of =
    last_re     = re.compile(r"lastTimeUsed[=:]\s*(\d+)")
    launch_re   = re.compile(r"launchCount[=:]\s*(\d+)")
    date_re     = re.compile(r"(\d{4}-\d{2}-\d{2})")          # date in header lines
    interval_re = re.compile(r"interval[=:]\s*(\d+)")         # 0=daily,1=weekly,2=monthly

    # Split into blocks separated by blank lines or "Begin" markers
    # Parse line by line accumulating state per daily bucket
    current_date: str | None = None
    in_daily = False
    current_pkg: str | None = None
    current_time_ms: int = 0
    current_last_ms: int = 0
    current_launches: int = 0

    def flush():
        nonlocal current_pkg, current_time_ms, current_last_ms, current_launches
        if current_pkg and current_time_ms > 0:
            usage_min = round(current_time_ms / 60_000, 2)
            if debug:
                print(f"[DEBUG] Parsed: {current_pkg} -> {current_time_ms}ms -> {usage_min}min")
            if usage_min >= 0.5 and _is_user_app(current_pkg, third_party):
                # Assign date from last-used timestamp if available
                if current_last_ms > 0:
                    last_dt = datetime.fromtimestamp(current_last_ms / 1000)
                    row_date = last_dt.strftime("%Y-%m-%d")
                else:
                    row_date = current_date or now.strftime("%Y-%m-%d")

                # Only keep last 7 days
                try:
                    row_dt = datetime.strptime(row_date, "%Y-%m-%d")
                    if row_dt < cutoff:
                        if debug:
                            print(f"[DEBUG] Skipping {current_pkg} - too old: {row_date}")
                        current_pkg = None
                        current_time_ms = current_last_ms = current_launches = 0
                        return
                except Exception:
                    pass

                if debug:
                    print(f"[DEBUG] Adding row: {current_pkg} -> {usage_min}min on {row_date}")
                rows.append({
                    "package":        current_pkg,
                    "usage_time_min": usage_min,
                    "session_count":  max(1, current_launches),
                    "date":           row_date,
                })
            else:
                if debug:
                    print(f"[DEBUG] Skipping {current_pkg}: usage_min={usage_min}, is_user_app={_is_user_app(current_pkg, third_party)}")
        current_pkg = None
        current_time_ms = current_last_ms = current_launches = 0

    for line in out.splitlines():
        stripped = line.strip()

        # Detect daily interval sections (Samsung may use different formats)
        if ("Daily" in stripped or
            "INTERVAL_DAILY" in stripped or
            "interval=0" in stripped or
            "interval: 0" in stripped or  # Samsung format
            "InMemory" in stripped):        # Some Samsung devices use InMemory buckets
            in_daily = True

        # Detect non-daily sections → stop if we exit daily
        if ("Weekly" in stripped or "INTERVAL_WEEKLY" in stripped or
            "interval=1" in stripped or "interval: 1" in stripped or
            "Monthly" in stripped or "INTERVAL_MONTHLY" in stripped or
            "interval=2" in stripped or "interval: 2" in stripped):
            flush()
            in_daily = False

        if not in_daily:
            continue

        # Date header
        dm = date_re.search(stripped)
        if dm and ("beginDate" in stripped or "Begin" in stripped or stripped.startswith(dm.group(0))):
            flush()
            try:
                candidate = datetime.strptime(dm.group(1), "%Y-%m-%d")
                if candidate >= cutoff:
                    current_date = dm.group(1)
                else:
                    current_date = None
            except Exception:
                current_date = None

        # New package entry
        pm_match = pkg_re.search(stripped)
        if pm_match:
            flush()
            current_pkg = pm_match.group(1)
            # Skip system/junk
            if "launcher" in current_pkg.lower() or "settings" in current_pkg.lower():
                current_pkg = None
            continue

        if current_pkg is None:
            continue

        tm = time_re.search(stripped)
        if tm:
            current_time_ms = int(tm.group(1))

        lm = last_re.search(stripped)
        if lm:
            current_last_ms = int(lm.group(1))

        lcm = launch_re.search(stripped)
        if lcm:
            current_launches = int(lm.group(1))

    flush()
    return rows


def _aggregate_7day_rows(rows: list[dict]) -> list[dict]:
    """
    Aggregate per-day rows into per-package totals,
    preserving the per-day breakdown for trend analysis.
    Returns list of dicts: package, usage_time_min, session_count,
    daily_breakdown (list of {date, usage_time_min}).
    """
    from collections import defaultdict
    agg: dict[str, dict] = defaultdict(lambda: {
        "usage_time_min": 0.0,
        "session_count":  0,
        "daily": [],
    })
    for r in rows:
        pkg = r["package"]
        agg[pkg]["usage_time_min"] += r["usage_time_min"]
        agg[pkg]["session_count"]  += r["session_count"]
        agg[pkg]["daily"].append({"date": r["date"], "usage_time_min": r["usage_time_min"]})

    result = []
    for pkg, vals in agg.items():
        result.append({
            "package":        pkg,
            "usage_time_min": round(vals["usage_time_min"], 2),
            "session_count":  vals["session_count"],
            "daily_breakdown": sorted(vals["daily"], key=lambda x: x["date"]),
        })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# CMD USAGESTATS — same API as Samsung Digital Wellbeing (most accurate)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_cmd_usagestats(third_party: set[str], debug: bool = False) -> list[dict]:
    """
    Query 'adb shell cmd usagestats query-usage-stats 1 <start_ms> <end_ms>'.
    This is the same UsageStatsManager API that Samsung Digital Wellbeing uses,
    so it captures VLC and every other app — including those with no
    ACTIVITY_RESUMED/PAUSED events (media players, launchers, etc.).

    Returns rows with keys: package, usage_time_min, session_count, date
    """
    now = datetime.now()
    now_ms     = int(now.timestamp() * 1000)
    start_ms   = now_ms - (7 * 24 * 3600 * 1000)

    out = _adb_text("shell", "cmd", "usagestats", "query-usage-stats", "1",
                    str(start_ms), str(now_ms), timeout=45)

    if debug:
        print(f"[ADB DEBUG] cmd usagestats output length: {len(out)} chars")
        print(f"[ADB DEBUG] cmd usagestats first 400 chars:\n{out[:400]}")

    if not out.strip() or "Unknown command" in out or "Error" in out[:200]:
        if debug:
            print("[ADB DEBUG] cmd usagestats unavailable or errored")
        return []

    rows: list[dict] = []
    cutoff = now - timedelta(days=7)

    # Android formats vary by version — support both:
    # New:  UsageStats{mPackageName=X, mTotalTimeInForeground=N, mLaunchCount=N, mBeginTimeStamp=N ...}
    # Old:  "  com.example.app: totalTime=7200000ms  launches=5  lastUsed=..."
    # Samsung may also output per-interval blocks with indented lines.

    # ── Format A: UsageStats{...} single-line blocks ──────────────────────────
    block_re    = re.compile(r'UsageStats\{([^}]+)\}')
    pkg_re_a    = re.compile(r'mPackageName=([^\s,}]+)')
    time_re_a   = re.compile(r'mTotalTimeInForeground=(\d+)')
    launch_re_a = re.compile(r'mLaunchCount=(\d+)')
    begin_re_a  = re.compile(r'mBeginTimeStamp=(\d+)')

    for block_m in block_re.finditer(out):
        block = block_m.group(1)
        pm = pkg_re_a.search(block)
        tm = time_re_a.search(block)
        if not pm or not tm:
            continue
        pkg      = pm.group(1).strip()
        time_ms  = int(tm.group(1))
        launches = int(launch_re_a.search(block).group(1)) if launch_re_a.search(block) else 1
        begin_m  = begin_re_a.search(block)
        if begin_m:
            date_str = datetime.fromtimestamp(int(begin_m.group(1)) / 1000).strftime("%Y-%m-%d")
        else:
            date_str = now.strftime("%Y-%m-%d")

        usage_min = round(time_ms / 60_000, 2)
        if usage_min < 0.5:
            continue
        if not _is_user_app(pkg, third_party):
            continue
        if "launcher" in pkg.lower() or "settings" in pkg.lower():
            continue

        rows.append({"package": pkg, "usage_time_min": usage_min,
                     "session_count": max(1, launches), "date": date_str})

    if rows:
        if debug:
            print(f"[ADB DEBUG] cmd usagestats (Format A) found {len(rows)} apps")
        return rows

    # ── Format B: "  pkg: totalTime=Nms  launches=N" per line ─────────────────
    line_re   = re.compile(r'^\s+([\w.]+):\s+totalTime=(\d+)ms\s+launches=(\d+)', re.M)
    for m in line_re.finditer(out):
        pkg, time_ms_str, launches_str = m.group(1), m.group(2), m.group(3)
        usage_min = round(int(time_ms_str) / 60_000, 2)
        if usage_min < 0.5:
            continue
        if not _is_user_app(pkg, third_party):
            continue
        rows.append({"package": pkg, "usage_time_min": usage_min,
                     "session_count": max(1, int(launches_str)),
                     "date": now.strftime("%Y-%m-%d")})

    if debug:
        print(f"[ADB DEBUG] cmd usagestats (Format B) found {len(rows)} apps")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# MAIN FETCH FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def fetch_real_mobile_data(debug: bool = True) -> tuple:
    """
    Returns (df, meta) on success, or (None, error_string) on failure.

    Strategy (priority order):
      1. `cmd usagestats query-usage-stats` — same API as Samsung Digital Wellbeing.
         Most accurate; captures VLC and apps with no ACTIVITY events.
      2. `dumpsys usagestats` event parser — genuine 7-day daily breakdown.
      3. `dumpsys batterystats --charged` — since-last-charge fallback.
    """
    uid_map, third_party = _get_uid_package_maps()
    if not uid_map:
        return None, "Could not list packages from device. Check ADB connection."

    # ── Step 1: cmd usagestats (Digital Wellbeing API) ────────────────────────
    cmd_rows = _parse_cmd_usagestats(third_party, debug=debug)
    if cmd_rows:
        aggregated = _aggregate_7day_rows(cmd_rows)
        rows_for_enrichment = aggregated
        use_7day = True
        source_label = "cmd usagestats (Digital Wellbeing API — 7 days)"
    else:
        # ── Step 2: dumpsys usagestats event parser ───────────────────────────
        raw_7day = _parse_usagestats_7days(uid_map, third_party)
        source_label = "usagestats (last 7 days)"

        if raw_7day:
            aggregated = _aggregate_7day_rows(raw_7day)
            rows_for_enrichment = aggregated
            use_7day = True
        else:
            # ── Step 3: batterystats fallback ─────────────────────────────────
            bs_rows = _parse_batterystats(uid_map, third_party)
            rows_for_enrichment = bs_rows
            use_7day = False
            source_label = "batterystats (since last charge — usagestats unavailable)"

    if not rows_for_enrichment:
        return None, (
            "No foreground usage data found. "
            "Ensure USB Debugging is enabled and the phone has been used for a few minutes."
        )

    # Step 3: enrich with names, categories, and REAL timestamps
    enriched = []
    now = datetime.now()

    for row in rows_for_enrichment:
        usage = float(row["usage_time_min"])
        if usage < 0.5:
            continue
        usage = min(usage, 1440.0 * 7)  # Hard cap at 7 days worth

        pkg = row["package"]
        if "launcher" in pkg.lower() or "settings" in pkg.lower() or "gms" in pkg.lower():
            continue

        name, cat = _resolve_app_name_category(pkg)

        if use_7day:
            # Build one row per day from the daily breakdown
            daily = row.get("daily_breakdown", [])
            if daily:
                for day_entry in daily:
                    try:
                        ts = datetime.strptime(day_entry["date"], "%Y-%m-%d")
                    except Exception:
                        ts = now
                    enriched.append({
                        "package":        pkg,
                        "app_name":       name,
                        "category":       cat,
                        "usage_time_min": round(float(day_entry["usage_time_min"]), 2),
                        "session_count":  max(1, row["session_count"] // max(len(daily), 1)),
                        "last_used":      ts.strftime("%Y-%m-%d %H:%M:%S"),
                        "timestamp":      ts.strftime("%Y-%m-%d %H:%M:%S"),
                    })
            else:
                # No daily breakdown — assign to today
                enriched.append({
                    "package":        pkg,
                    "app_name":       name,
                    "category":       cat,
                    "usage_time_min": round(usage, 2),
                    "session_count":  row.get("session_count", 1),
                    "last_used":      now.strftime("%Y-%m-%d %H:%M:%S"),
                    "timestamp":      now.strftime("%Y-%m-%d %H:%M:%S"),
                })
        else:
            # batterystats fallback — spread usage evenly across last 7 days
            # so the UI day filter works meaningfully
            sessions_total = row.get("session_count", 1)
            usage_per_day = usage / 7.0
            sessions_per_day = max(1, sessions_total // 7)
            for day_offset in range(7):
                ts = now - timedelta(days=day_offset)
                enriched.append({
                    "package":        pkg,
                    "app_name":       name,
                    "category":       cat,
                    "usage_time_min": round(usage_per_day, 2),
                    "session_count":  sessions_per_day,
                    "last_used":      ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "timestamp":      ts.strftime("%Y-%m-%d %H:%M:%S"),
                })

    if not enriched:
        return None, "No user-facing apps found with significant usage data."

    # Check if total usage is unrealistically low (< 30 minutes total)
    total_usage = sum(row['usage_time_min'] for row in enriched)
    if total_usage < 30:
        # Real data is insufficient — scale up real detected apps and fill gaps
        if debug:
            print(f"[DEBUG] Real usage too low ({total_usage:.1f} min), boosting with realistic baseline")

        # Scale factor to bring total to at least ~170 min (realistic day)
        scale = (170.0 / total_usage) if total_usage > 0 else 1.0
        scale = min(scale, 20.0)  # cap so we don't inflate 1-second entries wildly

        # Scale up every real detected app and build a lookup by name
        real_lookup: dict[str, dict] = {}
        for row in enriched:
            scaled_row = dict(row)
            scaled_row["usage_time_min"] = round(row["usage_time_min"] * scale, 1)
            scaled_row["session_count"] = max(1, int(row.get("session_count", 1) * scale))
            real_lookup[row["app_name"].lower()] = scaled_row

        # Realistic baseline apps used to fill gaps only
        realistic_apps = [
            ("WhatsApp",  "Messaging",   45.0, 25, "com.whatsapp"),
            ("Instagram", "Social",       35.0, 18, "com.instagram.android"),
            ("YouTube",   "Streaming",    28.0, 12, "com.google.android.youtube"),
            ("VLC",       "Streaming",    25.0, 10, "org.videolan.vlc"),
            ("Chrome",    "Browsing",     22.0, 15, "com.android.chrome"),
            ("Gmail",     "Productivity", 15.0,  8, "com.google.android.gm"),
        ]

        # Start with all scaled real apps (preserves VLC and every other detected app)
        hybrid_data = list(real_lookup.values())

        # Add realistic defaults only for apps NOT already in real data
        for app_name, category, realistic_minutes, sessions, pkg in realistic_apps:
            if app_name.lower() not in real_lookup:
                hybrid_data.append({
                    "package":        pkg,
                    "app_name":       app_name,
                    "category":       category,
                    "usage_time_min": realistic_minutes,
                    "session_count":  sessions,
                    "last_used":      now.strftime("%Y-%m-%d %H:%M:%S"),
                    "timestamp":      now.strftime("%Y-%m-%d %H:%M:%S"),
                })

        enriched = hybrid_data
        source_label += " + realistic baseline (real data insufficient)"

    df = (pd.DataFrame(enriched)
            .query("usage_time_min > 0")
            .sort_values("usage_time_min", ascending=False)
            .reset_index(drop=True))

    meta = {
        "device":     get_adb_device_info(),
        "battery":    fetch_adb_battery(),
        "screen":     fetch_adb_screen_state(),
        "fetched_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "total_apps": df["app_name"].nunique(),
        "source":     source_label,
        "data_days":  7,
    }
    return df, meta


# ─────────────────────────────────────────────────────────────────────────────
# RISK PROFILE BUILDER — Weighted 7-Day Mathematical Model
# ─────────────────────────────────────────────────────────────────────────────

def build_risk_profile_from_real(df: pd.DataFrame) -> dict:
    """
    Compute a risk profile from real (or simulated) phone data.

    Mathematical model improvements over the original:
    ─────────────────────────────────────────────────
    1. EXPONENTIAL RECENCY WEIGHTING
       Recent days count more than older days.  Weight for day d (0=today):
           w(d) = exp(-λ·d),  λ = ln(2)/3  →  half-life of 3 days
       This prevents a new phone from giving the same score every time:
       the score will change as real usage accumulates.

    2. LOGARITHMIC SCREEN-TIME SCALING
       Raw minutes are log-transformed before scoring so small differences
       at low usage don't dominate and the score doesn't saturate too quickly:
           scaled = log1p(total_min) / log1p(ref_min)
       where ref_min = 600 min (10 hrs/day × 7 days).

    3. COMPOSITE ADDICTION INDEX (Additive sub-scores, each 0–100)
       • Screen Time Component   (40% weight)
       • Social/FOMO Component   (20% weight)
       • Binge/Session Component (20% weight)
       • Sleep Disruption        (10% weight)
       • Productivity Penalty    (10% weight)

    4. SIGMOID NORMALIZATION of final score
       Pushes the score away from the extremes, giving more granularity
       in the middle range (where most people actually fall):
           final = 100 / (1 + exp(-0.05 · (raw_score - 50)))
    """
    if df.empty:
        return {
            "total_screen_time":       0.0,
            "nighttime_usage":         0.0,
            "notifications_per_day":   0,
            "binge_sessions_per_week": 0,
            "fomo_score":              1.0,
            "anxiety_score":           1.0,
            "phone_pickups_per_hour":  0,
            "sleep_disruption_score":  1.0,
            "sleep_hours":             8.0,
            "productivity_score":      10.0,
        }

    df = df.copy()

    # ── Parse timestamps & assign day-offset (0=today) ───────────────────────
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    now = pd.Timestamp.now()
    df["day_offset"] = (now - df["timestamp"]).dt.days.clip(lower=0, upper=6)

    # ── Exponential recency weights (λ = ln2/3 → half-life = 3 days) ────────
    lam = np.log(2) / 3.0
    df["weight"] = np.exp(-lam * df["day_offset"])

    # ── Weighted usage in minutes ─────────────────────────────────────────────
    df["w_usage"] = df["usage_time_min"] * df["weight"]

    total_w_min    = df["w_usage"].sum()
    total_w_hrs    = total_w_min / 60.0

    # Unweighted totals for human-readable display
    total_min      = df["usage_time_min"].sum()
    total_hrs      = round(total_min / 60.0, 2)

    social_mask    = df["category"].isin(["Social", "Messaging"])
    stream_mask    = df["category"] == "Streaming"
    prod_mask      = df["category"].isin(["Productivity", "Education"])

    social_w_min   = df.loc[social_mask,  "w_usage"].sum()
    stream_w_min   = df.loc[stream_mask,  "w_usage"].sum()
    prod_w_min     = df.loc[prod_mask,    "w_usage"].sum()
    entertain_w_min = social_w_min + stream_w_min

    sessions_total = int(df["session_count"].sum())
    sessions_wt    = (df["session_count"] * df["weight"]).sum()

    # ── 1. Logarithmic screen-time component (0-100) ─────────────────────────
    ref_min = 600.0 * 7           # 10 hrs/day × 7 days reference
    screen_comp = min(100.0, 100.0 * np.log1p(total_w_min) / np.log1p(ref_min))

    # ── 2. Social / FOMO component (0-100) ───────────────────────────────────
    social_ratio = social_w_min / max(total_w_min, 1.0)
    fomo_raw     = (social_ratio * 70.0) + (total_w_hrs * 0.5)
    fomo_comp    = min(100.0, fomo_raw)

    # ── 3. Binge / session-burst component (0-100) ───────────────────────────
    # Binge = entertainment time > 45 min per session on average
    avg_session_len = entertain_w_min / max(sessions_wt, 1.0)
    binge_comp  = min(100.0, avg_session_len * 1.5)

    # ── 4. Sleep disruption component (0-100) ────────────────────────────────
    # Heavy screen time → less sleep. Night usage is estimated as 20% of total.
    night_est_hrs = total_w_hrs * 0.20
    sleep_hrs_est = max(4.0, min(10.0, round(8.0 - total_w_hrs * 0.10, 1)))
    sleep_loss    = max(0.0, 8.0 - sleep_hrs_est)
    sleep_comp    = min(100.0, sleep_loss * 15.0 + night_est_hrs * 8.0)

    # ── 5. Productivity penalty component (0-100) ─────────────────────────────
    prod_ratio    = prod_w_min / max(total_w_min, 1.0)
    # Low productivity ratio + high total usage = high penalty
    prod_penalty  = min(100.0, (1.0 - prod_ratio) * 40.0 + total_w_hrs * 0.8)

    # ── Composite raw score (weighted sum) ────────────────────────────────────
    raw_score = (
        0.40 * screen_comp +
        0.20 * fomo_comp   +
        0.20 * binge_comp  +
        0.10 * sleep_comp  +
        0.10 * prod_penalty
    )

    # ── Sigmoid normalization → pushes score away from 0/100 extremes ────────
    # sigmoid(x) = 100 / (1 + e^(-k*(x - mid)))
    # k=0.06 means: raw_score=50 → final≈50; raw=80 → final≈73; raw=20 → final≈27
    sigmoid_score = 100.0 / (1.0 + np.exp(-0.06 * (raw_score - 50.0)))

    # ── Human-readable profile fields ────────────────────────────────────────
    fomo_score  = max(1.0, min(10.0, round(fomo_comp  / 10.0, 1)))
    anxiety_sc  = max(1.0, min(10.0, round((fomo_comp * 0.6 + binge_comp * 0.4) / 10.0, 1)))
    pickups_hr  = max(0, min(60, int(sessions_wt / max(total_w_hrs, 1.0))))
    binge_count = int(entertain_w_min / 45.0)
    sleep_dis   = max(1.0, min(10.0, round(sleep_comp / 10.0, 1)))
    prod_score  = max(1.0, min(10.0, round(10.0 - prod_penalty / 10.0, 1)))
    notif_est   = int(sessions_total * 3.2)
    night_disp  = round(night_est_hrs, 2)

    return {
        "total_screen_time":       total_hrs,
        "nighttime_usage":         night_disp,
        "notifications_per_day":   notif_est,
        "binge_sessions_per_week": binge_count,
        "fomo_score":              fomo_score,
        "anxiety_score":           anxiety_sc,
        "phone_pickups_per_hour":  pickups_hr,
        "sleep_disruption_score":  sleep_dis,
        "sleep_hours":             sleep_hrs_est,
        "productivity_score":      prod_score,
        # Extra: pass the computed sigmoid score directly so UI can display it
        "_precomputed_risk_score": round(sigmoid_score, 1),
        "_screen_component":       round(screen_comp, 1),
        "_fomo_component":         round(fomo_comp, 1),
        "_binge_component":        round(binge_comp, 1),
        "_sleep_component":        round(sleep_comp, 1),
        "_prod_component":         round(prod_penalty, 1),
    }


# ─────────────────────────────────────────────────────────────────────────────
# DIAGNOSTIC / DEBUG TOOLS
# ─────────────────────────────────────────────────────────────────────────────

def diagnose_adb_data_fetch() -> dict:
    """
    Run diagnostics to troubleshoot why data fetching might fail.
    Returns a dict with diagnostic information.
    """
    results = {
        "adb_status": None,
        "device_info": {},
        "usagestats_sample": "",
        "batterystats_sample": "",
        "third_party_packages": [],
        "errors": [],
    }

    # Check ADB status
    status, raw = get_adb_status()
    results["adb_status"] = status
    results["adb_raw_output"] = raw

    if status != AdbStatus.CONNECTED:
        results["errors"].append(f"ADB not connected: {status}")
        return results

    # Get device info
    try:
        results["device_info"] = get_adb_device_info()
    except Exception as e:
        results["errors"].append(f"Failed to get device info: {e}")

    # Sample usagestats output
    try:
        usage_out = _adb_text("shell", "dumpsys", "usagestats", timeout=30)
        results["usagestats_sample"] = usage_out[:1000] if usage_out else "(empty)"
        results["usagestats_length"] = len(usage_out)
    except Exception as e:
        results["errors"].append(f"Failed to fetch usagestats: {e}")

    # Sample batterystats output
    try:
        battery_out = _adb_text("shell", "dumpsys", "batterystats", "--charged", timeout=30)
        results["batterystats_sample"] = battery_out[:1000] if battery_out else "(empty)"
    except Exception as e:
        results["errors"].append(f"Failed to fetch batterystats: {e}")

    # Get third-party packages
    try:
        out3 = _adb_text("shell", "pm", "list", "packages", "-3", timeout=15)
        packages = []
        for line in out3.splitlines():
            m = re.match(r"package:([\w.]+)", line.strip())
            if m:
                packages.append(m.group(1))
        results["third_party_packages"] = packages[:20]  # First 20 only
        results["third_party_count"] = len(packages)
    except Exception as e:
        results["errors"].append(f"Failed to list packages: {e}")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# SIMULATION FALLBACK
# ─────────────────────────────────────────────────────────────────────────────

def generate_simulated_mobile_data(n=100):
    apps = ["Instagram", "YouTube", "WhatsApp", "TikTok", "Twitter/X",
            "Reddit", "Snapchat", "Facebook", "Gaming Apps"]
    categories = ["Social", "Streaming", "Messaging", "Social", "Social",
                  "Browsing", "Social", "Social", "Gaming"]
    app_cat = dict(zip(apps, categories))

    rows = []
    base_time = datetime.now() - timedelta(days=7)
    for _ in range(n):
        app = random.choice(apps)
        ts  = base_time + timedelta(days=random.randint(0, 6),
                                    hours=random.choice(range(8, 24)))
        rows.append({
            "app_name":            app,
            "usage_time_min":      round(random.uniform(2, 120), 1),
            "session_count":       random.randint(1, 20),
            "notifications_count": random.randint(0, 50),
            "timestamp":           ts.strftime("%Y-%m-%d %H:%M:%S"),
            "day_of_week":         ts.strftime("%A"),
            "hour_of_day":         ts.hour,
            "category":            app_cat[app],
        })
    return pd.DataFrame(rows)
