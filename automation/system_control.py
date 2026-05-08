"""
automation/system_control.py — Contrôle du système Windows.

Fonctions : volume, capture d'écran, veille, arrêt, redémarrage.

Pour le volume on utilise pycaw — bibliothèque qui communique
directement avec l'API audio Windows (Core Audio API).
C'est plus fiable que d'envoyer des touches média.
"""

import subprocess
import os
from datetime import datetime
from pathlib import Path
from utils.logger import print_error, print_system


class SystemControl:
    """Contrôle les fonctions système de Windows."""

    def set_volume(self, level: int) -> tuple[bool, str]:
        """Définit le volume maître à un niveau précis (0-100)."""
        level = max(0, min(100, level))
        try:
            iface = self._get_volume_interface()
            iface.SetMasterVolumeLevelScalar(level / 100.0, None)
            return True, f"Volume réglé à {level}%."
        except Exception as e:
            print_error(f"Volume — erreur : {e}")
            return False, "Impossible de modifier le volume."

    def _get_volume_interface(self):
        """
        Retourne l'interface IAudioEndpointVolume.

        Pycaw a changé son API dans les nouvelles versions.
        On essaie 3 méthodes dans l'ordre jusqu'à ce qu'une fonctionne.
        """
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        # Méthode 1 : via ._dev (nouvelles versions de pycaw)
        # GetSpeakers() retourne un AudioDevice wrapper, le vrai objet COM est dans ._dev
        try:
            speakers = AudioUtilities.GetSpeakers()
            dev = speakers._dev
            if dev is not None:
                interface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                return cast(interface, POINTER(IAudioEndpointVolume))
        except Exception:
            pass

        # Méthode 2 : appel direct (anciennes versions de pycaw)
        # GetSpeakers() retournait directement l'objet COM
        try:
            speakers = AudioUtilities.GetSpeakers()
            interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return cast(interface, POINTER(IAudioEndpointVolume))
        except Exception:
            pass

        # Méthode 3 : contournement total via l'énumérateur COM Windows
        # Ne dépend pas de la version de pycaw
        from comtypes.client import CreateObject
        from pycaw.pycaw import CLSID_MMDeviceEnumerator, IMMDeviceEnumerator

        enumerator = CreateObject(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
        # eRender=0, eMultimedia=1 → périphérique de lecture par défaut
        device = enumerator.GetDefaultAudioEndpoint(0, 1)
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))

    def get_volume(self) -> int:
        """Retourne le volume actuel (0-100), ou -1 si erreur."""
        try:
            return int(self._get_volume_interface().GetMasterVolumeLevelScalar() * 100)
        except Exception:
            return -1

    def mute(self) -> tuple[bool, str]:
        """Coupe ou réactive le son."""
        try:
            import keyboard
            keyboard.press_and_release("volume mute")
            return True, "Son coupé / réactivé."
        except Exception as e:
            return False, f"Erreur mute : {e}"

    def volume_up(self, steps: int = 5) -> tuple[bool, str]:
        """Monte le volume de N%."""
        current = self.get_volume()
        if current >= 0:
            return self.set_volume(min(100, current + steps))
        try:
            import keyboard
            for _ in range(steps // 2):
                keyboard.press_and_release("volume up")
            return True, "Volume augmenté."
        except Exception as e:
            return False, str(e)

    def volume_down(self, steps: int = 5) -> tuple[bool, str]:
        """Baisse le volume de N%."""
        current = self.get_volume()
        if current >= 0:
            return self.set_volume(max(0, current - steps))
        try:
            import keyboard
            for _ in range(steps // 2):
                keyboard.press_and_release("volume down")
            return True, "Volume baissé."
        except Exception as e:
            return False, str(e)

    def screenshot(self, save_dir: str = None) -> tuple[bool, str]:
        """Prend une capture d'écran avec PIL (plus fiable que pyautogui)."""
        save_dir = save_dir or str(Path.home() / "Pictures")
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join(save_dir, f"screenshot_{timestamp}.png")

        # Méthode 1 : PIL ImageGrab (recommandé, fonctionne sur Python 3.13)
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(filepath)
            return True, f"Capture sauvegardée dans Mes Images."
        except ImportError:
            pass

        # Méthode 2 : mss (ultra-rapide, zéro dépendances problématiques)
        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=filepath)
            return True, f"Capture sauvegardée dans Mes Images."
        except ImportError:
            pass

        return False, "Installe Pillow : pip install Pillow"

    def shutdown(self, delay: int = 0) -> tuple[bool, str]:
        """Éteint l'ordinateur."""
        try:
            subprocess.run(["shutdown", "/s", f"/t {delay}"], check=True)
            return True, f"Arrêt dans {delay} secondes."
        except Exception as e:
            return False, f"Impossible d'éteindre : {e}"

    def restart(self, delay: int = 0) -> tuple[bool, str]:
        """Redémarre l'ordinateur."""
        try:
            subprocess.run(["shutdown", "/r", f"/t {delay}"], check=True)
            return True, f"Redémarrage dans {delay} secondes."
        except Exception as e:
            return False, f"Impossible de redémarrer : {e}"

    def sleep(self) -> tuple[bool, str]:
        """Met l'ordinateur en veille."""
        try:
            subprocess.run(
                ["powershell", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('Suspend', $false, $false)"],
                check=True
            )
            return True, "Mise en veille."
        except Exception as e:
            return False, f"Veille impossible : {e}"

    def run_shell_command(self, command: str) -> tuple[bool, str]:
        """
        Exécute une commande shell et retourne la sortie.

        SÉCURITÉ : n'exécute que des commandes non-destructives.
        Les commandes dangereuses (rm, del, format) sont bloquées.
        """
        BLOCKED = ["rm ", "del ", "format ", "rd /s", "rmdir /s", ":(){ :|:& };:"]
        cmd_lower = command.lower()

        if any(blocked in cmd_lower for blocked in BLOCKED):
            return False, "Commande bloquée pour des raisons de sécurité."

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            output = result.stdout.strip() or result.stderr.strip() or "Commande exécutée."
            return True, output[:500]  # Limite la sortie à 500 caractères
        except subprocess.TimeoutExpired:
            return False, "La commande a dépassé le délai d'attente."
        except Exception as e:
            return False, f"Erreur d'exécution : {e}"