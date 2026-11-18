"""Monthly / annual utilisation report as PDF, drawn with PyMuPDF (already installed).

Page size measured with fitz.paper_rect("a4"): 595 x 842 pt = 210 x 297 mm (1 pt = 0.3528 mm).
Layout: chart pages first (vector charts + explanation), then table pages (fitz.Story,
flowing over as many pages as needed) each preceded by an explanation; the header band
and "Halaman i dari n" footer are stamped on every page at the end.
"""
import calendar
import datetime
import html as _html
import io
import math

import fitz

from labs import MONTHS_ID, MONTHS_SHORT_ID

A4 = fitz.paper_rect("a4")                    # Rect(0, 0, 595, 842)
MX, MT, MB = 42, 36, 40                       # margins ≈ 15 / 13 / 14 mm
HEADER_H = 44                                 # logo + title band
BODY = fitz.Rect(MX, MT + HEADER_H + 10, A4.width - MX, A4.height - MB - 8)  # 511 x 704 pt

PALETTE = ["#0b3d91", "#1f77b4", "#2ca02c", "#ff7f0e", "#d62728", "#9467bd", "#8c564b",
           "#e377c2", "#17becf", "#bcbd22", "#7f7f7f", "#aec7e8", "#ffbb78",
           "#98df8a", "#c5b0d5"]  # = dashboard.js + 2 so 14 labs never share a colour
NAVY, GRID, GREY, SHADE = (11/255, 61/255, 145/255), (.85, .87, .9), (.4, .4, .4), (.93, .93, .93)
# Signatory, as listed on templates/profile.html (Struktur Organisasi).
KANIT_NAME = "Diah Zakiah, S.T., M.T"
KANIT_NIP = "197905172006042015"
KANIT_TITLE = "Kepala Unit Sarana Praktek Pelaut"
SIG_H = 118  # height of the signature block (pt)

DAYS_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

CSS = """
body { font-family: sans-serif; font-size: 9.5pt; color: #222; }
h2 { font-size: 12.5pt; color: #0b3d91; margin: 0 0 4pt 0; }
h3 { font-size: 10pt; color: #0b3d91; margin: 0 0 3pt 0; }
p { margin: 0 0 5pt 0; text-align: justify; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt; margin-bottom: 6pt; }
th { background-color: #e8eef7; border: 0.5pt solid #9aa5b8; padding: 2pt 3pt; text-align: center; }
td { border: 0.5pt solid #9aa5b8; padding: 2pt 3pt; vertical-align: top; }
.r { text-align: right; } .c { text-align: center; }
.tot td { font-weight: bold; background-color: #f2f4f8; }
.we td { background-color: #efefef; color: #666; }
.note { font-size: 8pt; color: #555; }
"""


def esc(s):
    return _html.escape(str(s or ""))


def num(x, dec=0):
    """Indonesian number format: 1.234,5"""
    return f"{x:,.{dec}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def pct(part, total):
    return f"{num(part / total * 100, 1)}%" if total else "0,0%"


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


def _nice_step(vmax, n=5):
    if vmax <= 0:
        return 1
    raw = vmax / n
    mag = 10 ** math.floor(math.log10(raw))
    return next(m * mag for m in (1, 2, 5, 10) if raw <= m * mag)


def _tl(s, size, font="helv"):
    return fitz.get_text_length(s, fontname=font, fontsize=size)


def _box(page, y, h, html_s, x0=None, x1=None):
    """HTML text box at y; returns the y just below the text actually used."""
    spare, _ = page.insert_htmlbox(fitz.Rect(x0 or BODY.x0, y, x1 or BODY.x1, y + h), html_s, css=CSS)
    return y + (h - spare if spare >= 0 else h)


# ---------------- vector charts (ASCII labels only: base-14 font) ----------------

