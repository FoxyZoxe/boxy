@echo off
cd /d "%~dp0"
if exist "Boxy-Setup.bat" (
    call "Boxy-Setup.bat"
) else (
    echo Boxy-Setup.bat est introuvable.
    echo Re-telechargez le projet complet depuis GitHub.
    pause
    exit /b 1
)
