"""
core/jarvis.py — Classe principale de Boxy (Phase 2 — Voix).
"""

import re
import keyboard
import time
from ai.ai_manager import AIManager
from memory.memory_manager import MemoryManager
from voice.voice_manager import VoiceManager
from automation.command_executor import CommandExecutor
from utils.logger import (
    print_jarvis, print_user, print_system, print_error,
    print_success, print_separator, console
)
from config import Config

# ─── Filtre anti-salutation ───────────────────────────────────────────────────
# Le modèle a tendance à commencer ses réponses par des présentations/salutations.
# Ces patterns sont détectés EN DÉBUT de réponse et supprimés.
_GREETING_PATTERNS = re.compile(
    r'^('
    r'(bonjour|bonsoir|salut|hey)[^.!?\n]*[.!?\n]*\s*'       # "Bonjour Sir !", "Bonsoir !"
    r'|je (suis|m\'appelle|me nomme) [^.!?\n]*[.!?\n]*\s*'  # "Je suis Boxy..."
    r'|en tant (que|qu\') ?[^,.\n]*[,.\n]\s*'                # "En tant qu'assistant..."
    r'|comme [^,.\n]*(assistant|ia|boxy)[^.!\n]*[.!\n]\s*'  # "Comme assistant IA..."
    r'|(je suis |votre |ton )?(assistant|boxy)[^.!\n]*[.!\n]\s*'  # "Votre assistant Boxy..."
    r')',
    re.IGNORECASE,
)

def _strip_greeting(text: str) -> str:
    """
    Supprime le préfixe de salutation/présentation généré par le modèle.
    Exemples supprimés :
      "Bonjour Sir ! Comment puis-je…"  → ""
      "Je suis Boxy, votre assistant…"  → ""
    Si toute la réponse est une salutation, on la garde (rien d'autre à dire).
    """
    cleaned = _GREETING_PATTERNS.sub("", text).strip()
    # Si on a tout supprimé, on garde l'original (mieux que rien)
    return cleaned if cleaned else text


