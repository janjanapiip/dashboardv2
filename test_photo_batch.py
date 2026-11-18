"""Self-check for batch photo import. Run: .venv/Scripts/python.exe test_photo_batch.py

Runs the real routes against a temp copy of data/app.db; never touches live photos.
"""
import io
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import date
from pathlib import Path

from PIL import Image
from werkzeug.security import generate_password_hash

import photo_batch as pb

# ---- pure helpers ----
assert pb.parse_wa_datetime("WhatsApp Image 2026-06-08 at 14.05.02 (1).jpeg") == (date(2026, 6, 8), "14:05")
assert pb.parse_wa_datetime("Juni/WhatsApp Image 2026-06-10 at 9.29.41.jpeg") == (date(2026, 6, 10), "09:29")
assert pb.parse_wa_datetime("IMG-20260608-WA0012.jpg") == (date(2026, 6, 8), "")
assert pb.parse_wa_datetime("WhatsApp Image 2026-02-30 at 10.00.00.jpeg") == (None, "")
assert pb.parse_wa_datetime("DSC0001.jpg") == (None, "")
assert pb.staging_dir(Path("."), "../../etc") is None


def jpeg(color, size=(40, 30)):
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, "JPEG")
    return b.getvalue()


tmp = Path(tempfile.mkdtemp(prefix="photo_batch_test_"))
try:
    import db, backup as backup_mod, app as A
    shutil.copy(db.DB_PATH, tmp / "app.db")
    db.DB_PATH = backup_mod.DB_PATH = tmp / "app.db"
    backup_mod.BACKUP_DIR = tmp / "backups"
    A.UPLOAD_DIR = tmp / "photos"; A.UPLOAD_DIR.mkdir()
    A.BATCH_STAGING_DIR = tmp / "staging"
    os.environ.pop("SPP_ALLOW_PUBLIC_WRITES", None)

    conn = sqlite3.connect(db.DB_PATH)
    conn.execute("INSERT INTO admin_user (username, pw_hash) VALUES ('t_batch', ?)",
                 (generate_password_hash("throwaway"),))
    conn.execute("INSERT INTO admin_user (username, pw_hash) VALUES ('t_batch2', ?)",
                 (generate_password_hash("throwaway"),))
    # Pick a single-lab day and a multi-lab day from the real data.
    days = conn.execute(
        "SELECT year, month, day, group_concat(lab_id) FROM entry WHERE fr>0 OR jlh>0 OR drs>0 "
        "GROUP BY year, month, day").fetchall()
    conn.commit(); conn.close()
    one = next(d for d in days if "," not in d[3])
    multi = next(d for d in days if "," in d[3])
    d1, dm = date(*one[:3]).isoformat(), date(*multi[:3]).isoformat()
    lab_one, lab_multi = int(one[3]), [int(x) for x in multi[3].split(",")]

    c = A.app.test_client()
    assert c.post("/login", data={"username": "t_batch", "password": "throwaway"}).status_code == 302

    red, blue, green = jpeg("red"), jpeg("blue"), jpeg("green")
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as z:
        z.writestr(f"../../evil/WhatsApp Image {d1} at 10.00.00.jpeg", red)        # traversal name
        z.writestr(f"Juni/WhatsApp Image {d1} at 10.00.00 (1).jpeg", red)           # dup in batch
        z.writestr(f"WhatsApp Image {dm} at 11.27.41.jpeg", blue)                   # multi-lab
        z.writestr("WhatsApp Image 2026-05-26 at 08.00.00.jpeg", green)             # no activity
        z.writestr("fake.jpg", b"not an image")
        z.writestr("big.jpg", b"\xff" * (A.MAX_IMAGE_BYTES + 1))
        z.writestr("__MACOSX/._x.jpg", b"junk")
        z.writestr("notes.txt", b"hi")
        z.writestr("IMG-20991231-WA0001.jpg", jpeg("white"))                        # future date
    zbuf.seek(0)
    r = c.post("/admin/photo/batch", data={"files": [(zbuf, "fotos.zip")]},
               content_type="multipart/form-data")
    assert r.status_code == 302 and "/admin/photo/batch/" in r.location, r.location
    token = r.location.rstrip("/").rsplit("/", 1)[-1]
    assert not any(A.UPLOAD_DIR.iterdir()), "nothing may be saved before commit"
    assert not (tmp / "evil").exists() and not (tmp.parent / "evil").exists()

    import json
    items = json.loads((A.BATCH_STAGING_DIR / token / "manifest.json").read_text("utf-8"))["items"]
    by = {i["name"]: i for i in items}
    a = by[f"WhatsApp Image {d1} at 10.00.00.jpeg"]
    assert a["status"] == "auto" and a["lab_id"] == lab_one and not a["error"]
    assert "Duplikat" in by[f"WhatsApp Image {d1} at 10.00.00 (1).jpeg"]["error"]
    m = by[f"WhatsApp Image {dm} at 11.27.41.jpeg"]
    assert m["status"] == "ambiguous" and m["lab_id"] is None and len(m["candidates"]) >= 2
    assert by["WhatsApp Image 2026-05-26 at 08.00.00.jpeg"]["status"] in ("no_activity", "auto")
    assert by["fake.jpg"]["error"] and by["big.jpg"]["error"] == pb.TOO_BIG
    assert "masa depan" in by["IMG-20991231-WA0001.jpg"]["error"]
    assert "notes.txt" not in by and "._x.jpg" not in by

    page = c.get(f"/admin/photo/batch/{token}").get_data(as_text=True)
    assert "Tinjau Batch Foto" in page and "Duplikat" in page
    assert c.get(f"/admin/photo/batch/{token}/img/{a['idx']}").status_code == 200
    # Another admin account cannot see or commit this batch.
    c2 = A.app.test_client()
    assert c2.post("/login", data={"username": "t_batch2", "password": "throwaway"}).status_code == 302
    assert c2.get(f"/admin/photo/batch/{token}").status_code == 404

    # Lab not active that day must be refused and nothing saved.
    bad_lab = next(x for x in range(1, 30) if x not in lab_multi + [lab_one])
    form = {f"include_{a['idx']}": "1", f"date_{a['idx']}": d1, f"lab_{a['idx']}": str(bad_lab)}
    r = c.post(f"/admin/photo/batch/{token}/commit", data=form)
    assert r.status_code == 302 and not any(A.UPLOAD_DIR.iterdir())

    # Good commit: auto one keeps its lab, ambiguous one admin-picked, no-activity -> Umum.
    g = by["WhatsApp Image 2026-05-26 at 08.00.00.jpeg"]
    form = {f"include_{a['idx']}": "1", f"date_{a['idx']}": d1, f"lab_{a['idx']}": str(lab_one),
            f"include_{m['idx']}": "1", f"date_{m['idx']}": dm, f"lab_{m['idx']}": str(lab_multi[1]),
            f"include_{g['idx']}": "1", f"date_{g['idx']}": "2026-05-26", f"lab_{g['idx']}": ""}
    r = c.post(f"/admin/photo/batch/{token}/commit", data=form)
    assert r.status_code == 302 and r.location.endswith("/gallery"), r.location
    assert len(list(A.UPLOAD_DIR.iterdir())) == 3
    assert not (A.BATCH_STAGING_DIR / token).exists(), "staging cleared after commit"
    conn = sqlite3.connect(db.DB_PATH)
    rows = conn.execute("SELECT event_date, lab_id FROM photo ORDER BY id DESC LIMIT 3").fetchall()
    conn.close()
    assert sorted(rows, key=str) == sorted([(d1, lab_one), (dm, lab_multi[1]), ("2026-05-26", None)], key=str), rows
    assert any((tmp / "backups").iterdir()), "DB backed up before commit"

    # Re-uploading the same photo is caught as already-in-gallery.
    r = c.post("/admin/photo/batch", data={"files": [(io.BytesIO(red), f"WhatsApp Image {d1} at 10.00.00.jpeg")]},
               content_type="multipart/form-data")
    t2 = r.location.rsplit("/", 1)[-1]
    it2 = json.loads((A.BATCH_STAGING_DIR / t2 / "manifest.json").read_text("utf-8"))["items"][0]
    assert "Sudah ada" in it2["error"]
    assert c.post(f"/admin/photo/batch/{t2}/cancel").status_code == 302
    assert not (A.BATCH_STAGING_DIR / t2).exists()
    assert c.get("/admin/photo/batch/0123456789abcdef").status_code == 404
    assert "Umum" in c.get("/gallery").get_data(as_text=True)
    print("OK: photo batch self-check passed")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