def hbar(page, y, rows, colors, fmt, row_h=17):
    """Horizontal bars. rows=[(label, value)]. Returns bottom y."""
    rect = fitz.Rect(BODY.x0, y, BODY.x1, y + row_h * max(len(rows), 1))
    x0, x1 = rect.x0 + 46, rect.x1 - 54
    vmax = max([v for _, v in rows] + [0])
    step = _nice_step(vmax)
    top = step * max(1, math.ceil(vmax * 1.12 / step))
    k = 0
    while k * step <= top + 1e-9:
        x = x0 + (x1 - x0) * k * step / top
        page.draw_line((x, rect.y0), (x, rect.y1), color=GRID, width=0.4)
        t = num(k * step, 0 if float(step).is_integer() else 1)
        page.insert_text((x - _tl(t, 6.5) / 2, rect.y1 + 9), t, fontsize=6.5, color=GREY)
        k += 1
    bh = min(row_h * 0.62, 12)
    for i, (label, v) in enumerate(rows):
        yc = rect.y0 + row_h * i + row_h / 2
        page.insert_text((rect.x0, yc + 3), label, fontsize=8, fontname="hebo")
        w = (x1 - x0) * v / top
        if w > 0:
            page.draw_rect(fitz.Rect(x0, yc - bh / 2, x0 + w, yc + bh / 2), color=None, fill=colors[i])
        page.insert_text((x0 + w + 3, yc + 3), fmt(v), fontsize=7.5)
    return rect.y1 + 14


def vstack(page, y, h, cats, series, shade=(), ylabel=""):
    """Stacked vertical bars. series=[(label, hexcolor, [values per cat])]. Returns bottom y."""
    plot = fitz.Rect(BODY.x0 + 34, y + 10, BODY.x1, y + h - 14)
    n = len(cats)
    totals = [sum(s[2][i] for s in series) for i in range(n)]
    vmax = max(totals + [0])
    step = _nice_step(vmax)
    top = step * max(1, math.ceil(vmax * 1.1 / step))
    cw = plot.width / n
    for i in shade:
        page.draw_rect(fitz.Rect(plot.x0 + cw * i, plot.y0, plot.x0 + cw * (i + 1), plot.y1), color=None, fill=SHADE)
    k = 0
    while k * step <= top + 1e-9:
        yy = plot.y1 - plot.height * k * step / top
        page.draw_line((plot.x0, yy), (plot.x1, yy), color=GRID, width=0.4)
        t = num(k * step, 0 if float(step).is_integer() else 1)
        page.insert_text((plot.x0 - 4 - _tl(t, 6.5), yy + 2.5), t, fontsize=6.5, color=GREY)
        k += 1
    if ylabel:
        page.insert_text((BODY.x0 + 7, plot.y1 - plot.height / 2 + _tl(ylabel, 7) / 2), ylabel,
                         fontsize=7, color=GREY, rotate=90)
    bw = cw * 0.7
    for i, c in enumerate(cats):
        x = plot.x0 + cw * i + (cw - bw) / 2
        yy = plot.y1
        for _, col, vals in series:
            v = vals[i]
            if v > 0:
                hh = plot.height * v / top
                page.draw_rect(fitz.Rect(x, yy - hh, x + bw, yy), color=(1, 1, 1), fill=hexrgb(col), width=0.3)
                yy -= hh
        if totals[i] > 0:
            t = num(totals[i], 0 if float(totals[i]).is_integer() else 1)
            fs = 6 if n > 15 else 7
            page.insert_text((x + bw / 2 - _tl(t, fs) / 2, yy - 2), t, fontsize=fs)
        lab = str(c)
        page.insert_text((x + bw / 2 - _tl(lab, 6.5) / 2, plot.y1 + 9), lab, fontsize=6.5)
    return plot.y1 + 14


def legend(page, y, items):
    x = BODY.x0
    for label, col in items:
        w = _tl(label, 7) + 18
        if x + w > BODY.x1:
            x, y = BODY.x0, y + 11
        page.draw_rect(fitz.Rect(x, y - 6, x + 7, y + 1), color=None, fill=hexrgb(col))
        page.insert_text((x + 10, y), label, fontsize=7)
        x += w
    return y + 12


def kpis(page, y, items):
    """Row of KPI boxes: items=[(label, value_text)]."""
    gap = 8
    w = (BODY.width - gap * (len(items) - 1)) / len(items)
    for i, (label, value) in enumerate(items):
        x = BODY.x0 + i * (w + gap)
        page.draw_rect(fitz.Rect(x, y, x + w, y + 42), color=GRID, fill=(.96, .97, .99), width=0.6)
        page.insert_text((x + 7, y + 13), label, fontsize=7, color=GREY)
        page.insert_text((x + 7, y + 33), value, fontsize=15, fontname="hebo", color=NAVY)
    return y + 52


