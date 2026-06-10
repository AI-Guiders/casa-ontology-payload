@echo off
cd /d "%~dp0"
where pwsh >nul 2>&1 && (set "PSH=pwsh") || (set "PSH=powershell")
"%PSH%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0chat.ps1" %*
exit /b %ERRORLEVEL%
