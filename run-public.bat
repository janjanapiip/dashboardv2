@echo off
REM ==== Mulai dashboard + tunnel publik dalam satu klik ====
REM Membuka dua jendela: satu untuk Flask, satu untuk Cloudflare Tunnel.

cd /d "%~dp0"

echo Memulai dashboard SPP Utilisasi (jendela terpisah)...
start "SPP Utilisasi - Dashboard" cmd /k call run.bat

echo Menunggu dashboard siap...
timeout /t 8 /nobreak >nul

echo Memulai Cloudflare Tunnel (jendela terpisah)...
start "SPP Utilisasi - Tunnel" cmd /k call tunnel.bat

echo.
echo Dua jendela telah dibuka:
echo   1. Dashboard lokal di http://localhost:5000
echo   2. Cloudflare Tunnel - URL publik akan muncul di jendela tunnel.
echo.
echo Tutup salah satu jendela untuk menghentikan komponennya.
pause
