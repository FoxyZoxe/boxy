"""
config.py — Configuration centrale de Boxy.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent


class Config:
    # --- IA ---
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "ollama")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral:latest")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # --- Mémoire ---
    MAX_HISTORY_LENGTH: int = int(os.getenv("MAX_HISTORY_LENGTH", "20"))
    MEMORY_FILE: Path = BASE_DIR / "data" / "memory.json"
    CONVERSATIONS_DIR: Path = BASE_DIR / "data" / "conversations"

    # --- Personnalité ---
    ASSISTANT_NAME: str = os.getenv("ASSISTANT_NAME", "Boxy")
    USER_NAME: str      = os.getenv("USER_NAME", "Sir")

    @classmethod
    def _build_system_prompt(cls) -> str:
        import os
        # Chemins avec / (valides sur Windows, sans problème d'échappement JSON)
        home    = os.path.expanduser("~").replace("\\", "/")
        desktop = f"{home}/Desktop"
        return f"""Tu es {cls.ASSISTANT_NAME}, l'IA de {cls.USER_NAME}. Français. 1-2 phrases max. Jamais de listes. Jamais de présentation.
Pour agir sur le PC : [CMD:{{"action":"...", "clé":"val"}}] — seulement si demande explicite. Chemins : / obligatoire. Bureau={desktop}

{cls.USER_NAME}: ça va ?
{cls.ASSISTANT_NAME}: Ça va. Et toi ?

{cls.USER_NAME}: bonjour
{cls.ASSISTANT_NAME}: Salut.

{cls.USER_NAME}: que peux-tu faire ?
{cls.ASSISTANT_NAME}: Demande ce que tu veux, je m'en occupe.

{cls.USER_NAME}: ouvre chrome
{cls.ASSISTANT_NAME}: [CMD:{{"action":"open_app","name":"chrome"}}]

{cls.USER_NAME}: mets le volume à 50
{cls.ASSISTANT_NAME}: [CMD:{{"action":"volume_set","value":50}}]

{cls.USER_NAME}: cherche la météo
{cls.ASSISTANT_NAME}: [CMD:{{"action":"web_search","query":"météo aujourd'hui"}}]

{cls.USER_NAME}: crée un fichier test sur le bureau
{cls.ASSISTANT_NAME}: [CMD:{{"action":"save_file","path":"{desktop}/test.txt","content":""}}]"""

    SYSTEM_PROMPT: str = ""  # Initialisé dynamiquement après (voir bas de classe)

    # --- Vision (Phase 5) ---
    VISION_PROVIDER: str = os.getenv("VISION_PROVIDER", "ollama")
    VISION_MODEL: str    = os.getenv("VISION_MODEL", "moondream")

    # --- Voix (Phase 2) ---
    VOICE_ENABLED: bool = os.getenv("VOICE_ENABLED", "true").lower() == "true"
    TTS_VOICE: str = os.getenv("TTS_VOICE", "en-GB-RyanNeural")
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "fr")         # Langue de transcription Whisper (fr, en, es…)
    VOICE_MODE: str = os.getenv("VOICE_MODE", "push_to_talk")  # "push_to_talk" ou "wake_word"
    PTT_KEY: str = os.getenv("PTT_KEY", "space")
    WAKE_WORD_MODEL: str = os.getenv("WAKE_WORD_MODEL", "hey_jarvis")  # hey_jarvis | alexa | hey_mycroft | hey_rhasspy
    GLOBAL_HOTKEY: str = os.getenv("GLOBAL_HOTKEY", "ctrl+space")      # Hotkey système pour activer Boxy
    AI_TIMEOUT: int = int(os.getenv("AI_TIMEOUT", "120"))               # Timeout IA en secondes

    # --- Image generation ---
    IMAGE_PROVIDER: str  = os.getenv("IMAGE_PROVIDER", "pollinations")  # "pollinations" ou "openai"
    IMAGE_SAVE_DIR: Path = BASE_DIR / "data" / "images"

    # --- Discord ---
    DISCORD_TOKEN: str   = os.getenv("DISCORD_TOKEN", "")
    DISCORD_CHANNEL: str = os.getenv("DISCORD_CHANNEL", "boxy")  # Nom du channel Discord

    # --- OBS ---
    OBS_HOST: str  = os.getenv("OBS_HOST", "localhost")
    OBS_PORT: int  = int(os.getenv("OBS_PORT", "4455"))
    OBS_PASSWORD: str = os.getenv("OBS_PASSWORD", "")

    @classmethod
    def validate(cls) -> list[str]:
        errors = []
        if cls.AI_PROVIDER not in ("ollama", "openai", "groq"):
            errors.append(
                f"AI_PROVIDER invalide : '{cls.AI_PROVIDER}'. "
                "Valeurs acceptées : ollama, openai, groq."
            )
        if cls.AI_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY est vide alors que AI_PROVIDER=openai.")
        if cls.AI_PROVIDER == "groq" and not cls.GROQ_API_KEY:
            errors.append("GROQ_API_KEY est vide alors que AI_PROVIDER=groq.")
        return errors


# Calcule le system prompt une fois au chargement (après que les env vars soient lues)
Config.SYSTEM_PROMPT = Config._build_system_prompt()