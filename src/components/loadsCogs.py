from pathlib import Path

from discord.ext import commands

COGS_DIR: Path = Path(__file__).resolve().parents[1] / "cogs"


async def load_extensions(client : commands.Bot):
    for path in COGS_DIR.iterdir():
        if path.suffix == ".py":
            await client.load_extension(f"cogs.{path.stem}")