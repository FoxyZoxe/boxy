@echo off
setlocal EnableDelayedExpansion
title BOXY - Installateur
color 0B

set GITHUB_ZIP=https://github.com/FoxyZoxe/boxy/archive/refs/heads/main.zip
set INSTALL_DIR=%USERPROFILE%\Boxy
set DESKTOP=%USERPROFILE%\Desktop
set TMP_ZIP=%TEMP%\boxy_setup.zip
set TMP_DIR=%TEMP%\boxy_extract

cls
echo.
echo  ==========================================
echo    BOXY  --  Installateur automatique
echo  ==========================================
echo.
echo  Dossier : %INSTALL_DIR%
echo.

echo  [1/6] Verification de Python...
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERREUR] Python introuvable.
    echo  Telechargez Python 3.11+ sur https://www.python.org/downloads/
    echo  Cochez bien : Add Python to PATH
    echo.
    choice /c OQ /n /m "  Ouvrir python.org ? O=Oui Q=Quitter : "
    if !errorlevel! == 1 start https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo  [OK]   !PY_VER!
echo.

echo  [2/6] Telechargement depuis GitHub...
if exist "%TMP_ZIP%" del /q "%TMP_ZIP%" >nul 2>&1
if exist "%TMP_DIR%" rd /s /q "%TMP_DIR%" >nul 2>&1
echo  connexion internet requise...
echo.
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%GITHUB_ZIP%' -OutFile '%TMP_ZIP%' -UseBasicParsing"
if not exist "%TMP_ZIP%" (
    echo  [ERREUR] Telechargement echoue. Verifiez votre connexion.
    pause
    exit /b 1
)
echo  [OK]   Telechargement termine
echo.

echo  [3/6] Extraction des fichiers...
powershell -NoProfile -Command "Expand-Archive -Path '%TMP_ZIP%' -DestinationPath '%TMP_DIR%' -Force"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
for /d %%D in ("%TMP_DIR%\*") do xcopy /E /I /Y "%%D\*" "%INSTALL_DIR%\" >nul 2>&1
if not exist "%INSTALL_DIR%\main.py" (
    echo  [ERREUR] Fichiers introuvables apres extraction.
    pause
    exit /b 1
)
del /q "%TMP_ZIP%" >nul 2>&1
rd /s /q "%TMP_DIR%" >nul 2>&1
echo  [OK]   Fichiers copies dans %INSTALL_DIR%
echo.

echo  [4/6] Installation des dependances...
echo  patience 1 a 3 minutes...
echo.
cd /d "%INSTALL_DIR%"
python -m venv .venv >nul 2>&1
if exist ".venv\Scripts\pip.exe" (
    set PIP=%INSTALL_DIR%\.venv\Scripts\pip.exe
    echo  [OK]   Environnement virtuel cree
) else (
    set PIP=pip
    echo  [WARN] venv non dispo - installation globale
)
"%PIP%" install --upgrade pip -q 2>nul
"%PIP%" install -r "%INSTALL_DIR%\requirements.txt"
if errorlevel 1 (
    echo  [ERREUR] pip echoue.
    pause
    exit /b 1
)
echo  [OK]   Dependances installees
echo.

echo  [5/6] Configuration .env...
if exist "%INSTALL_DIR%\.env" (
    echo  [OK]   .env existant conserve
) else if exist "%INSTALL_DIR%\.env.example" (
    copy "%INSTALL_DIR%\.env.example" "%INSTALL_DIR%\.env" >nul
    echo  [OK]   .env cree depuis .env.example
) else (
    echo AI_PROVIDER=groq> "%INSTALL_DIR%\.env"
    echo GROQ_API_KEY=VOTRE_CLE_GROQ_ICI>> "%INSTALL_DIR%\.env"
    echo GROQ_MODEL=llama-3.3-70b-versatile>> "%INSTALL_DIR%\.env"
    echo ASSISTANT_NAME=Boxy>> "%INSTALL_DIR%\.env"
    echo USER_NAME=Monsieur>> "%INSTALL_DIR%\.env"
    echo VOICE_ENABLED=true>> "%INSTALL_DIR%\.env"
    echo TTS_VOICE=fr-FR-DeniseNeural>> "%INSTALL_DIR%\.env"
    echo WHISPER_MODEL=small>> "%INSTALL_DIR%\.env"
    echo STT_LANGUAGE=fr>> "%INSTALL_DIR%\.env"
    echo VOICE_MODE=wake_word>> "%INSTALL_DIR%\.env"
    echo THEME=cyan>> "%INSTALL_DIR%\.env"
    echo  [OK]   .env cree
)
echo.

echo  [6/6] Raccourci Bureau...
set LNK_TARGET=%INSTALL_DIR%\start.bat
set LNK_FILE=%DESKTOP%\Boxy.lnk
powershell -NoProfile -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut($env:LNK_FILE); $s.TargetPath=$env:LNK_TARGET; $s.WorkingDirectory=$env:INSTALL_DIR; $s.Description='Lancer Boxy'; $s.Save()"
if exist "%DESKTOP%\Boxy.lnk" (
    echo  [OK]   Raccourci Boxy cree sur le Bureau
) else (
    echo  [WARN] Raccourci non cree - lancez start.bat dans %INSTALL_DIR%
)
echo.

echo  ==========================================
echo    Installation terminee !
echo  ==========================================
echo.
echo  Ouvrez .env dans %INSTALL_DIR%
echo  et entrez votre cle Groq (gratuit sur console.groq.com)
echo.
choice /c LDQ /n /m "  L=Lancer  D=Dossier  Q=Quitter : "
if !errorlevel! == 1 start "" "%INSTALL_DIR%\start.bat"
if !errorlevel! == 2 start "" explorer "%INSTALL_DIR%"
exit /b 0
