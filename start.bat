@echo off
chcp 65001 >nul 2>&1
title BOXY
cd /d "%~dp0"

:: Lance Boxy avec le venv s'il existe, sinon Python global
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe main.py
) else (
  python main.py
)

:: Si Boxy quitte avec une erreur, garde la fenêtre ouverte
if errorlevel 1 (
  echo.
  echo  [ERREUR] Boxy s'est arrêté anormalement.
  echo  Vérifiez votre .env et relancez.
  pause
)