# ---------------- document plumbing ----------------

def _page(doc):
    return doc.new_page(width=A4.width, height=A4.height)


def _flow(doc, sections):
    """Each HTML section starts on a new page and flows over as many pages as it needs."""
    # ponytail: table header row is not repeated on continuation pages (Story has no thead repeat).
    buf = io.BytesIO()
    writer = fitz.DocumentWriter(buf)
    for html_s in sections:
        story = fitz.Story(html=html_s, user_css=CSS)
        more = 1
        while more:
            dev = writer.begin_page(A4)
            more, filled = story.place(BODY)
            story.draw(dev)
            writer.end_page()
    writer.close()
    doc.insert_pdf(fitz.open("pdf", buf.getvalue()))
    return fitz.Rect(filled).y1  # bottom of the content on the last page


def _sign(doc, y, signed):
    """Kanit signature block dated `signed` (last day of the reported period), right-aligned under the last table; moves to a fresh page if it won't fit."""
    if y + 14 + SIG_H > BODY.y1:
        doc.new_page(width=A4.width, height=A4.height)
        y = BODY.y0 - 14
    page = doc[-1]
    box = fitz.Rect(A4.width - MX - 230, y + 14, A4.width - MX, y + 14 + SIG_H)
    page.insert_htmlbox(box, (
        f"<div style='text-align:center; font-family:sans-serif; font-size:9.5pt; color:#222'>"
        f"Jakarta, {signed.day} {MONTHS_ID[signed.month]} {signed.year}<br>Mengetahui,<br>{esc(KANIT_TITLE)}"
        f"<br><br><br><br><br><b><u>{esc(KANIT_NAME)}</u></b><br>NIP. {esc(KANIT_NIP)}</div>"))


def _finish(doc, subtitle, logo, printed):
    n = doc.page_count
    logo_xref = 0
    stamp = f"Dicetak {printed.day} {MONTHS_ID[printed.month]} {printed.year} - Unit Sarana Praktek Pelaut, STIP Jakarta"
    for i, page in enumerate(doc):
        if logo and logo.exists():
            r = fitz.Rect(MX, MT, MX + 48, MT + 38)
            logo_xref = page.insert_image(r, xref=logo_xref) if logo_xref else page.insert_image(r, filename=str(logo))
        page.insert_htmlbox(
            fitz.Rect(MX + 56, MT - 1, A4.width - MX, MT + HEADER_H - 2),
            "<div style='font-size:11.5pt;color:#0b3d91'><b>Rekapitulasi Utilisasi Sarana Praktek Pelaut</b></div>"
            "<div style='font-size:8.5pt'>Sekolah Tinggi Ilmu Pelayaran Jakarta</div>"
            f"<div style='font-size:8.5pt;color:#555'>{subtitle}</div>", css=CSS)
        page.draw_line((MX, MT + HEADER_H), (A4.width - MX, MT + HEADER_H), color=NAVY, width=1.2)
        fy = A4.height - MB
        page.draw_line((MX, fy), (A4.width - MX, fy), color=GRID, width=0.5)
        page.insert_text((MX, fy + 11), stamp, fontsize=7, color=GREY)
        t = f"Halaman {i + 1} dari {n}"
        page.insert_text((A4.width - MX - _tl(t, 7), fy + 11), t, fontsize=7, color=GREY)
    doc.set_metadata({"title": f"Rekapitulasi Utilisasi SPP - {subtitle}", "author": "Unit SPP STIP Jakarta",
                      "creator": "spp-utilisasi"})
    return doc.tobytes(garbage=3, deflate=True)


def _rank(labs, key, total, unit, what, dec):
    ranked = sorted((l for l in labs if l[key] > 0), key=lambda l: -l[key])
    if not ranked:
        return f"Belum ada {what} yang tercatat."
    a = ranked[0]
    s = f"{what[0].upper() + what[1:]} tertinggi tercatat di <b>{esc(a['name'])}</b> ({num(a[key], dec)} {unit}; {pct(a[key], total)} dari total)"
    if len(ranked) > 1:
        b = ranked[1]
        s += f", diikuti {esc(b['name'])} ({num(b[key], dec)} {unit}; {pct(b[key], total)})"
    if len(ranked) > 2:
        s += f". Tiga sarana teratas menyumbang {pct(sum(l[key] for l in ranked[:3]), total)} dari total"
    return s + "."


