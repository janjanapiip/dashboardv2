@echo off
REM ==== Build static snapshot and deploy to Vercel ====
REM Pertama kali: jalankan "vercel login" dari PowerShell untuk autentikasi.

cd /d "%~dp0"

if not exist .venv (
  echo Virtual environment belum ada. Jalankan run.bat dulu untuk membuatnya.
  pause
  exit /b 1
)

echo === 1. Membuat snapshot statis ke dist\ ===
call .venv\Scripts\activate
python tools\static_export.py
if errorlevel 1 (
  echo.
  echo Export gagal. Periksa pesan error di atas.
  pause
  exit /b 1
)

echo.
echo === 2. Mengecek Vercel CLI ===
where vercel >nul 2>&1
if errorlevel 1 (
  echo Vercel CLI belum terinstall di PATH. Install dengan:
  echo   npm install -g vercel
  pause
  exit /b 1
)

echo.
echo === 3. Deploy ke Vercel (production) ===
echo.
echo Jika ini deployment pertama, ikuti prompt:
echo  - Set up and deploy? Y
echo  - Which scope?  ^(pilih akun Anda^)
echo  - Link to existing project? N
echo  - Project name? spp-utilisasi  ^(atau nama lain^)
echo  - In which directory is your code? ./
echo  - Modify settings? N
echo.
cd dist
vercel --prod --yes
cd ..

echo.
echo === Selesai. URL publik ditampilkan di atas. ===
pause
