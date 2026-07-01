@echo off
REM ==== Build static snapshot and deploy to Vercel ====
REM Auth handling is automatic:
REM  - If .env has VERCEL_TOKEN, it's used directly (no browser needed).
REM  - Otherwise the saved `vercel login` session is used. If that session
REM    has expired, this script automatically launches `vercel login` so
REM    you can re-authenticate in one click before the deploy continues.

cd /d "%~dp0"

if not exist .venv (
  echo Virtual environment belum ada. Jalankan run.bat dulu untuk membuatnya.
  pause
  exit /b 1
)

call .venv\Scripts\activate

where vercel >nul 2>&1
if errorlevel 1 (
  echo Vercel CLI belum terinstall di PATH. Install dengan:
  echo   npm install -g vercel
  pause
  exit /b 1
)

python tools\deploy_dist.py
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo === Deploy selesai. URL publik ditampilkan di atas. ===
) else (
  echo === Deploy gagal ^(exit %RC%^). Lihat pesan error di atas. ===
)
pause
exit /b %RC%
