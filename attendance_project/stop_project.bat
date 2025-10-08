@echo off
echo Stopping Real-Time Attendance System...
:: Kill Redis server
taskkill /IM redis-server.exe /F >nul 2>&1
:: Kill Django/Daphne
taskkill /IM python.exe /F >nul 2>&1
echo All servers stopped.
pause