"""Categorize JULI usage into 3 buckets (D4 / Upgrading / Short Course, UKP, Kerjasama)
and write the recap into the KETERANGAN column (col CU) per lab.

Rules (order matters — first match wins):
  1) UKP/Kerjasama : activity contains 'UKP' (case-insensitive)
  2) Upgrading     : jabatan contains 'Pasis'
  3) D4            : jabatan contains 'Taruna' OR users look like a STIP prodi class
                     (regex: 'Teknik', 'Tek ', 'Nautika', 'Naut ', 'TN-', 'ANT ' + prodi class,
                     'TL ', 'TM ', 'KALK')

Per-cell hours = DRS value in the DATA row (same column) for that day.
Per-lab recap = 3 lines in KETERANGAN cell. Zero-buckets are skipped.
"""
import re
from calendar import monthrange
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

MASTER = Path(__file__).resolve().parents[1] / "master" / "REKAP UTILISASI SPP v3 tabel Mei-Des.xlsx"
SHEET_NAME = "JULI"
YEAR, MONTH = 2026, 7

# Categorize
def categorize(users: str, jabatan: str, activity: str) -> str | None:
    a = (activity or "").lower()
    j = (jabatan or "").lower()
    u = (users or "").lower()
    if "ukp" in a:
        return "UKP"
    if "pasis" in j:
        return "UPGRADING"
    if "taruna" in j:
        return "D4"
    # user-based D4 detection
    if re.search(r"\bteknik\b|\btek\s|\bnautika\b|\bnaut\s|\btn[-\s]|\btl\s|\btm\s|\bkalk", u):
        return "D4"
    return None

def parse_kegiatan(text: str):
    """Return (users, jabatan, activity) from a Kegiatan cell (semicolon or fallback)."""
    if not text:
        return "", "", ""
    s = str(text).strip()
    if ";" in s:
        parts = [p.strip() for p in s.split(";", 2)]
        while len(parts) < 3:
            parts.append("")
        return parts[0], parts[1], parts[2]
    if ":" in s:
        u, a = s.split(":", 1)
        return u.strip(), "", a.strip()
    return "", "", s

def num(v):
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

def fmt_hours(h: float) -> str:
    """Format hours: drop trailing .0 for whole numbers."""
    if abs(h - round(h)) < 0.01:
        return f"{int(round(h))}"
    return f"{h:.1f}".rstrip("0").rstrip(".")

def main():
    wb = load_workbook(MASTER)
    ws = wb[SHEET_NAME]
    days = monthrange(YEAR, MONTH)[1]
    ket_col = 6 + days * 3  # 99 → CU

    # Walk lab pairs (data_row, keg_row) = (12,13), (14,15), ..., (28,29)
    grand = {"D4": 0.0, "UPGRADING": 0.0, "UKP": 0.0}
    unmatched_samples: list[str] = []
    per_lab_totals = []

    for data_row in range(12, 30, 2):
        keg_row = data_row + 1
        lab_name = ws.cell(row=data_row, column=2).value or f"row{data_row}"
        # marker "Kegiatan" in col B of keg_row confirms this is a lab pair
        if str(ws.cell(row=keg_row, column=2).value or "").strip().lower() != "kegiatan":
            continue

        buckets = {"D4": 0.0, "UPGRADING": 0.0, "UKP": 0.0}
        for d in range(1, days + 1):
            base_col = 6 + (d - 1) * 3  # F=6 -> day 1 (FR)
            drs_col = base_col + 2      # DRS
            keg_text = ws.cell(row=keg_row, column=base_col).value
            if not keg_text or not str(keg_text).strip():
                continue
            u, j, a = parse_kegiatan(keg_text)
            cat = categorize(u, j, a)
            drs = num(ws.cell(row=data_row, column=drs_col).value)
            if cat:
                buckets[cat] += drs
                grand[cat] += drs
            else:
                unmatched_samples.append(f"    day {d} col {get_column_letter(base_col)}: {keg_text!r}")

        per_lab_totals.append((lab_name, buckets))

        # Write recap into KETERANGAN cell for this lab
        lines = ["Rekap kategori penggunaan (jam):"]
        if buckets["D4"] > 0:
            lines.append(f"  • D4                       : {fmt_hours(buckets['D4'])} jam")
        if buckets["UPGRADING"] > 0:
            lines.append(f"  • Upgrading                : {fmt_hours(buckets['UPGRADING'])} jam")
        if buckets["UKP"] > 0:
            lines.append(f"  • Short Course, UKP, Kerjasama : {fmt_hours(buckets['UKP'])} jam")
        total = sum(buckets.values())
        if total > 0:
            lines.append(f"  Total                        : {fmt_hours(total)} jam")
            recap = "\n".join(lines)
            cell = ws.cell(row=data_row, column=ket_col)
            cell.value = recap
            cell.alignment = Alignment(wrap_text=True, vertical="top", horizontal="left")

    # Ensure KETERANGAN column is wide enough
    ws.column_dimensions[get_column_letter(ket_col)].width = max(
        ws.column_dimensions[get_column_letter(ket_col)].width or 0, 42
    )

    wb.save(MASTER)

    # Print report
    print(f"=== {SHEET_NAME} categorization ===\n")
    for lab_name, b in per_lab_totals:
        if sum(b.values()) == 0:
            continue
        print(f"{lab_name}")
        print(f"  D4        : {fmt_hours(b['D4'])} jam")
        print(f"  Upgrading : {fmt_hours(b['UPGRADING'])} jam")
        print(f"  UKP/KS    : {fmt_hours(b['UKP'])} jam")
    print("\n--- GRAND TOTAL ---")
    print(f"  D4                       : {fmt_hours(grand['D4'])} jam")
    print(f"  Upgrading                : {fmt_hours(grand['UPGRADING'])} jam")
    print(f"  Short Course, UKP, KS    : {fmt_hours(grand['UKP'])} jam")
    print(f"  TOTAL                    : {fmt_hours(sum(grand.values()))} jam")

    if unmatched_samples:
        print(f"\n⚠️  {len(unmatched_samples)} kegiatan tidak masuk kategori manapun:")
        for line in unmatched_samples[:20]:
            print(line)

if __name__ == "__main__":
    main()
