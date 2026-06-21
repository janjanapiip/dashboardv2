"""Indonesia public-holiday sync. Best-effort, offline-tolerant.

Primary source: Google Calendar's public Indonesian holidays iCal feed
(`id.indonesian#holiday@group.v.calendar.google.com`). Credible, includes
both 'Hari libur nasional' and 'Cuti bersama', and works without any API key.

Fallback: date.nager.at (international, well-maintained, national holidays only).
"""
import json
import urllib.request
import urllib.error
from datetime import date

from db import get_conn

USER_AGENT = "spp-utilisasi-dashboard/1.0"
TIMEOUT = 15

GOOGLE_ICAL_URL = (
    "https://calendar.google.com/calendar/ical/"
    "id.indonesian%23holiday%40group.v.calendar.google.com/public/basic.ics"
)
NAGER_URL = "https://date.nager.at/api/v3/PublicHolidays/{year}/ID"


def _http_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _http_json(url: str):
    return json.loads(_http_text(url))


def _parse_ical_events(text: str):
    """Yield (date_iso, summary, description) for each VEVENT in the iCal feed."""
    cur = None
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            if cur:
                yield cur
            cur = None
        elif cur is not None and ":" in line:
            key, _, val = line.partition(":")
            key = key.split(";", 1)[0]
            if key == "DTSTART":
                cur["date"] = val
            elif key == "SUMMARY":
                cur["summary"] = val
            elif key == "DESCRIPTION":
                cur["description"] = val


def _from_google_ical(year: int):
    body = _http_text(GOOGLE_ICAL_URL)
    out = []
    year_str = str(year)
    seen = set()
    for ev in _parse_ical_events(body):
        d_raw = ev.get("date", "")
        if len(d_raw) < 8 or not d_raw[:4] == year_str:
            continue
        d_iso = f"{d_raw[:4]}-{d_raw[4:6]}-{d_raw[6:8]}"
        name = (ev.get("summary") or "").strip()
        if not name:
            continue
        desc = (ev.get("description") or "").lower()
        is_cb = "cuti bersama" in desc or "cuti bersama" in name.lower()
        is_nat = 0 if is_cb else 1
        key = (d_iso, name)
        if key in seen:
            continue
        seen.add(key)
        out.append((d_iso, name, is_nat, "google-calendar"))
    return out


def _from_nager(year: int):
    data = _http_json(NAGER_URL.format(year=year))
    out = []
    for item in data:
        d = item.get("date")
        n = (item.get("localName") or item.get("name") or "").strip()
        if d and n:
            out.append((d, n, 1, "date.nager.at"))
    return out


def sync_year(year: int) -> dict:
    """Try primary source, then fallback. Upsert into holiday table. Returns status dict."""
    sources_tried = []
    fetched = []
    err = None

    for fn, label in [(_from_google_ical, "google-calendar"), (_from_nager, "date.nager.at")]:
        sources_tried.append(label)
        try:
            fetched = fn(year)
            if fetched:
                err = None
                break
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as e:
            err = str(e)
            continue

    if not fetched:
        return {"ok": False, "year": year, "count": 0, "error": err or "no data", "tried": sources_tried}

    with get_conn() as conn:
        conn.execute("DELETE FROM holiday WHERE date LIKE ?", (f"{year}-%",))
        conn.executemany(
            "INSERT OR REPLACE INTO holiday (date, name, is_national, source, synced_at) "
            "VALUES (?,?,?,?, datetime('now'))",
            fetched,
        )
        conn.commit()
    return {"ok": True, "year": year, "count": len(fetched), "source": fetched[0][3]}


def get_for_period(year: int, month: int) -> dict:
    """Return {day:int -> {"name": str, "is_national": bool}} for the month."""
    prefix = f"{year}-{month:02d}-"
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date, name, is_national FROM holiday WHERE date LIKE ? ORDER BY date",
            (f"{prefix}%",),
        ).fetchall()
    out = {}
    for r in rows:
        try:
            day = int(r["date"].split("-")[2])
            out[day] = {"name": r["name"], "is_national": bool(r["is_national"])}
        except (ValueError, IndexError):
            continue
    return out


def get_today(today: date) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT name FROM holiday WHERE date=?", (today.isoformat(),)
        ).fetchone()
    return row["name"] if row else None


def has_any_for_year(year: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM holiday WHERE date LIKE ? LIMIT 1", (f"{year}-%",)
        ).fetchone()
    return bool(row)
