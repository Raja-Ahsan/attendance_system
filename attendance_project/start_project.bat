@echo off

REM Kill any process on port 6379
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :6379') do (
    taskkill /PID %%a /F
)

REM Start Redis server (adjust path if necessary)
start "" "C:\Redis\redis-server.exe"

REM Wait 5 seconds for Redis to start
timeout /t 5 /nobreak

REM Activate virtual environment (adjust the path to your env Scripts folder)
call C:\Users\home\PycharmProjects\PythonProject1\env\Scripts\activate.bat

REM Change directory to your project folder
cd C:\Users\home\PycharmProjects\PythonProject1\attendance_project

REM Run Daphne
daphne -b 0.0.0.0 -p 8000 attendance_project.asgi:application

pause
