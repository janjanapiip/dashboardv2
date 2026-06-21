@echo off
REM ==== Dashboard Utilisasi SPP - Local launcher ====
cd /d "%~dp0"

REM Create venv on first run
if not exist .venv (
  echo Membuat virtual environment...
  python -m venv .venv
  call .venv\Scripts\activate
  echo Menginstall dependencies...
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate
)

echo.
echo === Menjalankan Dashboard Utilisasi SPP ===
echo Buka di browser: http://localhost:5000
echo Tekan CTRL+C untuk menghentikan server.
echo.

start "" http://localhost:5000
python app.py
pause
