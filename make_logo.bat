@echo off
REM ==== Konversi logo STIP menjadi PNG transparan untuk navbar ====
cd /d "%~dp0"

if not exist .venv (
  echo Virtual environment belum ada. Jalankan run.bat dulu untuk membuatnya.
  pause
  exit /b 1
)

call .venv\Scripts\activate
python tools\make_logo.py %1
pause
