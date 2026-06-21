@echo off
REM ==== Watcher: auto-deploy snapshot ke Vercel setiap kali data lokal berubah ====
REM Biarkan jendela ini terbuka selama Anda mengedit data lokal.
REM Setiap 60 detik tanpa perubahan, snapshot di-deploy ke Vercel otomatis.
REM
REM Argumen opsional: --quiet <detik>   (default 60)
REM Contoh: auto_deploy.bat --quiet 30

cd /d "%~dp0"

if not exist .venv (
  echo Virtual environment belum ada. Jalankan run.bat dulu.
  pause
  exit /b 1
)

call .venv\Scripts\activate
python tools\auto_deploy_watcher.py %*
pause
