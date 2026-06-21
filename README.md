# Dashboard Utilisasi SPP — Versi Lokal

Versi sederhana dari `dashboard-utilisasi-spp` yang dirombak menjadi aplikasi
**Flask + SQLite** yang berjalan sepenuhnya di PC lokal. Tidak butuh Node.js,
tidak butuh build step, dan database disimpan dalam satu file (`data/app.db`).

## Fitur

- **Jam &amp; tanggal langsung** di bagian atas (zona WIB), termasuk badge
  "Hari Libur" jika hari ini adalah hari libur nasional / cuti bersama.
- **Kalender hari libur Indonesia** disinkronkan dari Google Calendar
  (`id.indonesian#holiday`) — termasuk cuti bersama dan hari raya keagamaan,
  dengan fallback ke `date.nager.at` jika feed Google tidak tersedia.
  Tanggal libur ditandai merah pada tabel; akhir pekan ditandai abu-abu.
- **Halaman publik** (read-only): KPI ringkasan, grafik durasi per lab (bar),
  distribusi pengguna (donut), durasi harian (line stacked), tabel rincian
  13 laboratorium.
- **Mode tahunan** — menu "Rekap Tahunan" menampilkan 12 bulan sekaligus:
  KPI tahunan, bar durasi per lab, stacked bar bulanan, line tren per lab,
  dan tabel 13 lab &times; 12 bulan. Klik sel bulan untuk masuk ke detail bulanan.
- **Hover sel = preview foto** — sel yang memiliki foto kegiatan menampilkan
  thumbnail melayang saat di-hover (ditandai ikon kamera kecil).
- **Klik sel = zoom detail** — klik sel aktivitas untuk membuka modal dengan
  ringkasan FR/JLH/DRS, keterangan, dan foto kegiatan ukuran besar. Klik foto
  untuk membuka tampilan layar penuh (lightbox) dengan tombol navigasi.
- **Panel keterangan singkatan** — daftar penjelasan kolom (FR, JLH, DRS,
  JF, JP) dan deskripsi tiap laboratorium / simulator. Hover nama lab di tabel
  untuk tooltip penjelasan singkat.
- **Import Excel otomatis** dari format _Master Format Tabel Utilisasy.xlsx_
  (deteksi bulan/tahun otomatis dari header, parsing 13 lab × 30/31 hari ×
  FR/JLH/DRS; toleran terhadap typo nama lab via fuzzy matching).
- **Input manual** dengan auto-save (klik sel, isi angka, tekan Tab).
- **Upload foto kegiatan** — hanya menerima foto pada tanggal yang sudah memiliki
  catatan aktivitas (FR/JLH/DRS > 0) untuk lab terkait. Pilih opsi "Umum / tidak
  spesifik" untuk foto yang tidak terikat ke lab tertentu.
- **Export Excel** kembali ke format Master.
- **Admin login**; viewer/guest bisa lihat semua tanpa login.
- **Lokal di disk** — bisa dijalankan offline, data tidak dikirim ke cloud.
  Setelah hari libur disinkronkan sekali, dashboard tetap menampilkan tanggal
  merah meski tanpa internet.

## Setup

### Cara cepat (Windows)
Klik dua kali `run.bat`. Saat pertama kali dijalankan ia akan membuat virtual
environment dan menginstall dependensi, lalu membuka browser otomatis di
`http://localhost:5000`.

### Manual
```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Login default

- Username: `admin`
- Password: `admin`

Segera ganti password dari menu **Admin → Akun**.

Ingin pakai password awal yang berbeda? Set environment variable sebelum start:
```cmd
set SPP_ADMIN_PW=password-rahasia-anda
python app.py
```

## Mengunci agar hanya PC ini yang bisa akses

Defaultnya server bind ke `0.0.0.0:5000`, artinya siapa pun di jaringan lokal
yang sama dapat membuka dashboard (read-only). Untuk mengunci ke PC ini saja:
```cmd
python app.py --host 127.0.0.1
```
Atau set environment variable:
```cmd
set SPP_HOST=127.0.0.1
```

## Membuka akses publik (view-only) gratis

Dashboard sudah punya **guard otomatis**: semua endpoint yang menulis data
(login admin, simpan entri, upload foto, import Excel, hapus periode, restore
backup) hanya menerima request dari IP jaringan lokal (`127.0.0.0/8`,
`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, dst.). Request dari luar
yang masuk via tunnel publik tetap bisa melihat dashboard tetapi otomatis
ditolak dengan HTTP 403 ketika mencoba edit. Header `CF-Connecting-IP` dan
`X-Forwarded-For` dihormati supaya guard tidak salah baca IP.

### Rekomendasi: Cloudflare Tunnel (gratis, tanpa port forwarding)

