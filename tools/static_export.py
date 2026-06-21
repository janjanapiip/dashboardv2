"""Render the dashboard as a static snapshot for Vercel hosting.

Usage:
    python tools/static_export.py            # writes dist/
    python tools/static_export.py --quiet    # suppress progress lines

Output layout (under dist/):
    index.html                 -> latest monthly view
    YYYY-MM.html               -> one per period with data
    year-YYYY.html             -> yearly overview
    gallery.html               -> photo gallery
    api/period-YYYY-MM.json    -> per-period JSON (for cell hover preview)
    export/Rekap_Utilisasi_YYYY-MM.xlsx
    static/...                 -> copied from project static/
    uploads/photos/...         -> copied from data/uploads/photos/
    vercel.json                -> rewrites for clean URLs

The exporter sets SPP_STATIC_EXPORT=1 before importing app.py so templates
render in read-only mode (admin/login UI hidden, period picker becomes a
JS-navigating dropdown, etc.).
"""
import hashlib
import os
import re
import shutil
import sys
from pathlib import Path

os.environ["SPP_STATIC_EXPORT"] = "1"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Late imports so SPP_STATIC_EXPORT is set first
from app import app, available_periods, available_years  # noqa: E402

DIST = ROOT / "dist"
QUIET = "--quiet" in sys.argv

# Asset paths that are referenced from <link>/<script> tags. Each gets a
# content-hash query string appended at export time so browser caches refresh
# the moment the file changes — and otherwise serve the long-cached copy.
HASHABLE_ASSETS = [
    "css/style.css",
    "js/dashboard.js",
    "js/year.js",
    "js/admin.js",
]
ASSET_HASHES: dict[str, str] = {}


def log(msg: str) -> None:
    if not QUIET:
        print(msg)


def rewrite_html(html: str) -> str:
    """Convert any leftover query-string URLs to static paths, and append
    content-hash cache-busters to known CSS/JS asset URLs."""
    # Cache-bust CSS/JS by appending ?v=<hash> to known asset URLs
    for url, h in ASSET_HASHES.items():
        # Match both `href="..."` and `src="..."` cleanly without double-appending
        for attr in ("href", "src"):
            old = f'{attr}="{url}"'
            new = f'{attr}="{url}?v={h}"'
            html = html.replace(old, new)
    # /?year=2026&month=3 (with possibly & or &amp;) -> /2026-03.html
    html = re.sub(
        r'href="/\?year=(\d+)&(?:amp;)?month=(\d+)"',
        lambda m: f'href="/{int(m.group(1))}-{int(m.group(2)):02d}.html"',
        html,
    )
    # /year?year=2026 -> /year-2026.html
    html = re.sub(
        r'href="/year\?year=(\d+)"',
        lambda m: f'href="/year-{int(m.group(1))}.html"',
        html,
    )
    # /export?year=Y&month=M -> /export/Rekap_Utilisasi_YYYY-MM.xlsx
    html = re.sub(
        r'href="/export\?year=(\d+)&(?:amp;)?month=(\d+)"',
        lambda m: f'href="/export/Rekap_Utilisasi_{int(m.group(1))}-{int(m.group(2)):02d}.xlsx"',
        html,
    )
    return html


def _compute_asset_hashes() -> None:
    """Populate ASSET_HASHES from the files we just copied into dist/static/."""
    for rel in HASHABLE_ASSETS:
        p = DIST / "static" / rel
        if not p.exists():
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()[:8]
        ASSET_HASHES[f"/static/{rel}"] = digest
    if not QUIET:
        for url, h in ASSET_HASHES.items():
            log(f"  Cache-bust: {url}?v={h}")


def save(rel_path: str, content: bytes) -> None:
    target = DIST / rel_path.lstrip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def save_html(rel_path: str, raw_bytes: bytes) -> None:
    save(rel_path, rewrite_html(raw_bytes.decode("utf-8")).encode("utf-8"))


VERCEL_JSON = b"""\
{
  "cleanUrls": false,
  "trailingSlash": false,
  "rewrites": [
    { "source": "/year",                "destination": "/year.html" },
    { "source": "/year/:year",          "destination": "/year-:year.html" },
    { "source": "/period/:year/:month", "destination": "/:year-:month.html" },
    { "source": "/gallery",             "destination": "/gallery.html" }
  ],
  "headers": [
    { "source": "/(.*).html",      "headers": [{ "key": "Cache-Control", "value": "public, max-age=60, s-maxage=60, must-revalidate" }] },
    { "source": "/uploads/(.*)",   "headers": [{ "key": "Cache-Control", "value": "public, max-age=86400, immutable" }] },
    { "source": "/static/(.*)",    "headers": [{ "key": "Cache-Control", "value": "public, max-age=86400" }] },
    { "source": "/api/(.*).json",  "headers": [{ "key": "Cache-Control", "value": "public, max-age=60, s-maxage=60, must-revalidate" }] }
  ]
}
"""


