@echo off
rem Curated round-trip demo: a phrase -> language-independent concept graph -> phrase
rem (RU paraphrase + EN translation), ending with a refused category error.
rem Deterministic and auditable; not the dialogue chat.
cd /d "%~dp0"
rem switch the console to UTF-8 so the box-drawing / Cyrillic render (and never crash)
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
".venv\Scripts\python.exe" -m casa.curriculum.demo_meaning %*
exit /b %ERRORLEVEL%
