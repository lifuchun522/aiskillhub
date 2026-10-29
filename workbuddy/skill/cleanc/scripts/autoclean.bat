@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem Scheduled cleanup: only files older than 24h under %LOCALAPPDATA%\Temp.
rem *.vhdx (WSL/Docker virtual disks) are never deleted.
rem Preview first:  python server.py clean --ids local-temp --min-age-hours 24

python server.py clean --ids local-temp --apply --yes --min-age-hours 24 >> "%~dp0logs\autoclean.log" 2>&1
echo [%date% %time%] autoclean exit=%errorlevel% >> "%~dp0logs\autoclean.log"
endlocal
