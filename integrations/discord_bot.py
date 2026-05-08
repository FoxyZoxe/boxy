"""
integrations/discord_bot.py — Bot Discord connecté à Boxy.

Le bot écoute les messages dans un channel Discord et les transmet
à Boxy, puis renvoie la réponse dans Discord.

Setup :
1. Va sur https://discord.com/developers/applications
2. Crée une application → "Bot" → copie le Token
3. Active "Message Content Intent" dans l'onglet Bot
4. Invite le bot : OAuth2 → URL Generator → bot + Send Messages + Read Messages
5. Colle le token dans .env → DISCORD_TOKEN=...
6. Crée un channel nommé "boxy" dans ton serveur

Usage :
  - Écris dans le channel #boxy → Boxy répond
  - Mentionne @Boxy n'importe où → Boxy répond
  - !image <prompt> → génère une image
  - !ecran → analyse l'écran
  - !aide → liste des commandes
"""

import asyncio
import threading
from config import Config
from utils.logger import print_system, print_error


class DiscordBot:
    """Bot Discord qui fait le pont avec Boxy."""

    def __init__(self, jarvis_instance):
        """
        Args:
            jarvis_instance: Instance de Boxy déjà initialisée
        """
        self._jarvis = jarvis_instance
        self._bot    = None
        self._thread = None
        self._loop   = None

    def start(self) -> bool:
        """
        Lance le bot dans un thread séparé.

        Returns:
            True si le démarrage a réussi, False sinon
        """
        if not Config.DISCORD_TOKEN:
            print_error("DISCORD_TOKEN manquant dans .env — bot Discord désactivé.")
            return False

        try:
            import discord
        except ImportError:
            print_error("discord.py non installé : pip install discord.py")
            return False

        self._thread = threading.Thread(target=self._run_bot, daemon=True)
        self._thread.start()
        print_system(f"Bot Discord démarré — channel : #{Config.DISCORD_CHANNEL}")
        return True

    def _run_bot(self) -> None:
        """Point d'entrée du thread Discord."""
        import discord
        from discord.ext import commands

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        intents = discord.Intents.default()
        intents.message_content = True  # Requis pour lire les messages
        intents.members = True

        self._bot = commands.Bot(
            command_prefix="!",
            intents=intents,
            help_command=None  # On gère notre propre !aide
        )

        # ─── Events ────────────────────────────────────────────────

        @self._bot.event
        async def on_ready():
            name = self._bot.user.name
            print_system(f"Discord connecté en tant que : {name}")
            # Change le statut du bot
            await self._bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening,
                    name=f"#{Config.DISCORD_CHANNEL}"
                )
            )

        @self._bot.event
        async def on_message(message):
            # Ignore les messages du bot lui-même
            if message.author == self._bot.user:
                return

            # Répond si :
            # 1. Message dans le channel dédié
            # 2. Bot mentionné dans n'importe quel channel
            is_boxy_channel = message.channel.name == Config.DISCORD_CHANNEL
            is_mentioned = self._bot.user in message.mentions

            if not is_boxy_channel and not is_mentioned:
                # Laisse les commandes ! fonctionner partout
                await self._bot.process_commands(message)
                return

            # Nettoie le contenu (retire la mention du bot)
            content = message.content
            if self._bot.user.mention in content:
                content = content.replace(self._bot.user.mention, "").strip()

            if not content:
                return

            # Montre que le bot est en train de répondre
            async with message.channel.typing():
                response = await self._ask_boxy(content)

            # Envoie la réponse (coupe si trop long pour Discord)
            if len(response) > 2000:
                for chunk in [response[i:i+2000] for i in range(0, len(response), 2000)]:
                    await message.channel.send(chunk)
            else:
                await message.channel.send(response)

            await self._bot.process_commands(message)

        # ─── Commandes Discord ─────────────────────────────────────

        @self._bot.command(name="image")
        async def generate_image(ctx, *, prompt: str):
            """!image <prompt> — Génère une image avec Boxy."""
            await ctx.send(f"🎨 Génération en cours : *{prompt}*...")
            async with ctx.typing():
                response = await self._ask_boxy(f"génère une image de {prompt}")
            await ctx.send(response)

        @self._bot.command(name="ecran")
        async def analyze_screen(ctx):
            """!ecran — Analyse l'écran actuel."""
            await ctx.send("👁️ Analyse de l'écran...")
            async with ctx.typing():
                response = await self._ask_boxy("que vois-tu à l'écran ?")
            await ctx.send(response)

        @self._bot.command(name="aide")
        async def help_cmd(ctx):
            """!aide — Liste des commandes."""
            name = Config.ASSISTANT_NAME
            embed = discord.Embed(
                title=f"◈ {name} — Commandes Discord",
                color=0x00d4ff
            )
            embed.add_field(
                name="Chat",
                value=f"Écris dans #{Config.DISCORD_CHANNEL} ou mentionne @{name}",
                inline=False
            )
            embed.add_field(name="!image <prompt>", value="Génère une image", inline=True)
            embed.add_field(name="!ecran",          value="Analyse l'écran",  inline=True)
            embed.add_field(name="!aide",           value="Cette aide",       inline=True)
            await ctx.send(embed=embed)

        # Lance le bot
        try:
            self._loop.run_until_complete(
                self._bot.start(Config.DISCORD_TOKEN)
            )
        except Exception as e:
            print_error(f"Discord — erreur : {e}")

    async def _ask_boxy(self, text: str) -> str:
        """
        Envoie un message à Boxy et attend la réponse.
        Tourne dans l'event loop asyncio de Discord.
        """
        loop = asyncio.get_event_loop()
        # Boxy est synchrone → on le fait tourner dans un thread executor
        response = await loop.run_in_executor(
            None,
            self._process_sync,
            text
        )
        return response or "Je n'ai pas de réponse pour le moment."

    def _process_sync(self, text: str) -> str:
        """Appelle Boxy de façon synchrone (pour run_in_executor)."""
        try:
            self._jarvis.memory.add_message("user", text)
            messages = self._jarvis.memory.get_messages_for_ai()
            raw = self._jarvis.ai.chat(messages, stream=False)
            clean_text, cmd_results = self._jarvis.executor.process_response(raw)
            full = self._jarvis._build_full_response(clean_text, cmd_results)
            self._jarvis.memory.add_message("assistant", full or "")
            return full
        except Exception as e:
            print_error(f"Discord process error : {e}")
            return "Une erreur s'est produite."

    def stop(self) -> None:
        """Arrête le bot proprement."""
        if self._bot and self._loop:
            asyncio.run_coroutine_threadsafe(self._bot.close(), self._loop)
