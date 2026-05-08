"""
ai/ollama_provider.py — Provider pour Ollama (IA locale).

Ollama fait tourner des modèles LLM sur ta machine.
Avantages : gratuit, privé, fonctionne sans internet.
Inconvénient : nécessite une bonne RAM/GPU.
"""

import ollama
from ai.base_provider import BaseAIProvider
from utils.logger import console, print_error


class OllamaProvider(BaseAIProvider):
    """Connexion à Ollama pour les modèles IA locaux."""

    def __init__(self, model: str, base_url: str):
        self.model    = model
        self.base_url = base_url
        self._client  = ollama.Client(host=base_url)

        # Options de performance envoyées à chaque requête Ollama.
        # num_ctx   : fenêtre de contexte (tokens). 2048 suffit pour
        #             une conversation normale et économise beaucoup de RAM.
        # num_thread: threads CPU alloués à l'inférence.
        #             Laisser 2 threads libres pour le reste du système.
        import os
        cpu_count   = os.cpu_count() or 4
        self._options = {
            "num_ctx":    int(os.getenv("OLLAMA_CONTEXT", "2048")),
            "num_thread": max(2, cpu_count - 2),
            "temperature": 0.7,
        }

    @property
    def name(self) -> str:
        return f"Ollama ({self.model})"

    def is_available(self) -> bool:
        """Teste si Ollama est accessible via une requête HTTP directe."""
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=3.0)
            return response.status_code == 200
        except Exception:
            return False

    def chat(self, messages: list[dict], stream: bool = True,
             token_callback=None) -> str:
        """
        Envoie les messages à Ollama et retourne la réponse.

        Si stream=True, affiche chaque token au fur et à mesure.
        token_callback(token) est appelé pour chaque token si fourni.
        """
        try:
            if stream:
                return self._chat_stream(messages, token_callback)
            else:
                return self._chat_sync(messages)
        except ollama.ResponseError as e:
            print_error(f"Ollama — erreur de réponse : {e}")
            return "Je rencontre une difficulté technique, Sir."
        except Exception as e:
            print_error(f"Ollama — erreur inattendue : {e}")
            return "Connexion au modèle impossible pour le moment."

    def _chat_stream(self, messages: list[dict], token_callback=None) -> str:
        """Mode streaming — affiche les tokens un par un."""
        full_response = ""

        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        console.print(f"[dim]{timestamp}[/dim] [bold cyan]BOXY ▸[/bold cyan] ", end="")

        for chunk in self._client.chat(
            model=self.model,
            messages=messages,
            stream=True,
            options=self._options
        ):
            token = chunk["message"]["content"]
            if token:
                console.print(token, end="", markup=False)
                full_response += token
                if token_callback:
                    token_callback(token)

        console.print()
        return full_response

    def _chat_sync(self, messages: list[dict]) -> str:
        response = self._client.chat(
            model=self.model,
            messages=messages,
            stream=False,
            options=self._options
        )
        msg = response.get("message", {}) if isinstance(response, dict) else response.message
        return msg.get("content", "") if isinstance(msg, dict) else msg.content