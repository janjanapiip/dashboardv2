import re
from calendar import monthrange
from difflib import SequenceMatcher
import openpyxl
from labs import LABS, MONTHS_LOOKUP

FIRST_DATA_ROW = 12  # row 12 = lab #1, row 13 = lab #2, ... row 24 = lab #13

LAB_NAME_BY_ID = {lab_id: name for lab_id, _, name in LABS}

# Per-date activity lines in the KETERANGAN cell look like:
#   05/01 : PUKP, Pasis : Try out
#   12/1  : PUKP, Pasis, Taruna : UKP
#   14/1/ : ...  (trailing slash typo — tolerated)
#   05/01/2026 : ...   (optional year)
# Body after the date is split on the FIRST remaining colon: left=users, right=activity.
# Lines that don't match are returned as leftover text so they can still be
# stored in the legacy whole-month `keterangan` note.
_DETAIL_LINE_RE = re.compile(
    r"^\s*(?P<day>\d{1,2})\s*/\s*(?P<month>\d{1,2})(?:\s*/\s*(?P<year>\d{2,4}))?\s*/?\s*[:\-]\s*(?P<body>.+?)\s*$"
)


def parse_detail_lines(text, sheet_year: int, sheet_month: int):
    """Split a KETERANGAN cell into per-date detail entries + leftover free text.

    Returns (details, leftover) where:
      details  = list of {"day": int, "users": str, "activity": str}
      leftover = list of original lines that didn't match the dd/mm pattern
    """
    if text is None:
        return [], []
    details: list[dict] = []
    leftover: list[str] = []
    days_in_month = monthrange(sheet_year, sheet_month)[1]

    for raw in str(text).splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _DETAIL_LINE_RE.match(line)
        if not m:
            leftover.append(line)
            continue
        try:
            day = int(m.group("day"))
            month = int(m.group("month"))
        except (TypeError, ValueError):
            leftover.append(line)
            continue
        # Reject dates that can't belong to this sheet's month.
        if month != sheet_month or day < 1 or day > days_in_month:
            leftover.append(line)
            continue
        body = m.group("body").strip()
        if ":" in body:
            users, activity = body.split(":", 1)
        else:
            users, activity = "", body
        details.append({
            "day": day,
            "users": users.strip(),
            "activity": activity.strip(),
        })
    return details, leftover


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _find_sheet(wb):
    for name in wb.sheetnames:
        if "master" in name.lower() or "utilisas" in name.lower() or "rekap" in name.lower():
            return wb[name]
    return wb[wb.sheetnames[0]]


def _parse_period(ws):
    year = None
    month = None
    for r in range(1, 12):
        for c in range(1, 10):
            v = ws.cell(row=r, column=c).value
            if not v:
                continue
            s = str(v).lower()
            m_year = re.search(r"(20\d{2})", s)
            if m_year:
                year = int(m_year.group(1))
            for name_low, num in MONTHS_LOOKUP.items():
                if name_low in s:
                    month = num
                    break
            if year and month:
                return year, month
    return year, month


def _find_lab_row(ws, lab_id, lab_name):
    """Best-effort name match within rows 12-30 with positional fallback (row = 11 + lab_id).
    Tolerates typos like 'ENGINEEIRNG WORKSHOP' via SequenceMatcher."""
    target = _normalize(lab_name)
    best_ratio, best_row = 0.0, None
    for r in range(FIRST_DATA_ROW, 31):
        v = ws.cell(row=r, column=2).value
        if not v:
            continue
        normalized = _normalize(str(v))
        if normalized == target:
            return r
        ratio = SequenceMatcher(None, normalized, target).ratio()
        if ratio > best_ratio:
            best_ratio, best_row = ratio, r
    if best_ratio >= 0.6:
        return best_row
    # Positional fallback: standard Master Format places lab N at row 11+N
    fallback = FIRST_DATA_ROW + lab_id - 1
    if ws.cell(row=fallback, column=2).value:
        return fallback
    return None


def _parse_sheet(ws):
    """Parse a single worksheet using the Master Format layout. Returns dict with
    year/month/rows/keterangan, or raises ValueError if the sheet doesn't look like one."""
    year, month = _parse_period(ws)
    if not year or not month:
        raise ValueError(
            "Tidak ada keterangan bulan/tahun pada baris 6-8 ('BULAN : <Bulan> <Tahun>')."
        )

    days_in_month = monthrange(year, month)[1]
    rows = []
    keterangan = {}
    details = []

    for lab_id, _, lab_name in LABS:
        r = _find_lab_row(ws, lab_id, lab_name)
        if r is None:
            continue
        for d in range(1, days_in_month + 1):
            base_col = 6 + (d - 1) * 3  # F=6 -> day 1
            fr_v = ws.cell(row=r, column=base_col).value
            jlh_v = ws.cell(row=r, column=base_col + 1).value
            drs_v = ws.cell(row=r, column=base_col + 2).value
            fr = int(fr_v) if isinstance(fr_v, (int, float)) and fr_v is not None else 0
            jlh = int(jlh_v) if isinstance(jlh_v, (int, float)) and jlh_v is not None else 0
            try:
                drs = float(drs_v) if drs_v is not None and str(drs_v).strip() != "" else 0.0
            except (TypeError, ValueError):
                drs = 0.0
            if fr or jlh or drs:
                rows.append({"lab_id": lab_id, "day": d, "fr": fr, "jlh": jlh, "drs": drs})

        ket_col = 6 + days_in_month * 3
        ket = ws.cell(row=r, column=ket_col).value
        if ket and str(ket).strip():
            parsed_details, leftover = parse_detail_lines(ket, year, month)
            for item in parsed_details:
                details.append({"lab_id": lab_id, **item})
            # Only what didn't parse as a date-specific line is kept as the
            # whole-month note. Empty leftover -> drop the note entirely.
            residual = "\n".join(leftover).strip()
            if residual:
                keterangan[lab_id] = residual

    return {
        "year": year, "month": month,
        "rows": rows, "keterangan": keterangan,
        "details": details,
    }


def parse_master_format(path):
    """Single-sheet parse: picks the sheet that looks like Master Format, raises on failure."""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = _find_sheet(wb)
    return _parse_sheet(ws)


def parse_all_sheets(path):
    """Iterate every worksheet (left-to-right). Return a list with one entry per sheet:
        {sheet, ok, [year, month, rows, keterangan] or [error]}.
    Sheets that don't look like Master Format are reported as skipped, not fatal —
    so a workbook with a cover sheet + 12 month tabs is fine.
    """
    wb = openpyxl.load_workbook(path, data_only=True)
    results = []
    for name in wb.sheetnames:
        ws = wb[name]
        clean_name = name.strip()
        try:
            parsed = _parse_sheet(ws)
            results.append({
                "sheet": clean_name,
                "ok": True,
                "year": parsed["year"],
                "month": parsed["month"],
                "rows": parsed["rows"],
                "keterangan": parsed["keterangan"],
                "details": parsed["details"],
            })
        except Exception as e:
            results.append({"sheet": clean_name, "ok": False, "error": str(e)})
    return results