class Boxy:
    COMMANDS = {
        # ── Système ──────────────────────────────────────────────────
        "/quitter":     f"Quitte {Config.ASSISTANT_NAME}",
        "/aide":        "Affiche cette aide",
        "/clear":       "Efface l'historique de conversation",
        "/status":      "Affiche le statut du système",
        # ── Voix ─────────────────────────────────────────────────────
        "/voix":        "Active/désactive la synthèse vocale",
        "/ecoute":      "Lance une écoute manuelle",
        # ── Actions rapides ──────────────────────────────────────────
        "/screenshot":  "Capture l'écran",
        "/volume":      "Règle le volume  ex: /volume 50",
        "/recherche":   "Recherche web    ex: /recherche météo Paris",
        "/note":        "Crée une note    ex: /note Penser à appeler Marie",
        "/clipboard":   "Lit le presse-papiers",
        "/timer":       "Lance un timer   ex: /timer 5  (minutes)",
        # ── Interface ────────────────────────────────────────────────
        "/theme":       "Change le thème  ex: /theme red",
        "/export":      "Exporte la conversation",
        "/historique":  "Affiche les conversations passées",
        "/compact":     "Passe en mode compact",
        "/memoire":     "Affiche la mémoire long-terme",
    }

    def __init__(self, on_response=None, on_user_message=None, on_status=None,
                 on_token=None, on_stream_start=None, on_stream_end=None,
                 on_error=None, on_timing=None):
        """
        Args:
            on_response:     callback(text) — réponse finale complète
            on_user_message: callback(text) — utilisateur a écrit/parlé
            on_status:       callback(status) — "idle"|"listening"|"thinking"|"speaking"
            on_token:        callback(token) — token streamé (UI live)
            on_stream_start: callback() — début du streaming
            on_stream_end:   callback(text) — fin streaming, texte nettoyé
            on_error:        callback(msg) — erreur à afficher dans l'UI
            on_timing:       callback(seconds) — durée de génération
        """
        print_system(f"Initialisation de {Config.ASSISTANT_NAME}...")
        self.memory   = MemoryManager()
        self.ai       = AIManager()
        self.voice    = VoiceManager()
        self.executor = CommandExecutor()

        self._on_response     = on_response
        self._on_user_message = on_user_message
        self._on_status       = on_status
        self._on_token        = on_token
        self._on_stream_start = on_stream_start
        self._on_stream_end   = on_stream_end
        self._on_error        = on_error
        self._on_timing       = on_timing

        print_success(f"{Config.ASSISTANT_NAME} opérationnel.")

        # Remonte l'erreur wake word dans l'UI si elle a eu lieu
        if getattr(self.voice, "_wake_word_error", None):
            self._emit_error(
                f"Wake word désactivé : {self.voice._wake_word_error}\n"
                "→ Lance : pip install openwakeword  puis redémarre."
            )

    def _emit_response(self, text: str) -> None:
        """Affiche la réponse dans le terminal ET notifie l'UI si connectée."""
        print_jarvis(text)
        if self._on_response:
            self._on_response(text)

    def _emit_user_message(self, text: str) -> None:
        print_user(text)
        if self._on_user_message:
            self._on_user_message(text)

    def _emit_status(self, status: str) -> None:
        if self._on_status:
            self._on_status(status)

    def _emit_error(self, msg: str) -> None:
        print_error(msg)
        if self._on_error:
            self._on_error(msg)

    def _emit_timing(self, seconds: float) -> None:
        if self._on_timing:
            self._on_timing(seconds)

    def process_input(self, user_input: str) -> None:
        user_input = user_input.strip()
        if not user_input:
            return
        try:
            if user_input.startswith("/"):
                self._handle_command(user_input)
            else:
                self._chat_with_ai(user_input)
        except Exception as e:
            self._emit_error(f"Erreur inattendue : {e}")
            self._emit_status("idle")

    def _get_clean_ai_response(self, messages: list[dict],
                               stream: bool,
                               token_callback=None) -> tuple[str, str, list]:
        """
        Appelle l'IA, nettoie la réponse, exécute les commandes UNE SEULE FOIS.

        Si la réponse est méta (le modèle récite ses règles), un retry
        non-streamé est lancé automatiquement avec un message de correction.

        Returns:
            (raw, clean_text, cmd_results)
        """
        raw = self._call_ai_with_timeout(
            messages, stream=stream, token_callback=token_callback
        ) or ""

        clean_text, cmd_results = self.executor.process_response(raw)
        clean_text = _strip_greeting(clean_text)

        # Réponse méta ou complètement vide → retry silencieux (non-streamé)
        if raw and not clean_text and not cmd_results:
            print_system("  Retry : réponse méta, relance sans streaming...")
            retry_messages = messages + [
                {"role": "assistant", "content": raw[:300]},
                {"role": "user",      "content": "Réponds directement en 1 phrase. Pas de liste."},
            ]
            raw2 = self._call_ai_with_timeout(retry_messages, stream=False) or ""
            if raw2:
                clean_text2, cmd_results2 = self.executor.process_response(raw2)
                clean_text2 = _strip_greeting(clean_text2)
                if clean_text2 or cmd_results2:
                    return raw2, clean_text2, cmd_results2
            return "", "", []

        return raw, clean_text, cmd_results

    def _chat_with_ai(self, user_input: str) -> bool:
        """
        Envoie le message à l'IA, affiche et vocalise la réponse.

        Returns:
            True  — réponse terminée normalement
            False — interrompue pendant la lecture vocale
        """
        self.memory.add_message("user", user_input)
        messages = self.memory.get_messages_for_ai()

        self._emit_status("thinking")
        t_start = time.time()

        try:
            if self.voice.is_enabled:
                # Mode vocal : on attend la réponse complète avant de parler
                raw, clean_text, cmd_results = self._get_clean_ai_response(messages, stream=False)
                if not raw:
                    self._emit_status("idle")
                    return True

                clean_text, cmd_results = self._handle_web_results(
                    clean_text, cmd_results, messages
                )
                full_response = self._build_full_response(clean_text, cmd_results)
                self._emit_timing(time.time() - t_start)

                if full_response:
                    self._emit_response(full_response)
                    self._emit_status("speaking")
                    completed = self.voice.speak(full_response)
                else:
                    completed = True

                self.memory.add_message(
                    "assistant", clean_text or "[commande exécutée]"
                )
                self._emit_status("idle")
                return completed

            else:
                # Mode texte : streaming token par token vers l'UI
                has_ui_stream = bool(self._on_token)

                if has_ui_stream and self._on_stream_start:
                    self._on_stream_start()

                def _tok(t):
                    if self._on_token:
                        self._on_token(t)

                raw, clean_text, cmd_results = self._get_clean_ai_response(
                    messages,
                    stream=True,
                    token_callback=_tok if has_ui_stream else None,
                )

                clean_text, cmd_results = self._handle_web_results(
                    clean_text, cmd_results, messages
                )
                full_response = self._build_full_response(clean_text, cmd_results)
                self._emit_timing(time.time() - t_start)

                if has_ui_stream and self._on_stream_end:
                    self._on_stream_end(full_response or "")
                elif full_response:
                    self._emit_response(full_response)

                # Sauvegarde UNIQUEMENT le texte de l'IA dans l'historique
                self.memory.add_message(
                    "assistant", clean_text or "[commande exécutée]"
                )
                self._emit_status("idle")
                return True

        except TimeoutError:
            self._emit_error(
                f"Timeout : le modèle n'a pas répondu en {Config.AI_TIMEOUT}s.\n"
                "Vérifiez qu'Ollama tourne (ollama serve)."
            )
            if self._on_stream_end:
                self._on_stream_end("")
            self._emit_status("idle")
            return True
        except Exception as e:
            self._emit_error(f"Erreur IA : {e}")
            if self._on_stream_end:
                self._on_stream_end("")
            self._emit_status("idle")
            return True

    def _call_ai_with_timeout(self, messages, stream, token_callback=None) -> str:
        """
        Appelle l'IA avec un timeout surveillé dans un thread daemon.

        On utilise threading.Thread (pas ThreadPoolExecutor) pour éviter
        que les tokens streamés arrivent depuis un thread détaché qui continue
        de s'exécuter après le timeout et pollue la session suivante.
        """
        import threading
        timeout    = Config.AI_TIMEOUT
        result     = [None]
        exc        = [None]
        done       = threading.Event()
        timed_out  = [False]   # Partagé entre les threads

        def _run() -> None:
            try:
                def _safe_tok(t):
                    # Jette les tokens si on a déjà déclenché le timeout
                    if timed_out[0]:
                        return
                    if token_callback:
                        token_callback(t)

                result[0] = self.ai.chat(
                    messages,
                    stream=stream,
                    token_callback=_safe_tok if token_callback else None,
                )
            except Exception as e:
                exc[0] = e
            finally:
                done.set()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        finished = done.wait(timeout)

        if not finished:
            timed_out[0] = True   # Coupe les tokens en retard
            raise TimeoutError(f"IA timeout après {timeout}s")

        if exc[0]:
            raise exc[0]

        return result[0] or ""

    def _handle_web_results(
        self,
        clean_text: str,
        cmd_results: list[str],
        original_messages: list[dict],
    ) -> tuple[str, list[str]]:
        """
        Si des résultats web (tag [WEB]) sont présents, fait un second appel IA
        pour synthétiser une réponse naturelle basée sur ces résultats.

        Retourne (clean_text, cmd_results) mis à jour.
        """
        web_results  = [r[5:] for r in cmd_results if r.startswith("[WEB]")]
        other_results = [r for r in cmd_results if not r.startswith("[WEB]")]

        if not web_results:
            return clean_text, cmd_results

        search_context = "\n\n".join(web_results)
        print_system("Synthèse des résultats web en cours...")

        synthesis_messages = original_messages + [
            {"role": "assistant", "content": clean_text or ""},
            {
                "role": "user",
                "content": (
                    f"Voici les résultats de recherche :\n\n{search_context}\n\n"
                    "En te basant UNIQUEMENT sur ces résultats, réponds de façon "
                    "concise et naturelle en français. Pas de CMD supplémentaire."
                ),
            },
        ]

        synthesized = self.ai.chat(synthesis_messages, stream=False) or ""
        if synthesized:
            # On retire les éventuels CMD que l'IA pourrait quand même générer
            synth_text, _ = self.executor.process_response(synthesized)
            return synth_text, other_results

        return clean_text, other_results

    def _build_full_response(self, text: str, cmd_results: list[str]) -> str:
        """
        Combine le texte de l'IA avec les résultats des commandes.

        Les actions PC (open_app, volume...) retournent des confirmations courtes.
        Les actions vision retournent de longues descriptions à vocaliser.
        On les ajoute au texte principal pour que Boxy les lise.
        """
        parts = [text] if text else []

        for result in cmd_results:
            # Ignore les confirmations très courtes (ex: "chrome lancé.")
            # mais inclut les descriptions longues (vision, commandes shell)
            if len(result) > 40:
                parts.append(result)

        return " ".join(parts).strip()

    def _handle_command(self, command: str) -> None:
        """
        Route une commande slash vers le bon handler.
        Les commandes UI-only (/theme, /export, /historique, /compact) sont
        interceptées en amont par MainWindow._handle_ui_command() et ne
        parviennent jamais ici.
        """
        parts = command.strip().split(None, 1)   # ["/cmd", "args optionnel"]
        cmd   = parts[0].lower()
        args  = parts[1].strip() if len(parts) > 1 else ""

        # ── Système ──────────────────────────────────────────────────────

        if cmd == "/quitter":
            print_separator()
            farewell = f"Bonne journée, {Config.USER_NAME}. Mise en veille."
            print_jarvis(farewell)
            self.voice.speak(farewell)
            self.memory.save_conversation()
            self.voice.cleanup()
            raise SystemExit(0)

        elif cmd == "/aide":
            lines = ["Commandes disponibles :"]
            for name, desc in self.COMMANDS.items():
                lines.append(f"  {name:<16} {desc}")
            msg = "\n".join(lines)
            self._emit_response(msg)

        elif cmd == "/memoire":
            memories = self.memory.get_all_memories()
            if memories:
                lines = ["Mémoire long-terme :"]
                for key, value in memories.items():
                    lines.append(f"  {key} → {value}")
                self._emit_response("\n".join(lines))
            else:
                msg = "Aucune information mémorisée pour le moment."
                self._emit_response(msg)
                self.voice.speak(msg)

        elif cmd == "/clear":
            self.memory.clear_short_term()
            msg = "Historique effacé."
            self._emit_response(msg)
            self.voice.speak(msg)

        elif cmd == "/status":
            self._show_status()

        elif cmd == "/voix":
            enabled = self.voice.toggle()
            state = "activée" if enabled else "désactivée"
            msg = f"Synthèse vocale {state}."
            self._emit_response(msg)
            if enabled:
                self.voice.speak(msg)

        elif cmd == "/ecoute":
            if not self.voice.is_enabled:
                self._emit_response("La voix est désactivée. Tapez /voix pour l'activer.")
                return
            text = self.voice.listen()
            if text:
                self._emit_user_message(f"(vocal) {text}")
                self._chat_with_ai(text)
            else:
                self._emit_response("Je n'ai rien détecté.")

        # ── Actions rapides ───────────────────────────────────────────────

        elif cmd == "/screenshot":
            success, result = self.executor.execute_action("screenshot")
            msg = f"📸 {result}"
            self._emit_response(msg)
            self.voice.speak("Capture effectuée." if success else result)

        elif cmd == "/volume":
            if args.isdigit():
                val = max(0, min(100, int(args)))
                success, result = self.executor.execute_action("volume_set", value=val)
                msg = f"🔊 Volume → {val}%"
                self._emit_response(msg)
                self.voice.speak(msg)
            else:
                self._emit_response("Usage : /volume 50  (0-100)")

        elif cmd == "/recherche":
            if not args:
                self._emit_response("Usage : /recherche météo Paris")
                return
            self._emit_response(f"🔍 Recherche : {args}")
            self._chat_with_ai(f"cherche : {args}")

        elif cmd == "/note":
            if not args:
                self._emit_response("Usage : /note Texte de la note")
                return
            import os
            from datetime import datetime
            from pathlib import Path
            notes_dir = Path(os.path.expanduser("~")) / "Desktop"
            notes_file = notes_dir / "boxy_notes.txt"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            line = f"[{ts}] {args}\n"
            try:
                notes_file.parent.mkdir(parents=True, exist_ok=True)
                with open(notes_file, "a", encoding="utf-8") as f:
                    f.write(line)
                msg = f"📝 Note ajoutée dans boxy_notes.txt"
                self._emit_response(msg)
                self.voice.speak("Note enregistrée.")
            except Exception as e:
                self._emit_response(f"⚠ Erreur note : {e}")

        elif cmd == "/clipboard":
            success, result = self.executor.execute_action("read_clipboard")
            if success:
                self._emit_response(f"📋 Presse-papiers :\n{result}")
            else:
                self._emit_response(f"⚠ {result}")

        elif cmd == "/timer":
            minutes = 1
            if args:
                try:
                    minutes = max(1, int(float(args)))
                except ValueError:
                    self._emit_response("Usage : /timer 5  (minutes)")
                    return
            self._start_timer(minutes)

        # ── Interface (interceptées par l'UI, fallback terminal) ──────────

        elif cmd in ("/theme", "/export", "/historique", "/compact"):
            self._emit_response(f"Commande '{cmd}' disponible uniquement dans l'interface graphique.")

        else:
            msg = f"Commande inconnue : '{cmd}'. Tapez /aide."
            self._emit_response(msg)
            self.voice.speak(msg)

    def _start_timer(self, minutes: int) -> None:
        """Lance un timer dans un thread daemon. Vocalise l'alarme à la fin."""
        import threading

        def _run():
            import time
            self._emit_response(f"⏱ Timer {minutes} min lancé.")
            time.sleep(minutes * 60)
            msg = f"Timer {minutes} minute{'s' if minutes > 1 else ''} écoulé !"
            self._emit_response(f"🔔 {msg}")
            self.voice.speak(msg)

        threading.Thread(target=_run, daemon=True, name=f"timer-{minutes}m").start()

    def _show_status(self) -> None:
        import platform
        print_separator()
        console.print("[bold cyan]Statut système :[/bold cyan]")
        console.print(f"  Provider IA    : [cyan]{self.ai.provider_name}[/cyan]")
        console.print(f"  Voix           : [cyan]{'ON' if self.voice.is_enabled else 'OFF'}[/cyan]")
        console.print(f"  Mode vocal     : [cyan]{Config.VOICE_MODE}[/cyan]")
        console.print(f"  Modèle Whisper : [cyan]{Config.WHISPER_MODEL}[/cyan]")
        console.print(f"  OS             : [cyan]{platform.system()} {platform.release()}[/cyan]")
        print_separator()

    def run(self) -> None:
        """Boucle principale — mode vocal ou texte selon config."""
        print_separator()
        greeting = f"Bonjour, {Config.USER_NAME}. Tous les systèmes sont opérationnels."
        print_jarvis(greeting)
        self.voice.speak(greeting)

        if self.voice.is_enabled:
            print_jarvis("Mode vocal actif. ESPACE pour parler, ESC pour passer en mode texte.")
        else:
            print_jarvis("Tapez votre message. /aide pour les commandes.")
        print_separator()

        while True:
            try:
                if self.voice.is_enabled:
                    self._voice_loop()
                else:
                    self._text_loop()
            except KeyboardInterrupt:
                print()
                print_separator()
                farewell = "Interruption détectée. À bientôt, Sir."
                print_jarvis(farewell)
                self.voice.speak(farewell)
                self.memory.save_conversation()
                self.voice.cleanup()
                break
            except SystemExit:
                break
            except Exception as e:
                print_error(f"Erreur inattendue : {e}")

    def _voice_loop(self) -> None:
        """
        Un cycle du mode vocal :
        - Attend ESPACE (pression unique)
        - Écoute jusqu'au silence automatique
        - Transcrit et répond
        - Si interrompu pendant la réponse → relance l'écoute immédiatement
        - ESC pour passer en mode texte
        """
        console.print("\n[dim]  ESPACE → parler   ESC → mode texte[/dim]")

        # Attend ESPACE ou ESC
        while True:
            key = keyboard.read_key(suppress=True)
            if key == Config.PTT_KEY:
                break
            elif key == "esc":
                self.voice.toggle()
                print_jarvis("Mode texte activé. Tapez /voix pour revenir au mode vocal.")
                return

        self._emit_status("listening")
        text = self.voice.listen()
        self._emit_status("idle")

        if not text:
            self._emit_response("Je n'ai rien capté.")
            return

        self._emit_user_message(f"(vocal) {text}")

        if text.strip().startswith("/"):
            self._handle_command(text.strip())
            return

        # Répond — si interrompu, relance l'écoute sans attendre ESPACE
        completed = self._chat_with_ai(text)
        if not completed:
            console.print("[dim]  → Interrompu — écoute en cours...[/dim]")
            time.sleep(0.3)  # Laisse le temps de relâcher la touche / finir de parler
            follow_up = self.voice.listen()
            if follow_up:
                print_user(f"(vocal) {follow_up}")
                self._chat_with_ai(follow_up)

    def _text_loop(self) -> None:
        """Un cycle du mode texte — saisie clavier classique."""
        user_input = console.input("\n[bold white]YOU    ▸ [/bold white]")
        if user_input.strip():
            self.process_input(user_input)

    def run_ui(self, input_queue) -> None:
        """
        Boucle spéciale pour le mode interface graphique.

        Au lieu d'attendre une saisie clavier, on écoute une queue
        qui reçoit les messages depuis l'UI (thread-safe).

        Messages attendus : ("text", str) | ("voice", None) | ("quit", None)

        Mode wake word : une boucle permanente tourne en arrière-plan dès le
        démarrage — pas besoin de cliquer quoi que ce soit.
        """
        import queue as q
        import threading

        self._ww_running = False
        self._processing_lock = threading.Lock()

        wake_word_mode = (
            self.voice.is_enabled
            and Config.VOICE_MODE == "wake_word"
            and getattr(self.voice, "_wake_word", None) is not None
        )

        if wake_word_mode:
            # Mode wake word : pas de salutation vocale — Boxy est silencieux
            # et écoute en permanence depuis l'arrière-plan.
            model = Config.WAKE_WORD_MODEL.replace("_", " ").title()
            self._emit_response(
                f"Prêt. Dis « {model} » pour m'activer."
            )
            self._emit_status("idle")

            # Lance la boucle permanente dans un thread daemon
            self._ww_running = True
            ww_thread = threading.Thread(
                target=self._wake_word_loop, daemon=True, name="ww-loop"
            )
            ww_thread.start()
        else:
            # Mode push-to-talk ou voix désactivée : salutation normale
            greeting = f"Bonjour, {Config.USER_NAME}. Tous les systèmes sont opérationnels."
            self._emit_response(greeting)
            self.voice.speak(greeting)
            self._emit_status("idle")

        while True:
            try:
                kind, data = input_queue.get(timeout=0.1)

                if kind == "quit":
                    self._ww_running = False
                    self.memory.save_conversation()
                    self.voice.cleanup()
                    break

                elif kind == "text":
                    if data.strip():
                        self._emit_user_message(data)
                        self.process_input(data)

                elif kind == "voice":
                    # Déclenchement manuel (bouton mic / hotkey global)
                    # En mode wake word : ignore si la boucle traite déjà une commande
                    if self._processing_lock.locked():
                        continue
                    self._emit_status("listening")
                    text = self.voice._stt.listen_and_transcribe() if wake_word_mode else self.voice.listen()
                    self._emit_status("idle")
                    if text:
                        self._emit_user_message(f"(vocal) {text}")
                        self._chat_with_ai(text)
                    else:
                        self._emit_response("Je n'ai rien capté.")

            except q.Empty:
                continue
            except Exception as e:
                print_error(f"Erreur UI loop : {e}")

    def _wake_word_loop(self) -> None:
        """
        Boucle permanente — écoute le wake word en continu depuis le démarrage.

        Tourne dans un thread daemon séparé.
        Cycle : attente wake word → "Oui ?" → écoute commande → traitement → recommence
        """
        import time
        print_system("Wake word — écoute permanente démarrée.")

        while self._ww_running:
            try:
                # 1. Attend le mot-clé (bloquant — utilise le micro en continu)
                self._emit_status("idle")
                self.voice._wake_word.wait_for_wake_word()

                if not self._ww_running:
                    break

                # 2. Wake word détecté → verrouille pour éviter les conflits
                with self._processing_lock:
                    self._emit_status("listening")
                    print_system("Wake word détecté !")

                    # Confirmation vocale courte
                    self.voice.speak("Oui ?")

                    # 3. Écoute et transcrit la commande
                    text = self.voice._stt.listen_and_transcribe()
                    self._emit_status("idle")

                    if text:
                        self._emit_user_message(f"(vocal) {text}")
                        self._chat_with_ai(text)
                    else:
                        # Rien capté après le wake word → retour silencieux
                        pass

            except Exception as e:
                if self._ww_running:
                    print_error(f"Wake word loop — erreur : {e}")
                    time.sleep(1)  # Pause avant de réessayer