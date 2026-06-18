@echo off
rem Validator demo: meaning-equivalence triage (✅ equivalent / ⚠️ divergent / ❓ uncheckable)
rem on source↔translation pairs. Deterministic, cross-lingual, auditable.
cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
".venv\Scripts\python.exe" -m casa.curriculum.demo_check %*
exit /b %ERRORLEVEL%
