@echo off
setlocal enabledelayedexpansion

:: Set credentials and config
set PGPASSWORD=sshhsshh
set BACKUP_DIR=C:\backups\postgres
set DB=attendance_db
set USER=attendance_user
set HOST=localhost
set PORT=5432

:: Get current hour (pad if needed)
set HH=%time:~0,2%
if "%HH:~0,1%"==" " set HH=0%HH:~1%

:: Determine backup date (yesterday or today)
if %HH% LSS 12 (
  powershell -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')" > tmp_date.txt
) else (
  powershell -Command "(Get-Date).ToString('yyyy-MM-dd')" > tmp_date.txt
)

set /p BACKUP_DATE=<tmp_date.txt
del tmp_date.txt

:: Define file names
set SQL_FILE=%BACKUP_DIR%\%DB%_%BACKUP_DATE%.sql
set DUMP_FILE=%BACKUP_DIR%\%DB%_%BACKUP_DATE%.dump

:: Create backup directory if not exists
mkdir "%BACKUP_DIR%" 2>nul

:: Plain SQL backup
echo Creating plain SQL backup...
"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" -U %USER% -h %HOST% -p %PORT% -F p %DB% > "%SQL_FILE%"

:: Custom-format dump backup
echo Creating custom-format dump backup...
"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" -U %USER% -h %HOST% -p %PORT% -F c -f "%DUMP_FILE%" %DB%

echo.
echo ✅ Backup completed:
echo - SQL File:   %SQL_FILE%
echo - Dump File:  %DUMP_FILE%
