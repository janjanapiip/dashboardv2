@echo off
REM ==== Dashboard Utilisasi SPP - Setup Diagnostic ====
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo ============================================================
echo  CEK KESIAPAN PC UNTUK Dashboard Utilisasi SPP
echo ============================================================
echo.

REM --- 1. Python ---
echo [1/6] Python interpreter:
set "PY_OK=0"
where py >nul 2>&1
if not errorlevel 1 (
  for /f "tokens=*" %%v in ('py -3 --version 2^>^&1') do echo     [OK] py launcher: %%v
  set "PY_OK=1"
)
where python >nul 2>&1
if not errorlevel 1 (
  for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo     [OK] python: %%v
  set "PY_OK=1"
)
if "!PY_OK!"=="0" (
  echo     [MISSING] Python tidak ada di PATH.
  echo               Install dari https://www.python.org/downloads/
)
echo.

REM --- 2. Virtual environment ---
echo [2/6] Virtual environment ^(.venv^):
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -c "import sys" >nul 2>&1
  if not errorlevel 1 (
    for /f "tokens=*" %%v in ('.venv\Scripts\python.exe --version 2^>^&1') do echo     [OK] %%v
  ) else (
    echo     [BROKEN] .venv ada tapi tidak bisa dijalankan ^(mungkin dipindah dari PC lain^).
    echo              Jalankan run.bat untuk membuat ulang otomatis.
  )
) else (
  echo     [MISSING] .venv belum dibuat. Jalankan run.bat untuk membuatnya.
)
echo.

REM --- 3. Python packages ---
echo [3/6] Python packages ^(requirements.txt^):
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -c "import flask, flask_login, openpyxl, PIL, werkzeug, dotenv; print('    [OK] semua dependency terinstall')" 2>nul
  if errorlevel 1 (
    echo     [MISSING] Sebagian / semua dependency belum terinstall.
    echo               Jalankan run.bat untuk install otomatis.
  )
) else (
  echo     [SKIP] .venv tidak ada.
)
echo.

REM --- 4. Database ---
echo [4/6] Database ^(data\app.db^):
if exist data\app.db (
  for %%F in (data\app.db) do echo     [OK] data\app.db ^(%%~zF bytes^)
) else (
  echo     [INFO] data\app.db belum ada — akan dibuat otomatis saat first run.
)
echo.

REM --- 5. Node.js + Vercel CLI (opsional, untuk deploy snapshot publik) ---
echo [5/6] Tools opsional untuk deploy Vercel:
where node >nul 2>&1
if not errorlevel 1 (
  for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo     [OK] Node.js %%v
  where vercel >nul 2>&1
  if not errorlevel 1 (
    for /f "tokens=*" %%v in ('vercel --version 2^>^&1') do echo     [OK] vercel CLI %%v
  ) else (
    echo     [MISSING] vercel CLI ^(opsional^) — install: npm install -g vercel
  )
) else (
  echo     [MISSING] Node.js ^(opsional^) — install: winget install OpenJS.NodeJS.LTS
)
echo.

REM --- 6. cloudflared (opsional, untuk tunnel publik) ---
echo [6/6] cloudflared ^(opsional, untuk akses publik via tunnel^):
where cloudflared >nul 2>&1
if not errorlevel 1 (
  for /f "tokens=*" %%v in ('cloudflared --version 2^>^&1') do echo     [OK] %%v
) else (
  echo     [MISSING] cloudflared ^(opsional^) — install: winget install --id Cloudflare.cloudflared
)
echo.

echo ============================================================
echo  Selesai. Jika ada [MISSING] pada item wajib ^(1-3^),
echo  jalankan run.bat — sebagian besar masalah otomatis diperbaiki.
echo ============================================================
pause
