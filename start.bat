@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "main.py" --ui
    exit /b 0
) else if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe main.py --ui
) else (
    python main.py --ui
)
if errorlevel 1 (
    echo.
    echo  Boxy s est arrete. Verifiez votre .env et relancez.
    pause
)
