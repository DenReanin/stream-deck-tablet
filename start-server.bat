@echo off
REM Arranque rapido del Stream Deck server.
cd /d "%~dp0"
".venv\Scripts\python.exe" -m server.main
pause
