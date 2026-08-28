import asyncio
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from pymongo.results import DeleteResult, UpdateResult

try:
    from ..components.embeds import leak_embed
    from ..fuite.fuite import get_leak, read_leak_list
    from ..types.customBot import CustomClient
    from ..types.fuite import ArticlesResponse
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.components.embeds import leak_embed
    from src.fuite.fuite import get_leak, read_leak_list
    from src.types.customBot import CustomClient
    from src.types.fuite import ArticlesResponse


class Fuite(commands.Cog):
    def __init__(self, client: CustomClient):
        self.client = client

    @app_commands.command(name="lastleak", description="Get last leak")
    async def lastLeak(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Veuillez patienter...")

        try:
            data: ArticlesResponse | None = await read_leak_list()

            if data is None or not data.articles:
                await interaction.edit_original_response(
                    content="Une erreur est survenu !"
                )
                await asyncio.sleep(5)
                await interaction.delete_original_response()
                return

            first_leak = data.articles[0]

            embed = leak_embed(
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

    @app_commands.command(
        name="setupchannel", description="Setup your new leak channel"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_channel_leak(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        await interaction.response.send_message(
            content="Ajout en cours veuillez patienter", ephemeral=True
        )

        result: UpdateResult = await self.client.collection.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"channel_id": channel.id}},
            upsert=True,
        )

        if result.acknowledged and (
            result.modified_count > 0 or result.upserted_id is not None
        ):
            await interaction.edit_original_response(content="✅ ajout reussis !")
        else:
            await interaction.edit_original_response(
                content="😓 une erreur c'est produite"
            )

    @app_commands.command(name="unlinkchannel", description="Unlink your leak channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def unlink_channel_leak(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            content="Suppression en cours ...", ephemeral=True
        )

        result: DeleteResult = await self.client.collection.delete_one(
            {"guild_id": interaction.guild.id}
        )

        if result.acknowledged and result.deleted_count > 0:
            await interaction.edit_original_response(content="✅ suppression reussis !")
        else:
            await interaction.edit_original_response(
                content="😓 une erreur c'est produite"
            )

    @app_commands.command(
        name="leaks", description="Get All leaks happend in a year (default this year)"
    )
    async def all_leaks(
        self,
        interaction: discord.Interaction,
        year: Optional[int] = None,  # noqa: UP045
    ) -> None:

        if year >= 9999:
            await interaction.response.send_message(content="ABUSE MEC !")
            return

        current_year: int = datetime.now().year  # noqa: DTZ005

        if year > current_year or year < 2016:
            await interaction.response.send_message(
                content=f"Aucune fuite disponible pour l'année : {year}"
            )
            return

        await interaction.response.send_message(content="Veuillez patientier ...")
        if year is None or year == current_year:
            data: ArticlesResponse | None = await read_leak_list()
            return

        data: ArticlesResponse | None = await get_leak(year=year)
        if data is None:
            await interaction.edit_original_response("😓 Une erreur est survenu !")
            await asyncio.wait(5)
            await interaction.delete_original_response()
            return

        if data.stats.count == 0:
            await interaction.edit_original_response(
                f"Aucune fuite trouvé pour l'année : {year}"
            )
            return
            
        


async def setup(client: CustomClient) -> None:
    await client.add_cog(Fuite(client))