def _idle(labs, key="drs_total"):
    idle = [l["code"] for l in labs if not l[key]]
    return f" Sarana tanpa aktivitas: {', '.join(idle)}." if idle else ""


def _lab_table(labs, tot_fr, tot_jp, tot_drs, active_label, active_key, active_den):
    rows = "".join(
        f"<tr><td class='c'>{i}</td><td class='c'>{esc(l['code'])}{'*' if l.get('retired_from') else ''}</td>"
        f"<td>{esc(l['name'])}</td><td class='r'>{num(l['fr_total'])}</td><td class='r'>{num(l['jp_total'])}</td>"
        f"<td class='r'>{num(l['drs_total'], 1)}</td><td class='c'>{l[active_key]} / {active_den}</td>"
        f"<td class='r'>{pct(l['drs_total'], tot_drs)}</td></tr>"
        for i, l in enumerate(labs, 1))
    return (f"<table><tr><th>No</th><th>Kode</th><th>Nama Sarana</th><th>JF</th><th>JP</th>"
            f"<th>Durasi (jam)</th><th>{active_label}</th><th>Porsi Durasi</th></tr>{rows}"
            f"<tr class='tot'><td></td><td></td><td>TOTAL</td><td class='r'>{num(tot_fr)}</td>"
            f"<td class='r'>{num(tot_jp)}</td><td class='r'>{num(tot_drs, 1)}</td><td></td>"
            f"<td class='r'>{'100,0%' if tot_drs else '0,0%'}</td></tr></table>")


ABBREV = ("<p class='note'>JF = jumlah frekuensi (sesi/kelas praktikum); JP = jumlah pengguna (taruna/peserta, "
          "akumulasi harian); Durasi = total jam penggunaan sarana.</p>")


# ---------------- monthly ----------------

