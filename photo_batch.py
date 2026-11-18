"""Batch import of activity photos (folder or .zip), mainly WhatsApp exports.

Pure helpers only — routes live in app.py. Zip entries are read into memory by
basename; nothing is ever extracted to an archive-supplied path.
"""
import hashlib
import re
import shutil
import time
import zipfile
from datetime import date
from pathlib import Path

# WhatsApp Desktop/Web: "WhatsApp Image 2026-06-08 at 14.05.02 (1).jpeg"
WA_DESKTOP = re.compile(r"(\d{4})-(\d{2})-(\d{2}) at (\d{1,2})\.(\d{2})")
# WhatsApp Android media folder: "IMG-20260608-WA0012.jpg" (date only)
WA_ANDROID = re.compile(r"IMG-(\d{4})(\d{2})(\d{2})-WA\d+", re.I)

TOKEN_RE = re.compile(r"[0-9a-f]{16}")


def basename(name: str) -> str:
    return re.split(r"[\\/]", name or "")[-1]


def ext_of(name: str) -> str:
    return name.rsplit(".", 1)[1].lower() if "." in name else ""


def parse_wa_datetime(name: str) -> tuple[date | None, str]:
    """(date, 'HH:MM' or '') from a WhatsApp photo filename; (None, '') if no match."""
    try:
        m = WA_DESKTOP.search(name)
        if m:
            y, mo, d, h, mi = (int(x) for x in m.groups())
            return date(y, mo, d), (f"{h:02d}:{mi:02d}" if h < 24 and mi < 60 else "")
        m = WA_ANDROID.search(name)
        if m:
            return date(*(int(x) for x in m.groups())), ""
    except ValueError:  # e.g. 2026-02-30
        pass
    return None, ""


TOO_BIG = "Ukuran melebihi 2 MB."


def iter_sources(file_storages, allowed_ext, max_bytes, stats):
    """Yield (name, data, error) for every image in the uploads, expanding .zip files.

    One item in memory at a time (caller stages it to disk). Non-image entries
    only bump stats["skipped"]; oversized/encrypted/corrupt ones yield an error
    so the admin sees them in the review table.
    """
    for fs in file_storages:
        name = basename(fs.filename)
        ext = ext_of(name)
        if ext == "zip":
            try:
                with zipfile.ZipFile(fs.stream) as zf:
                    for info in zf.infolist():
                        entry = basename(info.filename)
                        if info.is_dir() or not entry or entry.startswith(".") \
                                or "__MACOSX" in info.filename:
                            continue
                        if ext_of(entry) not in allowed_ext:
                            stats["skipped"] += 1
                        elif info.flag_bits & 0x1:
                            yield entry, None, "Berkas di ZIP terenkripsi."
                        elif info.file_size > max_bytes:
                            yield entry, None, TOO_BIG
                        else:
                            with zf.open(info) as fh:  # header sizes can lie: cap the read
                                data = fh.read(max_bytes + 1)
                            yield (entry, None, TOO_BIG) if len(data) > max_bytes else (entry, data, None)
            except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError, EOFError):
                yield name, None, "Berkas ZIP rusak atau tidak dapat dibaca."
        elif ext in allowed_ext:
            data = fs.stream.read(max_bytes + 1)
            yield (name, None, TOO_BIG) if len(data) > max_bytes else (name, data, None)
        else:
            stats["skipped"] += 1  # desktop.ini, .txt, videos, ...


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def staging_dir(root: Path, token: str) -> Path | None:
    """Resolve a staging dir from an untrusted token; None if invalid/missing."""
    if not TOKEN_RE.fullmatch(token or ""):
        return None
    d = root / token
    return d if d.is_dir() else None


def purge_stale(root: Path, max_age_s: int = 24 * 3600) -> None:
    """Drop abandoned staging batches (review never committed/cancelled)."""
    if not root.exists():
        return
    cutoff = time.time() - max_age_s
    for d in root.iterdir():
        if d.is_dir() and TOKEN_RE.fullmatch(d.name) and d.stat().st_mtime < cutoff:
            shutil.rmtree(d, ignore_errors=True)
