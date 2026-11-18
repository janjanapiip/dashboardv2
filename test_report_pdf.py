"""Self-check for the PDF report. Run: .venv/Scripts/python.exe test_report_pdf.py

Uses a temp copy of data/app.db; the live DB is never written.
"""
import shutil
import sqlite3
import tempfile
from pathlib import Path

import fitz

import report_pdf as R

assert R.num(1234.5, 1) == "1.234,5" and R.num(0) == "0" and R.pct(1, 3) == "33,3%" and R.pct(1, 0) == "0,0%"
assert (round(R.A4.width), round(R.A4.height)) == (595, 842)          # A4 = 210 x 297 mm
assert R.esc("<b>&") == "&lt;b&gt;&amp;"

tmp = Path(tempfile.mkdtemp(prefix="report_pdf_test_"))
try:
    import db, app as A
    shutil.copy(db.DB_PATH, tmp / "app.db")
    db.DB_PATH = tmp / "app.db"
    con = sqlite3.connect(db.DB_PATH)
    year, month = con.execute("SELECT year, month FROM entry WHERE drs > 0 ORDER BY year DESC, month DESC").fetchone()
    con.close()
    c = A.app.test_client()

    def pdf(url):
        r = c.get(url)
        assert r.status_code == 200 and r.mimetype == "application/pdf", (url, r.status_code)
        d = fitz.open("pdf", r.data)
        assert all((round(p.rect.width), round(p.rect.height)) == (595, 842) for p in d), "not A4"
        txt = [p.get_text().replace("\ufb01", "fi") for p in d]   # Story emits the fi ligature
        for i, t in enumerate(txt):
            assert f"Halaman {i + 1} dari {d.page_count}" in t
            for b in p_blocks(d[i]):                           # >= 12 mm margins, nothing in the footer zone
                assert b[0] >= 34 and b[2] <= 595 - 34 and b[3] <= 842 - 26, (url, i, b)
        last = d[-1]                                            # Kanit signature closes every report
        assert sum(R.KANIT_NIP in t for t in txt) == 1 and R.KANIT_NIP in txt[-1], url
        nm, nip = last.search_for("Diah Zakiah")[0], last.search_for("NIP. " + R.KANIT_NIP)[0]
        assert nm.y1 < (nip.y0 + nip.y1) / 2 and nip.y1 <= 842 - 26 and nm.x0 > 595 / 2, (url, nm, nip)
        body = [b for b in last.get_text("blocks") if 60 < b[1] < nm.y0 - 80 and "Mengetahui" not in b[4]]
        assert all(b[3] < nm.y0 for b in body), url              # sits below the last table
        return d, txt

    def p_blocks(page):
        return [b for b in page.get_text("blocks")]

    def order(txt, *marks):
        """Each mark appears, and on a page not earlier than the previous mark (charts before tables)."""
        last = 0
        for m in marks:
            pg = next((i for i, t in enumerate(txt) if m in t), None)
            assert pg is not None and pg >= last, (m, pg, last)
            last = pg

    # monthly: charts (pages 1-2) then tables, totals match the dashboard's own aggregator
    d, txt = pdf(f"/export/pdf?year={year}&month={month}")
    assert d.page_count >= 3
    order(txt, "Grafik 1", "Grafik 2", "Grafik 3", "Grafik 4", "Tabel 1", "Tabel 2", "Tabel 3")
    assert "Tabel" not in txt[0] + txt[1]
    labs, *_ = A.period_summary(year, month)
    labs = A._filter_retired(labs, year, month)
    total = R.num(sum(l["drs_total"] for l in labs), 1)
    assert total in txt[0] and total in "".join(txt[2:]), total

    # annual
    d, txt = pdf(f"/export/pdf/year?year={year}")
    order(txt, "Grafik 1", "Grafik 3", "Grafik 4", "Tabel 1", "Tabel 2", "Tabel 3")
    ylabs = A._filter_retired_year(A.year_summary(year), year)
    assert R.num(sum(l["drs_total"] for l in ylabs), 1) in txt[0]

    # signature is dated the last day of the reported period, whatever day it is printed
    for url, want in [("/export/pdf?year=2028&month=2", "29 Februari 2028"), ("/export/pdf?year=2027&month=2", "28 Februari 2027"),
                      ("/export/pdf?year=2026&month=9", "30 September 2026"), ("/export/pdf?year=2026&month=12", "31 Desember 2026"),
                      ("/export/pdf/year?year=2026", "31 Desember 2026")]:
        last = pdf(url)[1][-1]
        assert f"Jakarta, {want}" in last, (url, want)

    # empty period renders instead of crashing
    d, txt = pdf("/export/pdf?year=2099&month=2")
    assert "Tidak ada aktivitas" in "".join(txt)
    pdf("/export/pdf/year?year=2099")

    # no room left on the last page: block moves to a new page instead of hitting the footer
    import datetime
    doc = fitz.open(); doc.new_page(width=595, height=842)
    R._sign(doc, R.BODY.y1 - 20, datetime.date(2026, 10, 31))
    assert doc.page_count == 2 and R.KANIT_NIP in doc[1].get_text() and "31 Oktober 2026" in doc[1].get_text()

    for bad in ("/export/pdf", "/export/pdf?year=x&month=1", "/export/pdf?year=2026&month=13",
                "/export/pdf/year?year=1500"):
        assert c.get(bad).status_code == 400, bad

    # buttons sit beside "Unduh Excel"
    page = c.get(f"/?year={year}&month={month}").get_data(as_text=True)
    assert page.index("Unduh Excel") < page.index("Unduh PDF") < page.index("Unduh Excel") + 400
    assert "Unduh PDF Tahunan" in c.get(f"/year?year={year}").get_data(as_text=True)
    print("OK: report pdf self-check passed")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
