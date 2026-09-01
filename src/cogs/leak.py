import asyncio

import discord
import mysql.connector
from discord import app_commands
from discord.ext import commands

try:
    from ..components.embeds import LeakListView, leak_embed
    from ..leak.api import FrenchBreachesError, FrenchBreachesRateLimitError
    from ..types.customBot import CustomClient
    from ..types.leak import secteur_autocomplete
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.components.embeds import LeakListView, leak_embed
    from src.leak.api import FrenchBreachesError, FrenchBreachesRateLimitError
    from src.types.customBot import CustomClient
    from src.types.leak import secteur_autocomplete


class LeakCog(commands.Cog):
    def __init__(self, client: CustomClient) -> None:
        self.client = client

    @app_commands.command(name="lastleak", description="Récupère la dernière fuite")
    async def last_leak(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Veuillez patienter...")

        try:
            leaks = await self.client.leak_client.latest(limit=1)

            if not leaks:
                await interaction.edit_original_response(
                    content="😓 Une erreur est survenue !"
                )
                await asyncio.sleep(5)
                await interaction.delete_original_response()
                return

            detail = await self.client.leak_client.detail(leaks[0].id)
            # /detail sert seulement au logo + à la bannière. On garde la
            # description courte de /dernieres (résumé condensé, la version
            # longue de /detail est trop verbeuse pour un embed).
            embed = leak_embed(detail or leaks[0], description=leaks[0].description)

            await interaction.edit_original_response(content=None, embed=embed)

        except FrenchBreachesRateLimitError as e:
            await interaction.edit_original_response(
                content=f"😓 Trop de requêtes, réessaie dans {e.retry}s !"
            )
        except FrenchBreachesError:
            await interaction.edit_original_response(
                content="😓 Une erreur est survenue !"
            )
        except Exception:  # noqa: BLE001
            self.client.logger["api"].exception("Erreur inattendue dans /lastleak")
            await interaction.edit_original_response(
                content="😓 Une erreur est survenue !"
            )

    @app_commands.command(
        name="setupchannel",
        description="Configure le salon où poster les nouvelles fuites",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_channel_leak(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        await interaction.response.send_message(
            content="Ajout en cours, veuillez patienter...", ephemeral=True
        )

        guild_id = channel.guild.id
        channel_id = channel.id
        try:
            async with self.client.db_lock:
                cursor = await self.client.mysql_client.cursor()
                try:
                    await cursor.execute(
                        f"INSERT INTO `{self.client.guilds_table}` "
                        "(guilds_id, auto_send_channel) VALUES (%s, %s) "
                        "ON DUPLICATE KEY UPDATE auto_send_channel = %s",
                        (guild_id, channel_id, channel_id),
                    )
                    await self.client.mysql_client.commit()
                finally:
                    await cursor.close()
        except mysql.connector.Error:
            self.client.logger["database"].exception("Erreur SQL dans /setupchannel")
            await interaction.edit_original_response(
                content="😓 Une erreur s'est produite"
            )
            return

        # rowcount vaut 0/1/2 selon insert/update/no-op : tous des succès.
        await interaction.edit_original_response(content="✅ Ajout réussi !")

    @app_commands.command(
        name="unlinkchannel",
        description="Arrête de poster les nouvelles fuites dans ce serveur",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def unlink_channel_leak(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            content="Suppression en cours...", ephemeral=True
        )

        guild_id = interaction.guild_id

        try:
            async with self.client.db_lock:
                cursor = await self.client.mysql_client.cursor()
                try:
                    await cursor.execute(
                        f"DELETE FROM `{self.client.guilds_table}` "
                        "WHERE guilds_id = %s",
                        (guild_id,),
                    )
                    await self.client.mysql_client.commit()
                    deleted = cursor.rowcount
                finally:
                    await cursor.close()
        except mysql.connector.Error:
            self.client.logger["database"].exception("Erreur SQL dans /unlinkchannel")
            await interaction.edit_original_response(
                content="😓 Une erreur s'est produite"
            )
            return

        if deleted:
            await interaction.edit_original_response(
                content="✅ Suppression réussie !"
            )
        else:
            await interaction.edit_original_response(
                content="😓 Aucun salon n'était configuré."
            )

    @app_commands.command(name="leaks", description="Liste des dernières fuites")
    @app_commands.describe(
        secteur="Secteur voulu (optionnel)",
        nombre="Nombre de fuites voulu (max : 25, défaut : 10, optionnel)",
    )
    @app_commands.autocomplete(secteur=secteur_autocomplete)
    async def all_leaks(
        self,
        interaction: discord.Interaction,
        secteur: str | None = None,
        nombre: int | None = None,
    ) -> None:
        await interaction.response.send_message(content="Veuillez patienter...")

        if nombre is None:
            nombre = 10

        if nombre < 1 or nombre > 25:
            await interaction.edit_original_response(
                content=f"Le nombre doit être entre 1 et 25 (reçu : {nombre})"
            )
            return

        try:
            leaks = await self.client.leak_client.latest(limit=nombre, sector=secteur)

            if not leaks:
                message = (
                    f"Aucune fuite trouvée pour le secteur : {secteur}"
                    if secteur
                    else "Aucune fuite trouvée."
                )
                await interaction.edit_original_response(content=message)
                return

            view = LeakListView(
                leaks=leaks,
                author=interaction.user,
                leak_client=self.client.leak_client,
            )
            await interaction.edit_original_response(
                content=None, embed=await view.current_embed(), view=view
            )
            view.message = await interaction.original_response()

        except FrenchBreachesRateLimitError as e:
            await interaction.edit_original_response(
                content=f"⏳ Trop de requêtes, réessaie dans {e.retry}s"
            )
        except FrenchBreachesError as e:
            await interaction.edit_original_response(content=f"Erreur API : {e}")
        except Exception:  # noqa: BLE001
            self.client.logger["api"].exception("Erreur inattendue dans /leaks")
            await interaction.edit_original_response(
                content="😓 Une erreur est survenue !"
            )


async def setup(client: CustomClient) -> None:
    await client.add_cog(LeakCog(client))
