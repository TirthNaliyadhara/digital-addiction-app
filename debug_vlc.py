"""
debug_vlc.py  —  Shows exactly what Samsung's usagestats says about VLC
Run:  python debug_vlc.py
"""
import subprocess, re, sys, os, shutil

# ── find adb ──────────────────────────────────────────────────────────────────
ADB_PATHS = [
    r"C:\Users\Administrator\platform-tools\adb.exe",
    "adb",
    os.path.expandvars(r"%USERPROFILE%\platform-tools\adb.exe"),
    r"C:\platform-tools\adb.exe",
]

def find_adb():
    for p in ADB_PATHS:
        if shutil.which(p) or os.path.isfile(p):
            return p
    return None

adb = find_adb()
if not adb:
    print("ERROR: adb not found"); sys.exit(1)

print(f"Using ADB: {adb}")
print("Fetching usagestats (this takes ~30s)…")
r = subprocess.run([adb, "shell", "dumpsys", "usagestats"],
                   capture_output=True, timeout=90)
out = r.stdout.decode("utf-8", errors="replace")

print(f"\nTotal dump size: {len(out):,} chars")

# ── Find every line that mentions vlc ────────────────────────────────────────
VLC_PKG = "org.videolan.vlc"
vlc_lines = [l for l in out.splitlines() if VLC_PKG in l]

print(f"\n=== Lines mentioning '{VLC_PKG}': {len(vlc_lines)} ===")
for l in vlc_lines[:80]:          # show up to 80 lines
    print(" ", l)

# ── Show all distinct event types seen in the dump ───────────────────────────
type_re = re.compile(r'type=(\S+)')
all_types = set()
for l in out.splitlines():
    m = type_re.search(l)
    if m:
        all_types.add(m.group(1))

print(f"\n=== All event type values seen in dump ===")
for t in sorted(all_types):
    print(" ", t)

# ── Show a 10-line sample of the format around a VLC event ───────────────────
if vlc_lines:
    print(f"\n=== Context around first VLC line ===")
    all_lines = out.splitlines()
    idx = next(i for i, l in enumerate(all_lines) if VLC_PKG in l)
    for l in all_lines[max(0, idx-3): idx+8]:
        print(" ", l)
