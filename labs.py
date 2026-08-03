LABS = [
    (1,  "CHL",   "CARGO HANDLING LABORATORY (CHL)"),
    (2,  "EEL",   "ELECTRIC AND ELECTRONIC LABORATORY (EEL)"),
    (3,  "EWS",   "ENGINEERING WORKSHOP"),
    (4,  "MEL",   "MARINE ENGINEERING LABORATORY (MEL)"),
    (5,  "BRF",   "BRIEFING ROOM"),
    (6,  "LCHS",  "LIQUID CARGO HANDLING SIMULATOR (LCHS)"),
    (7,  "NAS",   "NAVIGATION AIDS SIMULATOR (NAS)"),
    (8,  "SOL",   "SHIP OPERATIONAL LABORATORY (SOL)"),
    (9,  "CBT",   "COMPUTER BASED TRAINING 1 & 2 (CBT)"),
    (10, "ERCS",  "ENGINE ROOM CERTIFICATION SIMULATOR (ERCS)"),
    (11, "ERGL",  "ENGINE ROOM GRAPHICS LABORATORY (ERGL)"),
    (12, "LTL",   "LANGUAGE TRAINING LABORATORY (LTL)"),
    (13, "ACSL",  "AUTOMATIC CONTROL SYSTEM LABORATORY (ACSL)"),
    (14, "LAI",   "LAIN-LAIN (ROOFTOP LANTAI 3, SELASAR, DLL)"),
]

# Sarana yang dinonaktifkan mulai periode tertentu. Format: code -> (year, month)
# Sebelum bulan ini lab tetap ditampilkan (data historis tetap utuh);
# mulai bulan ini ke atas lab disembunyikan dari tabel/grafik & ditandai
# "Tidak aktif" pada panel keterangan singkatan.
RETIRED_LABS = {
    "BRF":  (2026, 5),
    "LCHS": (2026, 5),
    "NAS":  (2026, 5),
    "SOL":  (2026, 5),
    "ERGL": (2026, 5),
}


def active_labs(year: int, month: int):
    """Return LABS list filtered to those still active in the given period."""
    out = []
    for lab in LABS:
        _, code, _ = lab
        retired = RETIRED_LABS.get(code)
        if retired and (year, month) >= retired:
            continue
        out.append(lab)
    return out


def retired_in_period(year: int, month: int):
    """Return [(code, name)] of labs that are inactive in the given period."""
    out = []
    for lab_id, code, name in LABS:
        retired = RETIRED_LABS.get(code)
        if retired and (year, month) >= retired:
            out.append((code, name))
    return out

# Penjelasan ringkas tiap laboratorium / simulator
LAB_DESCRIPTIONS = {
    "CHL":  "Laboratorium penanganan muatan kapal: pelatihan loading, lashing, dan stowage muatan curah maupun peti kemas.",
    "EEL":  "Laboratorium kelistrikan & elektronika kapal: praktik instalasi, troubleshooting, dan pengendalian sistem elektronik kapal.",
    "EWS":  "Bengkel teknik (Engineering Workshop): kerja bangku, pengelasan, pembubutan, dan fabrikasi komponen permesinan kapal.",
    "MEL":  "Laboratorium permesinan kapal: praktik perawatan dan pengoperasian mesin diesel kapal beserta sistem pendukungnya.",
    "BRF":  "Ruang briefing: pengarahan pra-praktikum, debriefing, dan diskusi hasil simulasi.",
    "LCHS": "Simulator penanganan muatan cair: pelatihan operasi kapal tanker (kargo cair / gas) berbasis simulator.",
    "NAS":  "Simulator alat bantu navigasi: pelatihan radar, ARPA, ECDIS, dan instrumen navigasi modern.",
    "SOL":  "Laboratorium operasi kapal: prosedur dinas jaga, manuver, dan dokumentasi operasional pelayaran.",
    "CBT":  "Computer Based Training 1 & 2: pembelajaran berbasis modul digital interaktif untuk taruna.",
    "ERCS": "Engine Room Certification Simulator: sertifikasi kompetensi ruang mesin sesuai standar STCW.",
    "ERGL": "Engine Room Graphics Laboratory: visualisasi sistem permesinan kapal berbasis grafis.",
    "LTL":  "Language Training Laboratory: pelatihan Maritime English untuk komunikasi pelayaran.",
    "ACSL": "Automatic Control System Laboratory: praktik sistem kontrol otomatis dan instrumentasi kapal.",
    "LAI":  "Lain-lain: penggunaan area di luar laboratorium formal (rooftop lantai 3, selasar, ruang lain).",
}

# Penjelasan singkatan kolom yang muncul di tabel / dashboard
ABBREV_HELP = [
    ("FR",  "Frekuensi (harian)",
     "Jumlah sesi / kelas praktikum yang diselenggarakan pada hari tersebut."),
    ("JLH", "Jumlah Pengguna (harian)",
     "Jumlah taruna / peserta yang menggunakan sarana pada hari tersebut."),
    ("DRS", "Durasi (jam, harian)",
     "Total durasi penggunaan sarana dalam jam pada hari tersebut."),
    ("JF",  "Jumlah Frekuensi (bulanan)",
     "Total akumulasi nilai FR selama satu bulan."),
    ("JP",  "Jumlah Pengguna (bulanan)",
     "Total akumulasi nilai JLH selama satu bulan."),
    ("WIB", "Waktu Indonesia Barat",
     "Zona waktu UTC+7 yang digunakan untuk jam dashboard."),
]

MONTHS_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember",
}
MONTHS_SHORT_ID = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "Mei", 6: "Jun", 7: "Jul", 8: "Agu",
    9: "Sep", 10: "Okt", 11: "Nov", 12: "Des",
}
MONTHS_LOOKUP = {v.lower(): k for k, v in MONTHS_ID.items()}