**Cara cepat (sudah disiapkan):**

1. Klik dua kali `run-public.bat`. Script akan membuka dua jendela:
   - Jendela 1 menjalankan dashboard lokal di `http://localhost:5000`.
   - Jendela 2 menjalankan `cloudflared` dan mencetak URL publik
     `https://<random-words>.trycloudflare.com`.
2. Salin URL itu dan bagikan ke siapa pun yang ingin lihat dashboard.
3. Tutup salah satu jendela untuk menghentikan komponennya.

Atau jalankan satu-satu:
- `run.bat` &rarr; dashboard lokal.
- `tunnel.bat` &rarr; tunnel publik (perlu dashboard sudah running).

**Setup pertama kali** (sekali saja): install cloudflared via
`winget install --id Cloudflare.cloudflared`.

**URL berubah tiap restart.** Mode quick tunnel mendapatkan subdomain
`*.trycloudflare.com` baru setiap kali `cloudflared` dimulai. Untuk URL
permanen dengan subdomain Anda sendiri, daftar akun Cloudflare gratis dan
ikuti panduan
[Named Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-remote-tunnel/).

**Keamanan:** guard LAN tetap aktif &mdash; pengunjung dari URL publik
hanya dapat melihat dashboard dan men-download Excel. Login admin, upload
foto, import Excel, dan operasi destruktif lainnya otomatis ditolak 403
karena IP asal tidak ada di range LAN. Header `CF-Connecting-IP` dan
`X-Forwarded-For` dihormati supaya guard tidak salah baca IP.
Bila yakin ingin mengizinkan edit dari publik (tidak disarankan), set
`SPP_ALLOW_PUBLIC_WRITES=1` sebelum start app.

### Alternatif

- **Tailscale Funnel** &mdash; gratis untuk pemakaian pribadi; setup mirip
  cloudflared.
- **ngrok** &mdash; tier gratis cukup untuk demo singkat tetapi URL berganti
  dan ada batas request per menit.

## Deploy snapshot publik ke Vercel (gratis, URL permanen)

Vercel free hanya menjalankan fungsi serverless tanpa filesystem permanen,
sehingga **tidak dapat menjalankan aplikasi Flask + SQLite ini langsung**.
Solusi yang tepat untuk Vercel: **ekspor snapshot statis** dari PC Anda
(yang tetap menyimpan database), lalu publikasikan HTML hasil ekspor ke
Vercel sebagai situs hanya-baca dengan URL `*.vercel.app` permanen.

Keunggulan:
- URL permanen (mis. `spp-utilisasi.vercel.app`) yang tidak berubah.
- PC sumber tidak perlu menyala &mdash; Vercel meng-cache snapshot di edge global.
- Login, edit, upload tetap hanya di PC sumber &mdash; data tidak meninggalkan
  PC sebagai layanan, hanya hasil render-nya.

Trade-off: data di Vercel adalah snapshot, bukan real-time. Jalankan
ulang `deploy_vercel.bat` setiap kali ingin update.

### Setup sekali

1. Install Node.js LTS: `winget install OpenJS.NodeJS.LTS`.
2. Install Vercel CLI: `npm install -g vercel`.
3. Login: `vercel login` (akan membuka browser; gunakan email/GitHub gratis).

### Setiap kali ingin update snapshot publik

Tiga cara, dari yang paling manual ke yang otomatis:

**Manual** &mdash; klik dua kali `deploy_vercel.bat`. Script akan:
1. Menjalankan `tools/static_export.py` &mdash; merender semua halaman ke
   `dist/` dengan mode tampilan publik (admin/login disembunyikan,
   tombol periode jadi dropdown navigasi).
2. Menjalankan `vercel --prod` di folder `dist/`.
3. Mencetak URL publik di akhir.

**Auto-deploy saat data berubah** &mdash; klik dua kali `auto_deploy.bat`.
Watcher memantau `data/app.db` dan folder foto. Setelah 60 detik tanpa
perubahan, dia menjalankan export + deploy otomatis. Biarkan jendela ini
terbuka selama Anda mengedit. Berhenti dengan Ctrl+C.

- Tweak interval: `auto_deploy.bat --quiet 30` (deploy 30 dtk setelah berhenti).
- Sekali jalan: `python tools/auto_deploy_watcher.py --once` (satu siklus, langsung keluar).

**Catatan:** untuk update benar-benar real-time tanpa delay, pakai
**Cloudflare Tunnel** (lihat bagian sebelumnya). Vercel sifatnya snapshot
&mdash; arsitekturnya memang tidak mendukung push otomatis dari database
lokal tanpa interaksi watcher seperti di atas.

Cek snapshot sebelum deploy: jalankan `export.bat`, lalu di folder `dist/`
jalankan `python -m http.server 8765` dan buka `http://localhost:8765`.

