@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe main.py
) else (
    python main.py
)
if errorlevel 1 (
    echo.
    echo  Boxy s est arrete. Verifiez votre .env et relancez.
    pause
)
