@echo off
rem Unified showcase of the conceptual network: round-trip + questions + validator.
rem Deterministic, cross-lingual, auditable. One run for the team.
cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
".venv\Scripts\python.exe" -m casa.curriculum.showcase %*
exit /b %ERRORLEVEL%
