@echo off
rem Curated round-trip demo: a phrase -> language-independent concept graph -> phrase
rem (RU paraphrase + EN translation), ending with a refused category error.
rem Deterministic and auditable; not the dialogue chat.
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
".venv\Scripts\python.exe" -m casa.curriculum.demo_meaning %*
exit /b %ERRORLEVEL%
