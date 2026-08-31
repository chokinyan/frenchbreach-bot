from typing import Literal

import discord
from discord.ext import commands

try:
    from ..types.customBot import CustomClient
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.types.customBot import CustomClient


class Sync(commands.Cog):
    """Commande texte réservée au propriétaire pour (re)synchroniser l'arbre
    des slash commands à la demande, sans redémarrer le bot.

        *sync         -> sync global (toutes les guildes, ~qq minutes)
        *sync ~       -> sync la guilde courante (instantané)
        *sync *       -> copie le global vers la guilde courante puis sync
        *sync ^       -> vide les commandes de la guilde courante
        *sync 123 456 -> sync ces guildes précises
    """

    def __init__(self, client: CustomClient) -> None:
        self.client = client

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync(
        self,
        ctx: commands.Context,
        guilds: commands.Greedy[discord.Object],
        spec: Literal["~", "*", "^"] | None = None,
    ) -> None:
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            cible = "cette guilde" if spec else "global"
            await ctx.send(f"✅ {len(synced)} commande(s) synchronisée(s) ({cible}).")
            return

        done = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                done += 1
        await ctx.send(f"✅ Arbre synchronisé sur {done}/{len(guilds)} guilde(s).")


async def setup(client: CustomClient) -> None:
    await client.add_cog(Sync(client))
