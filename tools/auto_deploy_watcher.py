"""Watch the local database + uploads, auto-publish to Vercel after a quiet period.

Usage:
    python tools/auto_deploy_watcher.py            # 60 s debounce
    python tools/auto_deploy_watcher.py --quiet 30 # 30 s debounce
    python tools/auto_deploy_watcher.py --once     # one cycle then exit

Why a debounce? Saving a single cell triggers exactly one DB write, but a busy
editing session writes many times per minute. The watcher resets its timer on
every change, so it only runs the export+deploy after you've stopped editing
for the configured number of seconds.

Stop the watcher with Ctrl+C.
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from vercel_auth import ensure_authenticated, find_vercel_cli

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "app.db"
PHOTOS_DIR = ROOT / "data" / "uploads" / "photos"

POLL_INTERVAL = 2.0  # seconds between mtime checks


def fingerprint() -> tuple[int, float, int]:
    """Cheap state fingerprint: (db_size, db_mtime, photo_count). Misses no-op edits."""
    db_size = db_mtime = 0
    if DB_PATH.exists():
        st = DB_PATH.stat()
        db_size, db_mtime = st.st_size, st.st_mtime
    photo_count = 0
    if PHOTOS_DIR.exists():
        photo_count = sum(1 for _ in PHOTOS_DIR.iterdir() if _.is_file())
    return (db_size, round(db_mtime, 2), photo_count)


def export_and_deploy(vercel_cli: str, dist: Path) -> bool:
    print(f"  [{datetime.now():%H:%M:%S}] Menjalankan static_export ...")
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "static_export.py"), "--quiet"],
        cwd=str(ROOT),
    )
    if r.returncode != 0:
        print(f"  [{datetime.now():%H:%M:%S}] static_export gagal (exit {r.returncode}).")
        return False
    print(f"  [{datetime.now():%H:%M:%S}] Verifikasi login Vercel ...")
    token = ensure_authenticated(vercel_cli)
    print(f"  [{datetime.now():%H:%M:%S}] Mendeploy ke Vercel ...")
    cmd = [vercel_cli, "--prod", "--yes"]
    if token:
        cmd += ["--token", token]
    r = subprocess.run(cmd, cwd=str(dist))
    if r.returncode != 0:
        print(f"  [{datetime.now():%H:%M:%S}] vercel deploy gagal (exit {r.returncode}).")
        return False
    print(f"  [{datetime.now():%H:%M:%S}] Deploy berhasil.")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", type=int, default=60,
                    help="Detik tanpa perubahan sebelum deploy (default 60)")
    ap.add_argument("--once", action="store_true",
                    help="Lakukan satu siklus deploy lalu keluar")
    args = ap.parse_args()

    vercel_cli = find_vercel_cli()
    if not vercel_cli:
        print("ERROR: Vercel CLI tidak ditemukan. Jalankan 'npm install -g vercel' dulu.")
        return 2
    dist = ROOT / "dist"

    print(f"Auto-deploy watcher aktif.")
    print(f"  Database  : {DB_PATH}")
    print(f"  Foto      : {PHOTOS_DIR}")
    print(f"  Debounce  : {args.quiet} detik")
    print(f"  Vercel CLI: {vercel_cli}")
    print(f"  Tekan Ctrl+C untuk berhenti.\n")

    if args.once:
        return 0 if export_and_deploy(vercel_cli, dist) else 1

    last_fp = fingerprint()
    last_change = None  # type: float | None

    try:
        while True:
            time.sleep(POLL_INTERVAL)
            fp = fingerprint()
            if fp != last_fp:
                if last_change is None:
                    print(f"  [{datetime.now():%H:%M:%S}] Perubahan terdeteksi. "
                          f"Menunggu {args.quiet} dtk tanpa perubahan lebih lanjut ...")
                else:
                    print(f"  [{datetime.now():%H:%M:%S}] Perubahan baru, debounce direset.")
                last_fp = fp
                last_change = time.monotonic()
                continue

            if last_change is not None and (time.monotonic() - last_change) >= args.quiet:
                last_change = None
                export_and_deploy(vercel_cli, dist)
                # Re-baseline after deploy: prevents the deploy artifacts in dist/
                # from being re-detected as a "change".
                last_fp = fingerprint()
                print(f"  [{datetime.now():%H:%M:%S}] Menunggu perubahan berikutnya ...\n")
    except KeyboardInterrupt:
        print("\nWatcher dihentikan.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
