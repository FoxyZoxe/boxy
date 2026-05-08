"""
automation/command_executor.py — Exécute les commandes extraites des réponses IA.

Boxy reçoit une réponse de l'IA qui peut contenir des blocs :
    [CMD:{"action": "open_app", "name": "chrome"}]

Ce module :
1. Parse ces blocs JSON
2. Route vers le bon module d'automation
3. Retourne le résultat pour que Boxy puisse le vocaliser
"""

import json
import re
from automation.app_launcher import AppLauncher

# Regex pour corriger les backslashes invalides dans les chemins JSON.
# En JSON, seuls \\ \" \/ \b \f \n \r \t \uXXXX sont valides.
# L'IA génère souvent C:\Users\... avec des \ simples → on les double.
_BAD_BACKSLASH = re.compile(r'\\(?!["\\/bfnrtu])')
from automation.system_control import SystemControl
from automation.keyboard_control import KeyboardControl
from utils.logger import print_system, print_error

# Imports lazy — chargés uniquement quand nécessaire pour ne pas alourdir le démarrage
_vision    = None
_image_gen = None
_obs       = None
_web       = None

def _get_vision():
    global _vision
    if _vision is None:
        from ai.vision_provider import VisionProvider
        _vision = VisionProvider()
    return _vision

def _get_image_gen():
    global _image_gen
    if _image_gen is None:
        from ai.image_generator import ImageGenerator
        _image_gen = ImageGenerator()
    return _image_gen

def _get_obs():
    global _obs
    if _obs is None:
        from integrations.obs_control import OBSControl
        _obs = OBSControl()
    return _obs

def _get_web():
    global _web
    if _web is None:
        from ai.web_search import WebSearch
        _web = WebSearch()
    return _web

# Regex pour extraire les blocs [CMD:...] d'une réponse IA
CMD_PATTERN = re.compile(r'\[CMD:(.*?)\]', re.DOTALL)

# Phrases qui indiquent que le modèle récite le system prompt au lieu d'agir
_META_PHRASES = [
    "je comprends que je ne devrais pas",
    "je comprends que je dois",
    "je comprends également",
    "merci pour les informations",
    "merci pour ces informations",
    "tu m'as indiqué",
    "comme tu me l'as précisé",
    "comme indiqué dans la règle",
    "je vais suivre ces règles",
    "je vais respecter ces règles",
    "j'ai bien compris les règles",
    "je retiens que",
    "j'ai compris que je ne dois pas",
    "je ne dois jamais inclure",
    "je ne fais pas de salutations",
    "voici les commandes disponibles",
    "voici une liste",
    "voici quelques actions",
    "actions disponibles",
    "comme indiqué dans",
    "les chemins seront toujours",
    "en tant qu'assistant",
    "en tant qu'ia",
    "règle n°",
    "si vous avez besoin d'une action",
]

# Noms d'actions que le modèle ne doit pas lister dans ses réponses
_ACTION_NAMES = [
    "open_app", "close_app", "open_url", "volume_set", "volume_up",
    "volume_down", "volume_mute", "screenshot", "type_text", "press_key",
    "run_command", "shutdown", "restart", "sleep", "save_file", "read_file",
    "append_file", "read_clipboard", "write_clipboard", "web_search",
    "analyze_screen", "read_screen", "analyze_image", "generate_image",
]

# Détecte une ligne qui liste des actions (commence par *, -, • ou contient plusieurs noms d'actions)
_LIST_LINE = re.compile(r'^\s*[\*\-•]\s+\w', re.MULTILINE)


def _is_meta_response(text: str) -> bool:
    """
    Détecte si le modèle récite le system prompt, liste ses capacités,
    ou "explique ses règles" au lieu de répondre normalement.
    """
    lower = text.lower()
    if any(phrase in lower for phrase in _META_PHRASES):
        return True
    # Détecte si le texte contient 4+ noms d'actions distincts → c'est une liste
    matches = sum(1 for a in _ACTION_NAMES if a in lower)
    if matches >= 4:
        return True
    return False


