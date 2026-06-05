@echo off
title LaborAid Dev
cd /d "%~dp0"

echo.
echo ========================================
echo   LaborAid - local dev startup
echo ========================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev.ps1"

echo.
echo ----------------------------------------
echo Keep the Backend and Frontend windows open.
echo User:  http://127.0.0.1:5320
echo Admin: http://127.0.0.1:5320/login?portal=admin  (Admin / 123456)
echo Stop:  close those windows, or run stop-laboraid.bat
echo ----------------------------------------
pause
