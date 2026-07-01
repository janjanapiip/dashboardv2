@echo off
REM ==== Dashboard Utilisasi SPP - Local launcher ====
cd /d "%~dp0"

REM --- Detect available Python ---
set "PY_CMD="
where py >nul 2>&1
if not errorlevel 1 (
  set "PY_CMD=py -3"
) else (
  where python >nul 2>&1
  if not errorlevel 1 (
    set "PY_CMD=python"
  )
)

if "%PY_CMD%"=="" (
  echo [ERROR] Python tidak ditemukan di PATH.
  echo Install Python 3.10+ dari https://www.python.org/downloads/
  echo Pastikan centang "Add Python to PATH" saat install.
  pause
  exit /b 1
)

REM --- Check if existing .venv is valid AND has flask installed ---
set "VENV_OK=0"
if exist .venv\Scripts\python.exe (
  REM Verify venv interpreter works AND flask is importable (real readiness check)
  .venv\Scripts\python.exe -c "import flask, flask_login, openpyxl, PIL, werkzeug, dotenv" >nul 2>&1
  if not errorlevel 1 set "VENV_OK=1"
)

if "%VENV_OK%"=="0" (
  if exist .venv (
    echo [INFO] Virtual environment lama rusak / belum lengkap. Membuat ulang...
    rmdir /s /q .venv
    if exist .venv (
      echo [ERROR] Tidak bisa hapus .venv. Tutup semua jendela yang sedang pakai folder ini lalu coba lagi.
      pause
      exit /b 1
    )
  ) else (
    echo Membuat virtual environment...
  )
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Gagal membuat virtual environment.
    pause
    exit /b 1
  )
  call .venv\Scripts\activate.bat
  echo Mengupgrade pip...
  python -m pip install --upgrade pip
  echo Menginstall dependencies dari requirements.txt...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] Gagal install dependencies. Cek koneksi internet lalu jalankan ulang.
    pause
    exit /b 1
  )
  REM Final sanity check
  python -c "import flask, flask_login, openpyxl, PIL, werkzeug, dotenv" >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Setelah install, modul tetap tidak bisa di-import. Jalankan setup_check.bat untuk diagnosa.
    pause
    exit /b 1
  )
  echo [OK] Semua dependency terinstall.
) else (
  call .venv\Scripts\activate.bat
)

echo.
echo === Menjalankan Dashboard Utilisasi SPP ===
echo Buka di browser: http://localhost:5000
echo Tekan CTRL+C untuk menghentikan server.
echo.

start "" http://localhost:5000
python app.py
pause
