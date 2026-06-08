@echo off
rem One-click launcher for the von-neumann console chat (Windows).
rem Double-click this file, or run:  chat.cmd [--agency] [--verbose] [--store <id>]
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [chat] .venv not found. Create it first:
  echo     py -3.12 -m venv .venv
  echo     .venv\Scripts\python -m pip install -r tools\requirements.txt
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m casa.cli chat --store von-neumann %*
echo.
pause
