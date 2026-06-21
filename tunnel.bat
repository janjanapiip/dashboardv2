@echo off
REM ==== Cloudflare quick tunnel for SPP Utilisasi dashboard ====
REM Run AFTER run.bat is already running (dashboard at http://localhost:5000).
REM Cetak URL publik di console; URL berubah setiap kali tunnel di-restart.

cd /d "%~dp0"

set "CFLARE=C:\Program Files (x86)\cloudflared\cloudflared.exe"
if not exist "%CFLARE%" set "CFLARE=C:\Program Files\cloudflared\cloudflared.exe"
if not exist "%CFLARE%" (
  echo cloudflared belum terinstall.
  echo Install dengan: winget install --id Cloudflare.cloudflared
  pause
  exit /b 1
)

echo === Memulai Cloudflare Tunnel ===
echo Dashboard publik akan tersedia di URL yang tercetak di bawah ini.
echo Tutup jendela ini untuk menghentikan tunnel.
echo.

"%CFLARE%" tunnel --url http://localhost:5000