def _clean_response(text: str) -> str:
    """
    Supprime de force les sections "liste de capacités" d'une réponse,
    même si elle n'est pas entièrement méta.
    Garde uniquement les parties narratives (pas de listes à puces).
    """
    lines = text.splitlines()
    clean_lines = []
    skip_block = False

    for line in lines:
        stripped = line.strip()

        # Début d'un bloc "voici les commandes" → ignore tout ce qui suit
        lower = stripped.lower()
        if any(p in lower for p in ("voici les", "voici une liste", "voici quelques",
                                     "actions disponibles", "commandes disponibles",
                                     "pour commencer", "liste de")):
            skip_block = True
            continue

        # Ligne à puce contenant un nom d'action → ignore
        if skip_block or (re.match(r'^\s*[\*\-•`]', line) and
                          any(a in line.lower() for a in _ACTION_NAMES)):
            continue

        # Bloc de code entier (``` ... ```) contenant des actions → ignore
        if stripped.startswith("```"):
            skip_block = not skip_block
            continue

        skip_block = False
        clean_lines.append(line)

    return "\n".join(clean_lines).strip()


class CommandExecutor:
    """Parse et exécute les commandes incluses dans les réponses IA."""

    def __init__(self):
        self.app_launcher   = AppLauncher()
        self.system_control = SystemControl()
        self.keyboard       = KeyboardControl()

    def execute_action(self, action: str, **kwargs) -> tuple[bool, str]:
        """Exécute une action directement (sans passer par du texte IA)."""
        cmd = {"action": action, **kwargs}
        try:
            return self._execute(cmd)
        except Exception as e:
            return False, str(e)

    def process_response(self, ai_response: str) -> tuple[str, list[str]]:
        """
        Extrait les commandes d'une réponse IA, les exécute,
        et retourne le texte nettoyé + les résultats.

        Args:
            ai_response: Réponse brute de l'IA

        Returns:
            (texte_sans_commandes, [résultats_des_commandes])
        """
        if not ai_response:
            return "", []

        # Sécurité : si le modèle récite les règles du system prompt, on ignore
        # tous les [CMD] (ce sont des "exemples" involontaires) et on retourne vide
        # pour déclencher un retry dans jarvis.py
        if _is_meta_response(ai_response):
            print_system("  Réponse méta détectée — réponse ignorée, retry en cours.")
            return "", []

        commands = CMD_PATTERN.findall(ai_response)
        # Supprime les CMD + les éventuelles listes de capacités qui traînent
        clean_text = _clean_response(CMD_PATTERN.sub("", ai_response))
        results = []

        if commands:
            print_system(f"  {len(commands)} commande(s) détectée(s) dans la réponse IA")

        for cmd_json in commands:
            # --- Parse JSON avec correction automatique ---
            raw = cmd_json.strip()
            # Passe 1 : corrige les backslashes invalides (C:\Users → C:\\Users)
            raw_fixed = _BAD_BACKSLASH.sub(r'\\\\', raw)

            cmd_list = None
            for attempt in (raw_fixed, f"[{raw_fixed}]", raw, f"[{raw}]"):
                try:
                    parsed = json.loads(attempt)
                    cmd_list = parsed if isinstance(parsed, list) else [parsed]
                    if attempt.startswith("[") and len(cmd_list) > 1:
                        print_system(f"  (multi-actions groupées : {len(cmd_list)} actions)")
                    break
                except json.JSONDecodeError:
                    continue

            if cmd_list is None:
                print_error(f"Commande JSON invalide (non récupérable) : {raw[:80]}...")
                continue

            # --- Exécute chaque action dans l'ordre ---
            for cmd in cmd_list:
                if not isinstance(cmd, dict):
                    continue
                try:
                    success, message = self._execute(cmd)
                    results.append(message)
                    status = "✓" if success else "✗"
                    print_system(f"{status} Commande '{cmd.get('action')}' → {message}")
                except Exception as e:
                    action = cmd.get("action", "?")
                    print_error(f"Échec commande '{action}' : {e}")
                    results.append(f"Erreur lors de l'exécution de '{action}'.")

        return clean_text, results

    def _execute(self, cmd: dict) -> tuple[bool, str]:
        """Route la commande vers le bon module."""
        action = cmd.get("action", "")

        # --- Applications ---
        if action == "open_app":
            return self.app_launcher.open(cmd.get("name", ""))

        elif action == "close_app":
            return self.app_launcher.close(cmd.get("name", ""))

        elif action == "open_url":
            return self.app_launcher.open_url(cmd.get("url", ""))

        # --- Volume ---
        elif action == "volume_set":
            return self.system_control.set_volume(int(cmd.get("value", 50)))

        elif action == "volume_up":
            return self.system_control.volume_up(int(cmd.get("steps", 10)))

        elif action == "volume_down":
            return self.system_control.volume_down(int(cmd.get("steps", 10)))

        elif action == "volume_mute":
            return self.system_control.mute()

        # --- Système ---
        elif action == "screenshot":
            return self.system_control.screenshot()

        elif action == "run_command":
            return self.system_control.run_shell_command(cmd.get("cmd", ""))

        elif action == "shutdown":
            return self.system_control.shutdown(int(cmd.get("delay", 10)))

        elif action == "restart":
            return self.system_control.restart(int(cmd.get("delay", 10)))

        elif action == "sleep":
            return self.system_control.sleep()

        # --- Clavier ---
        elif action == "type_text":
            return self.keyboard.type_text(cmd.get("text", ""))

        elif action == "press_key":
            return self.keyboard.press_key(cmd.get("key", ""))

        # --- Fichiers ---
        elif action in ("save_file", "create_file", "write_file"):
            return self._action_save_file(
                path    = cmd.get("path", ""),
                content = cmd.get("content", cmd.get("text", "")),
            )

        elif action == "read_file":
            return self._action_read_file(cmd.get("path", ""))

        elif action == "append_file":
            return self._action_save_file(
                path    = cmd.get("path", ""),
                content = cmd.get("content", cmd.get("text", "")),
                append  = True,
            )

        # --- Recherche web ---
        elif action == "web_search":
            query = cmd.get("query", cmd.get("q", ""))
            if not query:
                return False, "Paramètre 'query' manquant pour la recherche web."
            result = _get_web().search(query)
            # Tag [WEB] pour que jarvis.py sache faire un 2e appel IA
            return True, f"[WEB]{result}"

        # --- Vision (Phase 5) ---
        elif action == "analyze_screen":
            # Analyse ce qui est affiché à l'écran
            prompt = cmd.get("prompt", None)
            result = _get_vision().analyze_screenshot(prompt)
            return True, result

        elif action == "read_screen":
            # Extrait uniquement le texte visible à l'écran
            result = _get_vision().read_screen_text()
            return True, result

        elif action == "analyze_image":
            path   = cmd.get("path", "")
            prompt = cmd.get("prompt", None)
            result = _get_vision().analyze_image_file(path, prompt)
            return True, result

        # --- Génération d'images ---
        elif action == "generate_image":
            prompt = cmd.get("prompt", "")
            style  = cmd.get("style", None)
            if not prompt:
                return False, "Prompt manquant pour la génération d'image."
            success, result = _get_image_gen().generate(prompt, style)
            if success:
                return True, f"Image générée et sauvegardée."
            return False, result

        # --- Presse-papiers ---
        elif action == "read_clipboard":
            return self._action_read_clipboard()

        elif action == "write_clipboard":
            return self._action_write_clipboard(cmd.get("text", cmd.get("content", "")))

        # --- OBS ---
        elif action == "obs_start_stream":
            return _get_obs().start_streaming()

        elif action == "obs_stop_stream":
            return _get_obs().stop_streaming()

        elif action == "obs_toggle_stream":
            return _get_obs().toggle_streaming()

        elif action == "obs_start_record":
            return _get_obs().start_recording()

        elif action == "obs_stop_record":
            return _get_obs().stop_recording()

        elif action == "obs_set_scene":
            return _get_obs().set_scene(cmd.get("name", ""))

        elif action == "obs_get_scenes":
            scenes = _get_obs().get_scenes()
            return True, f"Scènes disponibles : {', '.join(scenes)}" if scenes else "Aucune scène trouvée."

        else:
            return False, f"Action inconnue : '{action}'"

    # ─── Helpers fichiers ────────────────────────────────────────────────

    @staticmethod
    def _action_save_file(path: str, content: str, append: bool = False) -> tuple[bool, str]:
        """
        Crée ou écrase un fichier avec le contenu donné.

        Supporte les chemins avec ~, les variables d'env Windows (%USERPROFILE% etc.)
        et crée les dossiers parents si nécessaire.
        """
        from pathlib import Path
        import os

        if not path:
            return False, "Chemin de fichier manquant."

        # Résolution des chemins spéciaux
        path = os.path.expandvars(path)   # %USERPROFILE%, %DESKTOP%...
        path = os.path.expanduser(path)   # ~
        file_path = Path(path)

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with open(file_path, mode, encoding="utf-8") as f:
                # Remplace les \n littéraux que l'IA peut inclure
                f.write(content.replace("\\n", "\n").replace("\\t", "\t"))

            action_word = "Ajout dans" if append else "Fichier créé"

            # Ouvre automatiquement le fichier texte dans le bloc-notes
            if not append and file_path.suffix.lower() in (".txt", ".md", ".log", ".csv"):
                import subprocess
                subprocess.Popen(["notepad.exe", str(file_path)])

            return True, f"{action_word} : {file_path.name}"
        except PermissionError:
            return False, f"Permission refusée pour écrire dans '{file_path}'."
        except Exception as e:
            return False, f"Impossible d'écrire le fichier : {e}"

    # ─── Helpers presse-papiers ──────────────────────────────────────

    @staticmethod
    def _action_read_clipboard() -> tuple[bool, str]:
        """Lit le contenu du presse-papiers système."""
        try:
            import pyperclip
            content = pyperclip.paste()
            if not content:
                return False, "Presse-papiers vide."
            if len(content) > 2000:
                content = content[:2000] + "\n[… tronqué]"
            return True, content
        except Exception as e:
            return False, f"Impossible de lire le presse-papiers : {e}"

    @staticmethod
    def _action_write_clipboard(text: str) -> tuple[bool, str]:
        """Écrit du texte dans le presse-papiers système."""
        try:
            import pyperclip
            pyperclip.copy(text)
            short = text[:40] + ("…" if len(text) > 40 else "")
            return True, f"Copié dans le presse-papiers : {short}"
        except Exception as e:
            return False, f"Impossible d'écrire dans le presse-papiers : {e}"

    @staticmethod
    def _action_read_file(path: str) -> tuple[bool, str]:
        """Lit et retourne le contenu d'un fichier."""
        from pathlib import Path
        import os

        if not path:
            return False, "Chemin de fichier manquant."

        path = os.path.expandvars(path)
        path = os.path.expanduser(path)
        file_path = Path(path)

        try:
            content = file_path.read_text(encoding="utf-8")
            # Limite à 2000 caractères pour ne pas noyer la réponse vocale
            if len(content) > 2000:
                content = content[:2000] + "\n[… contenu tronqué]"
            return True, content
        except FileNotFoundError:
            return False, f"Fichier introuvable : '{file_path}'."
        except Exception as e:
            return False, f"Impossible de lire le fichier : {e}"