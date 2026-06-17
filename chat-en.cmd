@echo off
rem Interactive English console over the curriculum (translate / inflect / build clauses).
rem This is a deterministic generator, NOT the dialogue chat. Type ? for help.
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
".venv\Scripts\python.exe" -m casa.curriculum.demo_repl %*
exit /b %ERRORLEVEL%
