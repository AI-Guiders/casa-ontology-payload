@echo off
rem Reasoning demo: deterministic consistency checking over the concept graph —
rem contradiction / entailment / equivalence / independence, plus a SET-level
rem consistency scan. Cross-lingual, auditable, no hallucination.
cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
".venv\Scripts\python.exe" -m casa.curriculum.demo_reason %*
exit /b %ERRORLEVEL%
