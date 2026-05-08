@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Boxy - Installation
color 0B

set "APP_NAME=Boxy"
set "REPO_ZIP=https://github.com/FoxyZoxe/boxy/archive/refs/heads/main.zip"
set "INSTALL_DIR=%LOCALAPPDATA%\Boxy"
set "DESKTOP=%USERPROFILE%\Desktop"
set "TMP_ZIP=%TEMP%\boxy_setup.zip"
set "TMP_DIR=%TEMP%\boxy_setup"

cls
echo.
echo  ==========================================
echo    %APP_NAME% - Installation en quelques clics
echo  ==========================================
echo.
echo  Installation dans :
echo  %INSTALL_DIR%
echo.

choice /c OQ /n /m "  Installer maintenant ? O=Oui Q=Quitter : "
if errorlevel 2 exit /b 0

echo.
echo  [1/7] Recherche d'un Python compatible...
call :find_python
if not defined PY_CMD goto :python_missing
%PY_CMD% --version

echo.
echo  [2/7] Preparation du dossier...
if exist "%TMP_ZIP%" del /q "%TMP_ZIP%" >nul 2>&1
if exist "%TMP_DIR%" rd /s /q "%TMP_DIR%" >nul 2>&1
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo.
echo  [3/7] Telechargement de %APP_NAME%...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%REPO_ZIP%' -OutFile '%TMP_ZIP%' -UseBasicParsing"
if not exist "%TMP_ZIP%" (
    echo  [ERREUR] Telechargement impossible.
    echo  Verifiez la connexion internet ou l'adresse GitHub.
    pause
    exit /b 1
)

echo.
echo  [4/7] Installation des fichiers...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%TMP_ZIP%' -DestinationPath '%TMP_DIR%' -Force"
for /d %%D in ("%TMP_DIR%\*") do (
    xcopy /E /I /Y "%%D\*" "%INSTALL_DIR%\" >nul
)
if not exist "%INSTALL_DIR%\main.py" (
    echo  [ERREUR] main.py introuvable apres extraction.
    pause
    exit /b 1
)
del /q "%TMP_ZIP%" >nul 2>&1
rd /s /q "%TMP_DIR%" >nul 2>&1

echo.
echo  [5/7] Creation de l'environnement Python...
cd /d "%INSTALL_DIR%"
if exist ".venv" (
    echo  Ancien environnement detecte, nettoyage...
    rd /s /q ".venv"
)
%PY_CMD% -m venv .venv
if not exist "%INSTALL_DIR%\.venv\Scripts\python.exe" (
    echo  [ERREUR] Impossible de creer l'environnement virtuel.
    pause
    exit /b 1
)
set "VENV_PY=%INSTALL_DIR%\.venv\Scripts\python.exe"
set "VENV_PIP=%INSTALL_DIR%\.venv\Scripts\pip.exe"

echo.
echo  [6/7] Installation des dependances...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel
"%VENV_PIP%" install --prefer-binary -r "%INSTALL_DIR%\requirements.txt"
"%VENV_PIP%" install --prefer-binary "openwakeword>=0.6.0"
if errorlevel 1 (
    echo.
    echo  [ERREUR] L'installation des dependances a echoue.
    echo  Cause la plus probable : Python 3.14 ou trop recent.
    echo  Installez Python 3.13 ou 3.12 depuis python.org puis relancez.
    pause
    exit /b 1
)

echo.
echo  [7/7] Configuration et raccourcis...
if not exist "%INSTALL_DIR%\.env" (
    if exist "%INSTALL_DIR%\.env.example" (
        copy "%INSTALL_DIR%\.env.example" "%INSTALL_DIR%\.env" >nul
    ) else (
        echo AI_PROVIDER=groq> "%INSTALL_DIR%\.env"
        echo GROQ_API_KEY=VOTRE_CLE_GROQ_ICI>> "%INSTALL_DIR%\.env"
        echo GROQ_MODEL=llama-3.3-70b-versatile>> "%INSTALL_DIR%\.env"
        echo ASSISTANT_NAME=Boxy>> "%INSTALL_DIR%\.env"
        echo USER_NAME=Monsieur>> "%INSTALL_DIR%\.env"
        echo VOICE_ENABLED=true>> "%INSTALL_DIR%\.env"
        echo TTS_VOICE=fr-FR-DeniseNeural>> "%INSTALL_DIR%\.env"
        echo STT_LANGUAGE=fr>> "%INSTALL_DIR%\.env"
        echo THEME=cyan>> "%INSTALL_DIR%\.env"
    )
)
call :configure_api_key
call :write_launcher
call :create_shortcut

