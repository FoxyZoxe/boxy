"""
automation/app_launcher.py — Ouvre et ferme des applications.

Fonctionnement :
1. On cherche l'app dans le dictionnaire KNOWN_APPS
2. Si trouvée → on lance l'exécutable directement
3. Sinon → on laisse Windows chercher via subprocess (fonctionne
   pour les apps dans le PATH comme notepad, calc, etc.)
"""

import subprocess
import os
import psutil
from pathlib import Path
from utils.logger import print_system, print_error

# Dictionnaire des applications connues avec leurs chemins possibles.
# On liste plusieurs chemins car l'installation peut varier (Program Files vs x86).
KNOWN_APPS: dict[str, list[str]] = {
    "chrome":    [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
    "firefox":   [r"C:\Program Files\Mozilla Firefox\firefox.exe"],
    "edge":      [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"],
    "notepad":   ["notepad.exe"],
    "calculatrice": ["calc.exe"],
    "calc":      ["calc.exe"],
    "explorateur": ["explorer.exe"],
    "explorer":  ["explorer.exe"],
    "discord":   [str(Path.home() / r"AppData\Local\Discord\Update.exe --processStart Discord.exe")],
    "spotify":   [str(Path.home() / r"AppData\Roaming\Spotify\Spotify.exe")],
    "vscode":    ["code"],
    "terminal":  ["wt.exe"],
    "cmd":       ["cmd.exe"],
    "paint":     ["mspaint.exe"],
    "word":      [r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"],
    "excel":     [r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"],
    "steam":     [r"C:\Program Files (x86)\Steam\steam.exe"],
    "vlc":       [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ],
    "obs":       [
        r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
        r"C:\Program Files (x86)\obs-studio\bin\32bit\obs32.exe",
    ],
}


class AppLauncher:
    """Gère l'ouverture et la fermeture d'applications."""

    def open(self, app_name: str) -> tuple[bool, str]:
        """
        Ouvre une application.

        Args:
            app_name: Nom de l'application (ex: "chrome", "notepad")

        Returns:
            (True, message_succès) ou (False, message_erreur)
        """
        name = app_name.lower().strip()
        executable = self._find_executable(name)

        if not executable:
            return False, f"Application '{app_name}' introuvable."

        try:
            # shell=True permet à Windows de résoudre les noms simples (notepad, calc)
            subprocess.Popen(executable, shell=True)
            return True, f"{app_name} lancé."
        except Exception as e:
            print_error(f"AppLauncher — impossible d'ouvrir '{app_name}' : {e}")
            return False, f"Impossible d'ouvrir '{app_name}'."

    def close(self, app_name: str) -> tuple[bool, str]:
        """
        Ferme tous les processus dont le nom contient app_name.

        Args:
            app_name: Nom partiel du processus (ex: "chrome", "notepad")

        Returns:
            (True, message) ou (False, message)
        """
        name = app_name.lower().strip()
        killed = []

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if name in proc.info["name"].lower():
                    proc.terminate()
                    killed.append(proc.info["name"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed:
            return True, f"{app_name} fermé."
        return False, f"Aucun processus '{app_name}' trouvé."

    def open_url(self, url: str) -> tuple[bool, str]:
        """Ouvre une URL dans le navigateur par défaut."""
        import webbrowser
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            webbrowser.open(url)
            return True, f"Ouverture de {url}."
        except Exception as e:
            return False, f"Impossible d'ouvrir l'URL : {e}"

    def _find_executable(self, name: str) -> str | None:
        """
        Cherche l'exécutable dans cet ordre :
        1. Dictionnaire KNOWN_APPS (chemins hardcodés)
        2. Registre Windows App Paths (fiable pour Chrome, Firefox...)
        3. shutil.which (apps dans le PATH système)
        4. Nom brut en dernier recours
        """
        import shutil
        import winreg

        # 1. Dictionnaire hardcodé
        if name in KNOWN_APPS:
            for path in KNOWN_APPS[name]:
                exe = path.split()[0]
                if Path(exe).exists():
                    return path

        # 2. Registre Windows — là où sont enregistrées toutes les apps installées
        exe_name = name if name.endswith(".exe") else name + ".exe"
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            reg_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"
            try:
                key = winreg.OpenKey(root, reg_path)
                path, _ = winreg.QueryValueEx(key, None)
                winreg.CloseKey(key)
                if path and Path(path).exists():
                    return f'"{path}"'
            except (FileNotFoundError, OSError):
                continue

        # 3. PATH système
        found = shutil.which(name)
        if found:
            return found

        # 4. Dernier recours — Windows tentera de le résoudre lui-même
        return name