from discord.ext import commands

try:
    from ..fuite.fuite import get_liste_fuite
except ImportError:
    # Allow running this file directly in debug mode.
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.fuite.fuite import get_liste_fuite


def setup_handlers(client: commands.Bot) -> None:
    @client.event
    async def on_ready() -> None:
        for guild in client.guilds:
            client.tree.copy_global_to(guild=guild)
            await client.tree.sync(guild=guild)
        print(f"bot pret : {client.user}")

    @client.event
    async def on_error(event, *args, **kwargs) -> None:
        print(event)
