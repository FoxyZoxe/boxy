@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
title BOXY - Installateur
color 0B

:: ══════════════════════════════════════════════════════════════════
::  BOXY Bootstrapper
::  Ce fichier telecharge, installe et configure Boxy en entier.
::  Il suffit de le double-cliquer. Rien d'autre a faire.
:: ══════════════════════════════════════════════════════════════════

set "GITHUB_ZIP=https://github.com/FoxyZoxe/boxy/archive/refs/heads/main.zip"
set "INSTALL_DIR=%USERPROFILE%\Boxy"
set "DESKTOP=%USERPROFILE%\Desktop"
set "TMP_ZIP=%TEMP%\boxy_setup.zip"
set "TMP_DIR=%TEMP%\boxy_extract"

cls
echo.
echo  ==========================================
echo    BOXY  --  Installation automatique
echo  ==========================================
echo.
echo  Dossier d'installation : %INSTALL_DIR%
echo.


:: ══════════════════════════════════════════
:: ETAPE 1 - Verifier Python
:: ══════════════════════════════════════════
echo  [1/6]  Verification de Python...

where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERREUR] Python est introuvable sur ce PC.
    echo.
    echo  Vous devez installer Python 3.11 ou superieur.
    echo  Lien : https://www.python.org/downloads/
    echo.
    echo  IMPORTANT : cochez "Add Python to PATH" pendant l'installation,
    echo  puis relancez ce fichier install.bat.
    echo.
    choice /c OQ /n /m "  Ouvrir python.org maintenant ? (O=Oui  Q=Quitter) : "
    if !errorlevel! == 1 start https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo  [OK]   !PY_VER!
echo.


:: ══════════════════════════════════════════
:: ETAPE 2 - Telecharger Boxy depuis GitHub
:: ══════════════════════════════════════════
echo  [2/6]  Telechargement de Boxy depuis GitHub...
echo  (necessite une connexion internet)
echo.

:: Nettoie les fichiers temporaires precedents
if exist "%TMP_ZIP%"   del /q "%TMP_ZIP%"   >nul 2>&1
if exist "%TMP_DIR%"   rd  /s /q "%TMP_DIR%" >nul 2>&1

powershell -NoProfile -Command ^
  "try { Invoke-WebRequest -Uri '%GITHUB_ZIP%' -OutFile '%TMP_ZIP%' -UseBasicParsing; Write-Host 'OK' } catch { Write-Host ('ERREUR: ' + $_.Exception.Message) }"

if not exist "%TMP_ZIP%" (
    echo.
    echo  [ERREUR] Telechargement echoue.
    echo  Verifiez votre connexion internet et relancez.
    echo.
    pause
    exit /b 1
)

echo  [OK]   Telechargement termine
echo.


:: ══════════════════════════════════════════
:: ETAPE 3 - Extraire et installer les fichiers
:: ══════════════════════════════════════════
echo  [3/6]  Extraction des fichiers...

powershell -NoProfile -Command ^
  "Expand-Archive -Path '%TMP_ZIP%' -DestinationPath '%TMP_DIR%' -Force"

if errorlevel 1 (
    echo.
    echo  [ERREUR] Extraction echouee.
    echo.
    pause
    exit /b 1
)

:: Cree le dossier d'installation
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Copie les fichiers depuis boxy-main vers INSTALL_DIR
xcopy /E /I /Y "%TMP_DIR%\boxy-main\*" "%INSTALL_DIR%\" >nul 2>&1
if errorlevel 1 (
    :: Essai avec le nom de dossier alternatif GitHub peut generer
    for /d %%D in ("%TMP_DIR%\*") do (
        xcopy /E /I /Y "%%D\*" "%INSTALL_DIR%\" >nul 2>&1
    )
)

:: Verifie que main.py est bien la
if not exist "%INSTALL_DIR%\main.py" (
    echo.
    echo  [ERREUR] Fichiers Boxy introuvables apres extraction.
    echo  Contenu extrait dans : %TMP_DIR%
    echo.
    pause
    exit /b 1
)

:: Nettoie les temporaires
del /q "%TMP_ZIP%"      >nul 2>&1
rd  /s /q "%TMP_DIR%"   >nul 2>&1

echo  [OK]   Fichiers installes dans : %INSTALL_DIR%
echo.


:: ══════════════════════════════════════════
:: ETAPE 4 - Environnement virtuel + pip
:: ══════════════════════════════════════════
echo  [4/6]  Installation des dependances...
echo  (patience, 1 a 3 minutes selon votre connexion)
echo.

cd /d "%INSTALL_DIR%"

python -m venv .venv >nul 2>&1
if exist ".venv\Scripts\pip.exe" (
    set "PIP=%INSTALL_DIR%\.venv\Scripts\pip.exe"
    set "PYTHON=%INSTALL_DIR%\.venv\Scripts\python.exe"
    echo  [OK]   Environnement virtuel cree
) else (
    set "PIP=pip"
    set "PYTHON=python"
    echo  [WARN] Environnement virtuel non disponible - installation globale
)

