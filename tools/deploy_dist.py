"""Build the static snapshot and deploy dist/ to Vercel.

Replaces the old `cd dist && vercel --prod --yes` flow with one that verifies
(and auto-recovers) Vercel CLI auth first, and passes --token explicitly when
VERCEL_TOKEN is set in .env.

Usage:
    python tools/deploy_dist.py              # build + deploy
    python tools/deploy_dist.py --no-build   # deploy whatever is already in dist/
"""
import subprocess
import sys
from pathlib import Path

# Same-dir import works because Python prepends the script's directory to sys.path.
from vercel_auth import ensure_authenticated, find_vercel_cli

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


def build() -> int:
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / "static_export.py")],
        cwd=str(ROOT),
    ).returncode


def deploy(cli: str, token: str | None) -> int:
    cmd = [cli, "--prod", "--yes"]
    if token:
        cmd += ["--token", token]
    return subprocess.run(cmd, cwd=str(DIST)).returncode


def main() -> int:
    cli = find_vercel_cli()
    if not cli:
        print("[deploy] Vercel CLI not found. Install with: npm install -g vercel")
        return 2

    if "--no-build" not in sys.argv:
        rc = build()
        if rc != 0:
            print(f"[deploy] static_export failed (exit {rc}).")
            return rc

    token = ensure_authenticated(cli)
    return deploy(cli, token)


if __name__ == "__main__":
    sys.exit(main())
