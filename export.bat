@echo off
REM ==== Hanya menghasilkan snapshot statis tanpa deploy ====
cd /d "%~dp0"

if not exist .venv (
  echo Virtual environment belum ada. Jalankan run.bat dulu.
  pause
  exit /b 1
)

call .venv\Scripts\activate
python tools\static_export.py
echo.
echo Snapshot tersedia di folder dist\. Buka dist\index.html di browser untuk pratinjau,
echo atau jalankan: python -m http.server 8765 di folder dist\ untuk test server lokal.
pause