def monthly(year, month, labs, days, day_meta, details_map, photo_count, prev_drs, retired, logo, printed):
    period = f"{MONTHS_ID[month]} {year}"
    fr = sum(l["fr_total"] for l in labs)
    jp = sum(l["jp_total"] for l in labs)
    drs = sum(l["drs_total"] for l in labs)
    for l in labs:
        l["active_days"] = sum(1 for c in l["days"].values() if c["drs"] > 0 or c["fr"] > 0)
    n_active = sum(1 for l in labs if l["drs_total"] > 0 or l["fr_total"] > 0)
    colors = {l["id"]: PALETTE[i % len(PALETTE)] for i, l in enumerate(labs)}
    rng = range(1, days + 1)
    d_fr = [sum(l["days"][d]["fr"] for l in labs) for d in rng]
    d_jp = [sum(l["days"][d]["jlh"] for l in labs) for d in rng]
    d_drs = [sum(l["days"][d]["drs"] for l in labs) for d in rng]
    off = [d for d in rng if day_meta[d]["is_weekend"] or day_meta[d]["holiday"]]
    workdays = days - len(off)
    act_days = [d for d in rng if d_drs[d - 1] > 0 or d_fr[d - 1] > 0]
    act_off = [d for d in act_days if d in off]

    doc = fitz.open()
    # --- page 1: KPI + per-lab charts
    p = _page(doc)
    overview = (f"Pada {period} tercatat <b>{num(fr)}</b> sesi penggunaan (JF) dengan <b>{num(jp)}</b> pengguna (JP) "
                f"dan total durasi <b>{num(drs, 1)} jam</b> pada {n_active} dari {len(labs)} sarana yang beroperasi. "
                f"Dokumentasi kegiatan: {photo_count} foto.")
    if prev_drs:
        diff = (drs - prev_drs) / prev_drs * 100
        word = "naik" if diff > 0 else "turun" if diff < 0 else "sama dengan"
        pm = MONTHS_ID[month - 1 if month > 1 else 12]
        overview += (f" Dibanding {pm} ({num(prev_drs, 1)} jam), total durasi {word}"
                     f"{' ' + num(abs(diff), 1) + '%' if diff else ''}.")
    if retired:
        overview += " Sarana yang sudah tidak beroperasi dan tidak dihitung: " + ", ".join(esc(c) for c, _ in retired) + "."
    y = _box(p, BODY.y0, 110, f"<h2>Ringkasan Utilisasi {period}</h2><p>{overview}</p>")
    y = kpis(p, y + 2, [("Total Frekuensi (JF)", num(fr)), ("Total Pengguna (JP)", num(jp)),
                        ("Total Durasi (jam)", num(drs, 1)), ("Sarana Aktif", f"{n_active} / {len(labs)}")])
    by_drs = sorted(labs, key=lambda l: -l["drs_total"])
    y = _box(p, y, 20, "<h3>Grafik 1. Durasi Penggunaan per Sarana (jam)</h3>")
    y = hbar(p, y + 2, [(l["code"], l["drs_total"]) for l in by_drs], [hexrgb(colors[l["id"]]) for l in by_drs],
             lambda v: f"{num(v, 1)} jam", 21)
    y = _box(p, y, 60, f"<p>{_rank(labs, 'drs_total', drs, 'jam', 'durasi penggunaan', 1)}{_idle(labs)}</p>")
    by_jp = sorted(labs, key=lambda l: -l["jp_total"])
    y = _box(p, y + 4, 20, "<h3>Grafik 2. Distribusi Pengguna (JP) per Sarana</h3>")
    y = hbar(p, y + 2, [(l["code"], l["jp_total"]) for l in by_jp], [hexrgb(colors[l["id"]]) for l in by_jp],
             lambda v: f"{num(v)} ({pct(v, jp)})", 21)
    avg = f" Rata-rata {num(jp / fr, 1)} pengguna per sesi." if fr else ""
    _box(p, y, 60, f"<p>{_rank(labs, 'jp_total', jp, 'orang', 'jumlah pengguna', 0)}{avg}</p>")

    # --- page 2: daily charts
    p = _page(doc)
    y = _box(p, BODY.y0, 20, "<h3>Grafik 3. Durasi Harian per Sarana (jam)</h3>")
    shown = [l for l in labs if l["drs_total"] > 0]
    y = vstack(p, y, 270, list(rng), [(l["code"], colors[l["id"]], [l["days"][d]["drs"] for d in rng]) for l in shown],
               shade=[d - 1 for d in off], ylabel="Durasi (jam)")
    y = legend(p, y + 8, [(l["code"], colors[l["id"]]) for l in shown])
    if act_days:
        top_v = max(d_drs)
        when = ", ".join(f"{DAYS_ID[day_meta[d]['dow']]} {d}" for d in rng if d_drs[d - 1] == top_v)
        txt = (f"Aktivitas berlangsung pada <b>{len(act_days)} hari</b> dari {workdays} hari kerja "
               f"(Senin–Jumat di luar hari libur). Durasi harian tertinggi {num(top_v, 1)} jam pada "
               f"{when} {MONTHS_ID[month]}. "
               f"Rata-rata {num(drs / len(act_days), 1)} jam per hari aktif.")
        if act_off:
            txt += f" Sebanyak {len(act_off)} hari aktif jatuh pada akhir pekan/hari libur."
    else:
        txt = "Tidak ada aktivitas tercatat pada bulan ini."
    y = _box(p, y + 2, 70, f"<p>{txt} Kolom berlatar abu-abu menandai akhir pekan dan hari libur.</p>")
    y = _box(p, y + 6, 20, "<h3>Grafik 4. Jumlah Pengguna (JP) Harian</h3>")
    y = vstack(p, y, 200, list(rng), [("JP", PALETTE[0], d_jp)], shade=[d - 1 for d in off], ylabel="Pengguna")
    if any(d_jp):
        pk = max(rng, key=lambda d: d_jp[d - 1])
        _box(p, y + 2, 50, f"<p>Jumlah pengguna harian tertinggi terjadi pada tanggal {pk} {MONTHS_ID[month]} "
                           f"({num(d_jp[pk - 1])} pengguna dalam {num(d_fr[pk - 1])} sesi).</p>")

    # --- tables
    t1 = (f"<h3>Tabel 1. Rekapitulasi per Sarana — {period}</h3>"
          f"<p>Tabel berikut merangkum total frekuensi, pengguna, dan durasi tiap sarana selama {period}. "
          f"Hari aktif adalah jumlah hari dengan aktivitas tercatat; porsi durasi adalah persentase terhadap "
          f"total durasi bulan ini ({num(drs, 1)} jam).</p>"
          + _lab_table(labs, fr, jp, drs, "Hari Aktif", "active_days", days) + ABBREV)
    notes = [l for l in labs if (l.get("keterangan") or "").strip()]
    if notes:
        t1 += ("<h3>Keterangan per Sarana</h3><p>Catatan yang menyertai data master untuk periode ini.</p><table>"
               "<tr><th>Kode</th><th>Keterangan</th></tr>"
               + "".join(f"<tr><td class='c'>{esc(l['code'])}</td><td>{esc(l['keterangan']).replace(chr(10), '<br>')}</td></tr>"
                         for l in notes) + "</table>")
    t2_rows = ""
    for d in rng:
        m = day_meta[d]
        codes = ", ".join(l["code"] for l in labs if l["days"][d]["drs"] > 0 or l["days"][d]["fr"] > 0)
        ket = esc(m["holiday"]) if m["holiday"] else ("Akhir pekan" if m["is_weekend"] else "")
        cls = " class='we'" if d in off else ""
        t2_rows += (f"<tr{cls}><td class='c'>{d}</td><td>{DAYS_ID[m['dow']]}</td><td>{ket}</td>"
                    f"<td class='r'>{num(d_fr[d - 1]) if d_fr[d - 1] else ''}</td>"
                    f"<td class='r'>{num(d_jp[d - 1]) if d_jp[d - 1] else ''}</td>"
                    f"<td class='r'>{num(d_drs[d - 1], 1) if d_drs[d - 1] else ''}</td><td>{codes}</td></tr>")
    t2 = (f"<h3>Tabel 2. Rekapitulasi Harian — {period}</h3>"
          f"<p>Total harian seluruh sarana beserta kode sarana yang aktif. Baris abu-abu menandai akhir pekan "
          f"dan hari libur; sel kosong berarti tidak ada aktivitas.</p>"
          f"<table><tr><th>Tgl</th><th>Hari</th><th>Keterangan</th><th>JF</th><th>JP</th><th>Durasi (jam)</th>"
          f"<th>Sarana Aktif</th></tr>{t2_rows}<tr class='tot'><td></td><td></td><td>TOTAL</td>"
          f"<td class='r'>{num(fr)}</td><td class='r'>{num(jp)}</td><td class='r'>{num(drs, 1)}</td>"
          f"<td>{len(act_days)} hari aktif</td></tr></table>")
    code_of = {l["id"]: l["code"] for l in labs}
    det = [(d, code_of[lid], e) for lid, per_day in details_map.items() if lid in code_of
           for d, entries in per_day.items() for e in entries]
    det.sort(key=lambda t: (t[0], t[1]))
    if det:
        t3_body = ("<table><tr><th>Tgl</th><th>Sarana</th><th>Pengguna</th><th>Jabatan</th><th>Kegiatan</th></tr>"
                   + "".join(f"<tr><td class='c'>{d}</td><td class='c'>{esc(c)}</td><td>{esc(e['users'])}</td>"
                             f"<td>{esc(e['jabatan'])}</td><td>{esc(e['activity'])}</td></tr>" for d, c, e in det)
                   + "</table>")
    else:
        t3_body = "<p><i>Tidak ada rincian kegiatan yang tercatat untuk periode ini.</i></p>"
    t3 = (f"<h3>Tabel 3. Rincian Kegiatan — {period}</h3>"
          f"<p>Rincian kegiatan per hari sebagaimana tercatat pada data master (kelas/pengguna, jabatan, "
          f"dan isi kegiatan). Jumlah entri: {len(det)}.</p>" + t3_body)
    _sign(doc, _flow(doc, [t1, t2, t3]), datetime.date(year, month, calendar.monthrange(year, month)[1]))
    return _finish(doc, f"Laporan Bulanan · {period}", logo, printed)


