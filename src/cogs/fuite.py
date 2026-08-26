import asyncio

import discord
from discord import app_commands
from discord.ext import commands

try:
    from ..components.embeds import fuite_embed
    from ..fuite.fuite import read_liste_fuite
    from ..types.fuite import ArticlesResponse
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.components.embeds import fuite_embed
    from src.fuite.fuite import read_liste_fuite
    from src.types.fuite import ArticlesResponse


class Fuite(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="lastleak", description="Get last leak")
    async def lastLeak(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Veuillez patienter...")

        try:
            data: ArticlesResponse | None = await read_liste_fuite()

            if data is None or not data.articles:
                await interaction.edit_original_response(
                    content="Une erreur est survenu !"
                )
                await asyncio.sleep(5)
                await interaction.delete_original_response()
                return

            first_leak = data.articles[0]

            embed = fuite_embed(
                title=first_leak.title,
                url=first_leak.shortUrl,
                logo=first_leak.logo,
                volume=first_leak.dataVolumeGb,
                date=first_leak.date,
                status=first_leak.breachStatus,
                affected_count=first_leak.affectedCount,
                data_types=first_leak.dataTypes,
            )

            await interaction.edit_original_response(content="", embed=embed)

        except Exception as e:  # noqa: BLE001
            import traceback

            traceback.print_exc()
            await interaction.edit_original_response(content=f"Erreur: {e}")


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Fuite(client))