### Yang ada di snapshot

- `index.html` &mdash; dashboard bulan terkini
- `<YYYY>-<MM>.html` &mdash; satu file per bulan dengan data
- `year-<YYYY>.html` &mdash; rekap tahunan
- `gallery.html` &mdash; galeri foto kegiatan
- `api/period-<YYYY>-<MM>.json` &mdash; data JSON untuk hover preview cell
- `export/Rekap_Utilisasi_<YYYY>-<MM>.xlsx` &mdash; tombol Unduh Excel
- `static/`, `uploads/photos/` &mdash; aset + foto
- `vercel.json` &mdash; rewrite supaya `/year`, `/year/2026`, `/gallery`
  bekerja sebagai URL bersih.

### Catatan plan Hobby

Vercel free (Hobby) ditujukan untuk pemakaian non-komersial. Penggunaan
oleh lembaga pendidikan umumnya diterima &mdash; periksa
[ketentuan Vercel](https://vercel.com/legal/terms) jika ragu.

## Penyimpanan data

```
data/
  app.db                      # database SQLite (semua data)
  uploads/photos/             # foto kegiatan
  backups/                    # snapshot otomatis sebelum operasi destruktif
```

Backup = copy folder `data/` ke flash disk atau cloud drive.

## Proteksi data

Data tidak hilang tanpa konfirmasi eksplisit dari admin:

- **Mode aman default** untuk import Excel &mdash; data yang sudah ada tidak
  ditimpa. Untuk benar-benar menimpa, centang "Timpa data" *dan* ketik
  `OVERWRITE` pada kolom konfirmasi.
- **Auto-backup** snapshot SQLite (`data/backups/app_<timestamp>_<reason>.db`)
  dibuat sebelum setiap import, hapus periode, dan restore. 30 snapshot terakhir
  disimpan; yang lama dirotasi.
- **Mengosongkan sel di tabel admin** akan menampilkan dialog konfirmasi
  (sisi browser) dan ditolak server (HTTP 409) jika konfirmasi tidak disertakan.
  Nilai semula dikembalikan otomatis jika admin membatalkan.
- **Hapus periode** memerlukan admin mengetik persis frasa
  `HAPUS <BULAN> <TAHUN>` (mis. `HAPUS FEBRUARI 2026`).
- **Pulihkan backup** dari menu Admin &raquo; Backup &mdash; ketik `PULIHKAN`
  untuk konfirmasi. Database saat ini juga disnapshot dulu sebelum diganti.

## Mengganti logo navbar

1. Simpan file logo Anda (PNG/JPG, background apa saja) di:
   `data/uploads/_logo_source.png`
2. Klik dua kali `make_logo.bat` (atau jalankan `python tools/make_logo.py`).
3. Script akan membuat versi transparan di `static/img/stip-logo.png`,
   meresize ke tinggi maks 192 px.
4. Refresh browser &mdash; logo otomatis muncul di kiri atas. Selama file
   tersebut belum ada, navbar memakai simbol jangkar bawaan.

Untuk pakai sumber lain: `python tools/make_logo.py path/ke/logo.jpg`.

## Batas unggah

| Berkas | Format diterima | Maks |
|---|---|---|
| Foto kegiatan | `.png`, `.jpg`, `.jpeg`, `.webp` | 2 MB / foto |
| Master Format Excel | `.xlsx`, `.xlsm` | 25 MB |

Pengecekan dilakukan di dua sisi: browser memberi peringatan instan,
server memvalidasi ulang (ekstensi + ukuran + header file gambar via Pillow)
agar berkas non-gambar yang dipalsukan tetap ditolak.

## Format Excel yang didukung

File _Master Format Tabel Utilisasy.xlsx_:
- Bulan & tahun dibaca dari header (baris 6–8 yang berisi `BULAN : <Bulan> <Tahun>`).
- Nama lab dideteksi dari kolom B baris 12–24 (13 laboratorium).
- Tiap hari memakai 3 kolom: **FR** (frekuensi), **JLH** (jumlah pengguna),
  **DRS** (durasi jam), dimulai dari kolom F.
- Kolom **KETERANGAN** ada di kolom terakhir.

Saat import, centang **"Timpa data periode tersebut"** untuk mengganti data
bulan tsb sepenuhnya, atau biarkan tidak dicentang untuk merge.

## Tech stack (singkat)

| Lapisan      | Pilihan                          |
|--------------|----------------------------------|
| Backend      | Flask 3, Flask-Login             |
| Database     | SQLite (file lokal)              |
| Parsing xlsx | openpyxl                         |
| Frontend     | Bootstrap 5 + Chart.js (CDN)     |
| Build        | tidak ada                        |
