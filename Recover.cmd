@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch.ps1" -Action recover
set "fnm_result=%errorlevel%"
pause
exit /b %fnm_result%