"%PIP%" install --upgrade pip -q 2>nul
"%PIP%" install -r "%INSTALL_DIR%\requirements.txt"

if errorlevel 1 (
    echo.
    echo  [ERREUR] Installation des dependances echouee.
    echo  Verifiez votre connexion internet et relancez.
    echo.
    pause
    exit /b 1
)

echo.
echo  [OK]   Dependances installees
echo.


:: ══════════════════════════════════════════
:: ETAPE 5 - Fichier de configuration .env
:: ══════════════════════════════════════════
echo  [5/6]  Configuration...

if exist "%INSTALL_DIR%\.env" (
    echo  [OK]   .env existant conserve
) else (
    if exist "%INSTALL_DIR%\.env.example" (
        copy "%INSTALL_DIR%\.env.example" "%INSTALL_DIR%\.env" >nul
        echo  [OK]   .env cree depuis .env.example
    ) else (
        (
            echo AI_PROVIDER=groq
            echo GROQ_API_KEY=VOTRE_CLE_GROQ_ICI
            echo GROQ_MODEL=llama-3.3-70b-versatile
            echo OLLAMA_BASE_URL=http://localhost:11434
            echo OLLAMA_MODEL=mistral:latest
            echo OPENAI_API_KEY=
            echo OPENAI_MODEL=gpt-4o-mini
            echo ASSISTANT_NAME=Boxy
            echo USER_NAME=Monsieur
            echo MAX_HISTORY_LENGTH=6
            echo VOICE_ENABLED=true
            echo TTS_VOICE=fr-FR-DeniseNeural
            echo WHISPER_MODEL=small
            echo STT_LANGUAGE=fr
            echo VOICE_MODE=wake_word
            echo PTT_KEY=space
            echo WAKE_WORD_MODEL=hey_jarvis
            echo GLOBAL_HOTKEY=ctrl+space
            echo AI_TIMEOUT=120
            echo THEME=cyan
            echo IMAGE_PROVIDER=pollinations
            echo DISCORD_TOKEN=
            echo DISCORD_CHANNEL=boxy
            echo OBS_HOST=localhost
            echo OBS_PORT=4455
            echo OBS_PASSWORD=
            echo HF_HUB_DISABLE_SYMLINKS_WARNING=1
        ) > "%INSTALL_DIR%\.env"
        echo  [OK]   .env cree avec valeurs par defaut
    )
    echo.
    echo  RAPPEL : ouvrez .env dans %INSTALL_DIR%
    echo  et entrez votre cle API Groq (gratuit sur console.groq.com)
)
echo.


:: ══════════════════════════════════════════
:: ETAPE 6 - Raccourci sur le Bureau
:: ══════════════════════════════════════════
echo  [6/6]  Creation du raccourci Bureau...

:: Cree start.bat dans le dossier d'installation
(
    echo @echo off
    echo cd /d "%%~dp0"
    echo if exist ".venv\Scripts\python.exe" ^(
    echo     .venv\Scripts\python.exe main.py
    echo ^) else ^(
    echo     python main.py
    echo ^)
    echo if errorlevel 1 ^(
    echo     echo.
    echo     echo  Boxy s'est arrete - verifiez votre .env
    echo     pause
    echo ^)
) > "%INSTALL_DIR%\start.bat"

:: Cree le raccourci via variables d'environnement pour eviter les bugs d'expansion
set "LNK_TARGET=%INSTALL_DIR%\start.bat"
set "LNK_FILE=%DESKTOP%\Boxy.lnk"

powershell -NoProfile -Command ^
  "$ws=New-Object -ComObject WScript.Shell;" ^
  "$s=$ws.CreateShortcut($env:LNK_FILE);" ^
  "$s.TargetPath=$env:LNK_TARGET;" ^
  "$s.WorkingDirectory=$env:INSTALL_DIR;" ^
  "$s.Description='Lancer Boxy';" ^
  "$s.Save()" >nul 2>&1

if exist "%DESKTOP%\Boxy.lnk" (
    echo  [OK]   Raccourci "Boxy" cree sur le Bureau
) else (
    echo  [WARN] Raccourci non cree - lancez start.bat manuellement
    echo         depuis : %INSTALL_DIR%
)
echo.


:: ══════════════════════════════════════════
:: TERMINE
:: ══════════════════════════════════════════
echo  ==========================================
echo    Boxy est installe et pret !
echo  ==========================================
echo.
echo  Dossier : %INSTALL_DIR%
echo.
echo  Prochaines etapes :
echo.
echo    1. Ouvrez le fichier .env dans le dossier Boxy
echo       et entrez votre cle API Groq
echo       (gratuit sur https://console.groq.com)
echo.
echo    2. Double-cliquez sur "Boxy" sur votre Bureau
echo.
echo  ==========================================
echo.

choice /c LDQ /n /m "  L=Lancer Boxy  D=Ouvrir le dossier  Q=Quitter : "
if !errorlevel! == 1 start "" "%INSTALL_DIR%\start.bat"
if !errorlevel! == 2 start "" explorer "%INSTALL_DIR%"

exit /b 0