# ---------------- annual ----------------

def annual(year, labs, retired, logo, printed):
    fr = sum(l["fr_total"] for l in labs)
    jp = sum(l["jp_total"] for l in labs)
    drs = sum(l["drs_total"] for l in labs)
    n_active = sum(1 for l in labs if l["drs_total"] > 0 or l["fr_total"] > 0)
    colors = {l["id"]: PALETTE[i % len(PALETTE)] for i, l in enumerate(labs)}
    ms = range(1, 13)
    m_fr = [sum(l["months"][m]["fr"] for l in labs) for m in ms]
    m_jp = [sum(l["months"][m]["jlh"] for l in labs) for m in ms]
    m_drs = [sum(l["months"][m]["drs"] for l in labs) for m in ms]
    m_ph = [sum(l["months"][m].get("photos", 0) for l in labs) for m in ms]
    data_m = [m for m in ms if m_drs[m - 1] > 0 or m_fr[m - 1] > 0]
    short = [MONTHS_SHORT_ID[m] for m in ms]

    doc = fitz.open()
    p = _page(doc)
    span = (f"{len(data_m)} bulan berdata ({MONTHS_ID[data_m[0]]}–{MONTHS_ID[data_m[-1]]})" if data_m
            else "belum ada bulan berdata")
    overview = (f"Sepanjang tahun {year} ({span}) tercatat <b>{num(fr)}</b> sesi penggunaan (JF), "
                f"<b>{num(jp)}</b> pengguna (JP), dan total durasi <b>{num(drs, 1)} jam</b> pada "
                f"{n_active} dari {len(labs)} sarana.")
    if retired:
        overview += (" Sarana bertanda * tidak beroperasi lagi sejak "
                     + "; ".join(f"{esc(r['code'])} ({MONTHS_ID[r['from_month']]} {r['from_year']})" for r in retired)
                     + " — data setelahnya dihitung nol.")
    y = _box(p, BODY.y0, 110, f"<h2>Ringkasan Utilisasi Tahun {year}</h2><p>{overview}</p>")
    y = kpis(p, y + 2, [("Total Frekuensi (JF)", num(fr)), ("Total Pengguna (JP)", num(jp)),
                        ("Total Durasi (jam)", num(drs, 1)), ("Sarana Aktif", f"{n_active} / {len(labs)}")])
    rh = 21 if len(labs) <= 10 else 16
    by_drs = sorted(labs, key=lambda l: -l["drs_total"])
    y = _box(p, y, 20, f"<h3>Grafik 1. Durasi Penggunaan per Sarana — Total {year} (jam)</h3>")
    y = hbar(p, y + 2, [(l["code"], l["drs_total"]) for l in by_drs], [hexrgb(colors[l["id"]]) for l in by_drs],
             lambda v: f"{num(v, 1)} jam", rh)
    y = _box(p, y, 60, f"<p>{_rank(labs, 'drs_total', drs, 'jam', 'durasi penggunaan', 1)}{_idle(labs)}</p>")
    by_jp = sorted(labs, key=lambda l: -l["jp_total"])
    y = _box(p, y + 4, 20, f"<h3>Grafik 2. Distribusi Pengguna (JP) per Sarana — {year}</h3>")
    y = hbar(p, y + 2, [(l["code"], l["jp_total"]) for l in by_jp], [hexrgb(colors[l["id"]]) for l in by_jp],
             lambda v: f"{num(v)} ({pct(v, jp)})", rh)
    avg = f" Rata-rata {num(jp / fr, 1)} pengguna per sesi." if fr else ""
    _box(p, y, 60, f"<p>{_rank(labs, 'jp_total', jp, 'orang', 'jumlah pengguna', 0)}{avg}</p>")

    p = _page(doc)
    y = _box(p, BODY.y0, 20, "<h3>Grafik 3. Durasi Bulanan per Sarana (jam)</h3>")
    shown = [l for l in labs if l["drs_total"] > 0]
    y = vstack(p, y, 280, short, [(l["code"], colors[l["id"]], [l["months"][m]["drs"] for m in ms]) for l in shown],
               ylabel="Durasi (jam)")
    y = legend(p, y + 8, [(l["code"], colors[l["id"]]) for l in shown])
    if data_m:
        hi = max(data_m, key=lambda m: m_drs[m - 1])
        lo = min(data_m, key=lambda m: m_drs[m - 1])
        txt = (f"Bulan dengan durasi tertinggi adalah <b>{MONTHS_ID[hi]}</b> ({num(m_drs[hi - 1], 1)} jam) dan "
               f"terendah {MONTHS_ID[lo]} ({num(m_drs[lo - 1], 1)} jam). Rata-rata {num(drs / len(data_m), 1)} jam "
               f"per bulan berdata.")
    else:
        txt = "Belum ada aktivitas tercatat pada tahun ini."
    y = _box(p, y + 2, 60, f"<p>{txt}</p>")
    y = _box(p, y + 6, 20, "<h3>Grafik 4. Jumlah Pengguna (JP) Bulanan</h3>")
    y = vstack(p, y, 200, short, [("JP", PALETTE[0], m_jp)], ylabel="Pengguna")
    if data_m:
        pk = max(data_m, key=lambda m: m_jp[m - 1])
        _box(p, y + 2, 50, f"<p>Jumlah pengguna tertinggi tercatat pada {MONTHS_ID[pk]} ({num(m_jp[pk - 1])} "
                           f"pengguna dalam {num(m_fr[pk - 1])} sesi).</p>")

    t1 = (f"<h3>Tabel 1. Rekapitulasi per Sarana — Tahun {year}</h3>"
          f"<p>Total tahunan tiap sarana. Bulan aktif adalah jumlah bulan dengan durasi tercatat; porsi durasi "
          f"adalah persentase terhadap total durasi tahun {year} ({num(drs, 1)} jam).</p>"
          + _lab_table(labs, fr, jp, drs, "Bulan Aktif", "active_months", 12) + ABBREV)
    t1 += ("<h3>Tabel 2. Rekapitulasi Bulanan</h3>"
           "<p>Total seluruh sarana per bulan. Kolom foto menghitung foto kegiatan yang sudah dikaitkan ke sarana.</p>"
           "<table><tr><th>Bulan</th><th>JF</th><th>JP</th><th>Durasi (jam)</th><th>Sarana Aktif</th>"
           "<th>Foto</th><th>Porsi Durasi</th></tr>"
           + "".join(f"<tr><td>{MONTHS_ID[m]}</td><td class='r'>{num(m_fr[m - 1])}</td><td class='r'>{num(m_jp[m - 1])}</td>"
                     f"<td class='r'>{num(m_drs[m - 1], 1)}</td>"
                     f"<td class='c'>{sum(1 for l in labs if l['months'][m]['drs'] > 0)}</td>"
                     f"<td class='c'>{m_ph[m - 1]}</td><td class='r'>{pct(m_drs[m - 1], drs)}</td></tr>" for m in ms)
           + f"<tr class='tot'><td>TOTAL</td><td class='r'>{num(fr)}</td><td class='r'>{num(jp)}</td>"
             f"<td class='r'>{num(drs, 1)}</td><td></td><td class='c'>{sum(m_ph)}</td><td></td></tr></table>")
    mrows = ""
    for i, l in enumerate(labs, 1):
        cells = ""
        for m in ms:
            c = l["months"][m]
            cells += f"<td class='{'c' if c.get('retired') else 'r'}'>{'—' if c.get('retired') else (num(c['drs']) if c['drs'] else '')}</td>"
        mrows += (f"<tr><td class='c'>{i}</td><td class='c'>{esc(l['code'])}</td>{cells}"
                  f"<td class='r'>{num(l['drs_total'], 1)}</td></tr>")
    t3 = (f"<h3>Tabel 3. Matriks Durasi Sarana × Bulan (jam) — {year}</h3>"
          "<p>Durasi tiap sarana per bulan. Sel kosong berarti tidak ada aktivitas; tanda — berarti sarana sudah "
          "tidak beroperasi pada bulan tersebut. Nama lengkap sarana lihat Tabel 1.</p>"
          "<table><tr><th>No</th><th>Kode</th>" + "".join(f"<th>{s}</th>" for s in short) + "<th>Total</th></tr>"
          + mrows + "<tr class='tot'><td></td><td>TOTAL</td>"
          + "".join(f"<td class='r'>{num(v) if v else ''}</td>" for v in m_drs)
          + f"<td class='r'>{num(drs, 1)}</td></tr></table>")
    _sign(doc, _flow(doc, [t1, t3]), datetime.date(year, 12, 31))
    return _finish(doc, f"Laporan Tahunan · {year}", logo, printed)
