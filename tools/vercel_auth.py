"""Verify (and auto-recover) Vercel CLI authentication before a deploy.

Two modes, picked automatically:

1. **Token mode (recommended for unattended/auto-deploy).** Put a Vercel
   personal access token in `.env`:

       VERCEL_TOKEN=xxxxxxxxxxxxxxxx

   Generate one at https://vercel.com/account/tokens. The deploy scripts will
   pass it via `vercel --token`, so the auto_deploy watcher never gets stuck
   on an expired browser login.

2. **CLI-login mode.** If no token is set we fall back to credentials saved
   by `vercel login`. If those have expired (or never existed), this module
   automatically launches `vercel login` so you can re-authenticate in one
   click.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WHOAMI_TIMEOUT = 15  # seconds; long enough for normal whoami, short enough to catch a stuck login flow


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env")


def find_vercel_cli() -> str | None:
    cli = shutil.which("vercel")
    if cli:
        return cli
    # npm global installs on Windows land here but aren't always on PATH for batch scripts.
    candidate = Path(os.environ.get("APPDATA", "")) / "npm" / "vercel.cmd"
    return str(candidate) if candidate.exists() else None


def _whoami(cli: str, token: str | None) -> bool:
    cmd = [cli, "whoami"]
    if token:
        cmd += ["--token", token]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=WHOAMI_TIMEOUT,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        # whoami without creds starts the device-auth flow and blocks reading stdin.
        return False
    if result.returncode != 0:
        return False
    combined = (result.stdout or "") + (result.stderr or "")
    return "No existing credentials" not in combined


def ensure_authenticated(cli: str) -> str | None:
    """Make sure the Vercel CLI is ready to deploy.

    Returns the token to pass to deploy commands (when in token mode), or None
    when relying on the saved CLI login. Exits with code 2 on unrecoverable
    auth failure.
    """
    _load_env()
    token = (os.environ.get("VERCEL_TOKEN") or "").strip() or None

    if token:
        if _whoami(cli, token):
            return token
        print("[vercel] VERCEL_TOKEN is set but invalid/expired.")
        print("[vercel] Generate a fresh token at https://vercel.com/account/tokens")
        print("[vercel] then update VERCEL_TOKEN in your .env file.")
        sys.exit(2)

    if _whoami(cli, None):
        return None

    print("[vercel] CLI login expired or missing. Launching `vercel login` ...")
    rc = subprocess.run([cli, "login"]).returncode
    if rc != 0:
        print("[vercel] `vercel login` failed.")
        sys.exit(2)
    if not _whoami(cli, None):
        print("[vercel] Still not authenticated after `vercel login`. Aborting.")
        sys.exit(2)
    print("[vercel] Re-authenticated.")
    return None


if __name__ == "__main__":
    # Convenience: `python tools/vercel_auth.py` runs a one-shot check.
    cli = find_vercel_cli()
    if not cli:
        print("Vercel CLI not found. Install with: npm install -g vercel")
        sys.exit(2)
    tok = ensure_authenticated(cli)
    print(f"OK (mode={'token' if tok else 'cli-login'})")
