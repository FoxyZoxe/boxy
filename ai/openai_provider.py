"""
ai/openai_provider.py — Provider pour OpenAI et services compatibles (Groq, etc.).

Supporte :
  - OpenAI   : base_url=None         (payant)
  - Groq     : base_url=https://api.groq.com/openai/v1   (GRATUIT)

Groq utilise exactement le même format d'API qu'OpenAI, seule la base_url change.
"""

from openai import OpenAI, APIConnectionError, AuthenticationError, RateLimitError
from ai.base_provider import BaseAIProvider
from utils.logger import console, print_error
from datetime import datetime


class OpenAIProvider(BaseAIProvider):
    """Connexion à l'API OpenAI ou à tout service compatible (Groq, etc.)."""

    def __init__(self, api_key: str, model: str, base_url: str = None):
        self.model = model
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url or None,   # None = OpenAI officiel
        )

    @property
    def name(self) -> str:
        return f"OpenAI ({self.model})"

    def is_available(self) -> bool:
        """Teste la connexion OpenAI avec un appel minimal."""
        try:
            # Liste les modèles disponibles — requête légère
            self._client.models.list()
            return True
        except (APIConnectionError, AuthenticationError):
            return False
        except Exception:
            return False

    def chat(self, messages: list[dict], stream: bool = True,
             token_callback=None) -> str:
        try:
            if stream:
                return self._chat_stream(messages, token_callback)
            else:
                return self._chat_sync(messages)
        except AuthenticationError:
            print_error("Clé OpenAI invalide. Vérifie OPENAI_API_KEY dans .env")
            return "Clé API invalide."
        except RateLimitError as e:
            if "insufficient_quota" in str(e):
                print_error("Quota OpenAI dépassé. Ajoute des crédits sur platform.openai.com/billing")
                return "Quota OpenAI épuisé — recharge les crédits sur platform.openai.com/billing."
            print_error(f"OpenAI — limite de débit : {e}")
            return "Limite de requêtes OpenAI atteinte, réessaie dans un instant."
        except APIConnectionError:
            print_error("Impossible de joindre l'API OpenAI. Vérifie ta connexion.")
            return "Connexion à OpenAI impossible."
        except Exception as e:
            print_error(f"OpenAI — erreur : {e}")
            return "Erreur OpenAI inattendue."

    def _chat_stream(self, messages: list[dict], token_callback=None) -> str:
        full_response = ""
        timestamp = datetime.now().strftime("%H:%M:%S")
        console.print(f"[dim]{timestamp}[/dim] [bold cyan]BOXY ▸[/bold cyan] ", end="")

        with self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True
        ) as stream:
            for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    console.print(token, end="", markup=False)
                    full_response += token
                    if token_callback:
                        token_callback(token)

        console.print()
        return full_response

    def _chat_sync(self, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content