"""
automation/keyboard_control.py — Contrôle clavier et souris.

pyautogui contrôle la souris et peut taper du texte.
keyboard gère les raccourcis et touches spéciales.

IMPORTANT : ces fonctions agissent sur la fenêtre active.
Assure-toi que le focus est sur la bonne application avant d'appeler.
"""

import time
import pyautogui
import keyboard
from utils.logger import print_error

# Désactive le failsafe pyautogui (déplacement souris coin supérieur gauche = arrêt)
# On le garde activé par sécurité — déplace la souris en haut à gauche pour tout arrêter
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05  # Petite pause entre chaque action (plus naturel)


class KeyboardControl:
    """Tape du texte et exécute des raccourcis clavier."""

    def type_text(self, text: str, delay: float = 0.05) -> tuple[bool, str]:
        """
        Tape du texte dans la fenêtre active.

        Args:
            text: Texte à taper
            delay: Délai entre chaque caractère (secondes)
        """
        try:
            time.sleep(0.3)  # Laisse le temps à la fenêtre d'avoir le focus
            pyautogui.write(text, interval=delay)
            return True, f"Texte tapé : '{text[:30]}...'" if len(text) > 30 else f"Texte tapé."
        except Exception as e:
            print_error(f"Type text — erreur : {e}")
            return False, f"Impossible de taper le texte : {e}"

    def press_key(self, keys: str) -> tuple[bool, str]:
        """
        Appuie sur une touche ou un raccourci.

        Args:
            keys: Touche ou raccourci (ex: "ctrl+c", "alt+f4", "enter", "escape")
        """
        try:
            # pyautogui.hotkey accepte les touches séparées par '+'
            if "+" in keys:
                parts = [k.strip() for k in keys.split("+")]
                pyautogui.hotkey(*parts)
            else:
                pyautogui.press(keys)
            return True, f"Touche '{keys}' appuyée."
        except Exception as e:
            print_error(f"Press key — erreur : {e}")
            return False, f"Touche '{keys}' inconnue."

    def copy(self) -> tuple[bool, str]:
        """Ctrl+C"""
        return self.press_key("ctrl+c")

    def paste(self) -> tuple[bool, str]:
        """Ctrl+V"""
        return self.press_key("ctrl+v")

    def undo(self) -> tuple[bool, str]:
        """Ctrl+Z"""
        return self.press_key("ctrl+z")

    def select_all(self) -> tuple[bool, str]:
        """Ctrl+A"""
        return self.press_key("ctrl+a")

    def close_window(self) -> tuple[bool, str]:
        """Alt+F4"""
        return self.press_key("alt+f4")

    def minimize_window(self) -> tuple[bool, str]:
        """Win+D (affiche le bureau)"""
        return self.press_key("win+d")