# Preserve these entries across re-exports — they hold Vercel link state and
# would force the user to re-link the project every time otherwise.
PRESERVE = {".vercel", ".git"}


def _clear_dist() -> None:
    """Remove dist/ contents but tolerate the top-level dir being locked (Explorer, antivirus).
    Preserves entries listed in PRESERVE (e.g. .vercel/ from `vercel link`)."""
    if not DIST.exists():
        DIST.mkdir(parents=True)
        return
    log(f"  Membersihkan {DIST.relative_to(ROOT)}/ (mempertahankan {', '.join(sorted(PRESERVE))}) ...")
    for child in DIST.iterdir():
        if child.name in PRESERVE:
            continue
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=False)
        else:
            child.unlink(missing_ok=True)


def main() -> int:
    _clear_dist()

    log(f"  Menyalin static/ ...")
    shutil.copytree(ROOT / "static", DIST / "static")
    _compute_asset_hashes()

    photos_src = ROOT / "data" / "uploads" / "photos"
    if photos_src.exists() and any(photos_src.iterdir()):
        log(f"  Menyalin foto kegiatan ...")
        shutil.copytree(photos_src, DIST / "uploads" / "photos", dirs_exist_ok=True)
    else:
        (DIST / "uploads" / "photos").mkdir(parents=True, exist_ok=True)

    periods = available_periods()
    years = available_years()
    log(f"  Periode: {len(periods)} bulan, {len(years)} tahun.")

    client = app.test_client()

    # Latest monthly view = / and /index.html
    if periods:
        y, m = periods[0]
        log(f"  Menulis index.html (terkini: {m:02d}/{y}) ...")
        r = client.get(f"/?year={y}&month={m}")
        if r.status_code != 200:
            print(f"  ERROR: GET /?year={y}&month={m} -> {r.status_code}")
            return 1
        save_html("index.html", r.data)
    else:
        log("  Tidak ada data periode &mdash; menulis index.html kosong.")
        r = client.get("/")
        save_html("index.html", r.data)

    # Each monthly period
    for y, m in periods:
        log(f"  Menulis {y}-{m:02d}.html ...")
        r = client.get(f"/?year={y}&month={m}")
        if r.status_code != 200:
            print(f"  ERROR: GET /?year={y}&month={m} -> {r.status_code}")
            return 1
        save_html(f"{y}-{m:02d}.html", r.data)

    # Year overviews
    for y in years:
        log(f"  Menulis year-{y}.html ...")
        r = client.get(f"/year?year={y}")
        if r.status_code != 200:
            print(f"  ERROR: GET /year?year={y} -> {r.status_code}")
            return 1
        save_html(f"year-{y}.html", r.data)
    # /year alias points at the latest year
    if years:
        save_html("year.html", client.get(f"/year?year={years[0]}").data)

    # Gallery
    log("  Menulis gallery.html ...")
    save_html("gallery.html", client.get("/gallery").data)

    # JSON snapshots used by client-side hover preview
    log("  Menulis API JSON snapshots ...")
    for y, m in periods:
        r = client.get(f"/api/period?year={y}&month={m}")
        if r.status_code == 200:
            save(f"api/period-{y}-{m:02d}.json", r.data)

    # Excel downloads
    log("  Menulis Excel exports ...")
    for y, m in periods:
        r = client.get(f"/export?year={y}&month={m}")
        if r.status_code == 200:
            save(f"export/Rekap_Utilisasi_{y}-{m:02d}.xlsx", r.data)

    # Vercel config
    save("vercel.json", VERCEL_JSON)

    # 404 fallback
    save_html("404.html", client.get("/__not_found__").data if client.get("/__not_found__").status_code == 404 else
              b"<!doctype html><meta charset=utf-8><title>404</title><body><h1>404</h1>"
              b"<p><a href='/'>Kembali ke dashboard</a></p>")

    log("")
    log(f"  Selesai. Snapshot ada di: {DIST}")
    log(f"  Deploy ke Vercel: vercel --prod {DIST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