echo.
echo  ==========================================
echo    %APP_NAME% est installe.
echo  ==========================================
echo.
echo  Un raccourci "%APP_NAME%" a ete ajoute sur le Bureau.
echo.
choice /c LDQ /n /m "  L=Lancer  D=Ouvrir le dossier  Q=Quitter : "
if errorlevel 3 exit /b 0
if errorlevel 2 start "" explorer "%INSTALL_DIR%" & exit /b 0
start "" "%INSTALL_DIR%\Lancer Boxy.bat"
exit /b 0

:find_python
set "PY_CMD="
where py >nul 2>&1
if not errorlevel 1 (
    py -3.13 -c "import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3.13"
    if not defined PY_CMD (
        py -3.12 -c "import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)" >nul 2>&1
        if not errorlevel 1 set "PY_CMD=py -3.12"
    )
    if not defined PY_CMD (
        py -3.11 -c "import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)" >nul 2>&1
        if not errorlevel 1 set "PY_CMD=py -3.11"
    )
)
if not defined PY_CMD (
    where python >nul 2>&1
    if not errorlevel 1 (
        python -c "import sys; raise SystemExit(0 if (3, 11) <= sys.version_info[:2] < (3, 14) else 1)" >nul 2>&1
        if not errorlevel 1 set "PY_CMD=python"
    )
)
exit /b 0

:python_missing
echo.
echo  [ERREUR] Aucun Python compatible trouve.
echo  Python 3.14 est trop recent pour certaines dependances comme pygame.
echo  Installez Python 3.13 ou 3.12, puis relancez l'installateur.
choice /c OQ /n /m "  Ouvrir python.org ? O=Oui Q=Quitter : "
if errorlevel 2 exit /b 1
start "" "https://www.python.org/downloads/"
exit /b 1

:write_launcher
(
echo @echo off
echo cd /d "%%~dp0"
echo if exist ".venv\Scripts\pythonw.exe" ^(
echo     start "" ".venv\Scripts\pythonw.exe" "main.py" --ui
echo ^) else if exist ".venv\Scripts\python.exe" ^(
echo     ".venv\Scripts\python.exe" "main.py" --ui
echo ^) else ^(
echo     python "main.py" --ui
echo ^)
) > "%INSTALL_DIR%\Lancer Boxy.bat"
exit /b 0

:configure_api_key
echo.
echo  Configuration IA :
echo  - Appuyez sur Entree pour garder la configuration actuelle.
echo  - Collez votre cle Groq si vous voulez utiliser Boxy tout de suite.
set /p "GROQ_KEY=  Cle Groq : "
if "%GROQ_KEY%"=="" exit /b 0
powershell -NoProfile -ExecutionPolicy Bypass -Command "$envPath='%INSTALL_DIR%\.env'; $content=Get-Content -Raw $envPath; if ($content -match '(?m)^GROQ_API_KEY=') { $content=$content -replace '(?m)^GROQ_API_KEY=.*','GROQ_API_KEY=%GROQ_KEY%' } else { $content += \"`r`nGROQ_API_KEY=%GROQ_KEY%`r`n\" }; Set-Content -Path $envPath -Value $content -Encoding UTF8"
exit /b 0

:create_shortcut
set "SHORTCUT=%DESKTOP%\%APP_NAME%.lnk"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath='%INSTALL_DIR%\Lancer Boxy.bat'; $s.WorkingDirectory='%INSTALL_DIR%'; $s.Description='Lancer Boxy'; if (Test-Path '%INSTALL_DIR%\data\boxy.ico') { $s.IconLocation='%INSTALL_DIR%\data\boxy.ico' }; $s.Save()"
exit /b 0
