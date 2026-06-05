@echo off
title LaborAid Stop
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop.ps1"
pause
