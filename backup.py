"""Timestamped snapshots of data/app.db before destructive operations."""
import re
import shutil
from datetime import datetime
from pathlib import Path

from db import DB_PATH, DATA_DIR

BACKUP_DIR = DATA_DIR / "backups"
KEEP_BACKUPS = 30
SAFE_REASON = re.compile(r"[^A-Za-z0-9_\-]")


def _safe(reason: str) -> str:
    return SAFE_REASON.sub("_", reason)[:48] or "manual"


def create_backup(reason: str = "manual") -> Path | None:
    """Copy the live DB to data/backups/app_<ts>_<reason>.db. Returns the path or None if DB missing."""
    if not DB_PATH.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"app_{ts}_{_safe(reason)}.db"
    shutil.copy2(DB_PATH, dest)
    _rotate()
    return dest


def _rotate(keep: int = KEEP_BACKUPS) -> None:
    files = sorted(BACKUP_DIR.glob("app_*.db"))
    excess = len(files) - keep
    for f in files[:max(0, excess)]:
        f.unlink(missing_ok=True)


def list_backups() -> list[dict]:
    if not BACKUP_DIR.exists():
        return []
    out = []
    for f in sorted(BACKUP_DIR.glob("app_*.db"), reverse=True):
        st = f.stat()
        out.append({
            "name": f.name,
            "size_kb": round(st.st_size / 1024, 1),
            "created": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return out


def restore_backup(name: str) -> Path:
    """Replace the live DB with a backup. The current DB is itself backed up first."""
    src = BACKUP_DIR / name
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(name)
    if SAFE_REASON.search(name.replace(".db", "")):
        raise ValueError("invalid backup name")
    create_backup("pre_restore")
    shutil.copy2(src, DB_PATH)
    return DB_PATH
