import discord
from discord.ext import commands
import fnc_embed
from fnc_embed import simple_embed

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="-", intents=intents) # choix du prefix
intents.message_content = True

async def example(ctx):
    embed = simple_embed(
        f"Hello!",
        f"this is an example embed !",
        color="vert"
    )
    await ctx.send(embed=embed)


bot.run(os.getenv("BOT_TOKEN"))