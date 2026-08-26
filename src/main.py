import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

import components.loadsCogs as c
import fuite.fuite as f
import handlers.handlers as h

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="*", intents=intents)


async def main() -> None:
    load_dotenv()
    h.setup_handlers(client)
    await c.load_extensions(client)
    await f.write_liste_fuite()
    await client.start(os.getenv("TOKEN"))


if __name__ == "__main__":
    asyncio.run(main())
