import os

import discord
from discord.ext import commands


def setup_handlers(client: commands.Bot) -> None:
    synced = False

    @client.event
    async def on_ready() -> None:
        nonlocal synced
        if not synced:
            # `on_ready` peut se redéclencher à chaque reconnexion : on ne
            # synchronise qu'une fois pour éviter le rate limit Discord.
            dev_guild = os.getenv("DEV_GUILD_ID")
            if dev_guild:
                # Sync instantané sur un serveur de test.
                guild = discord.Object(id=int(dev_guild))
                client.tree.copy_global_to(guild=guild)
                await client.tree.sync(guild=guild)
            else:
                # Sync global (propagation ~1 h, mais une seule requête).
                await client.tree.sync()
            synced = True
        client.logger["discord"].info(f"bot prêt : {client.user}")

    @client.event
    async def on_error(event, *args, **kwargs) -> None:
        # Appelé depuis un bloc except de discord.py : .exception() capture
        # la stacktrace en cours.
        client.logger["discord"].exception(
            "Event error : %s | args=%s kwargs=%s", event, args, kwargs
        )

    @client.tree.error
    async def on_app_command_error(
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            message = f"Cooldown actif. Réessaye dans {error.retry_after:.2f}s."
        elif isinstance(error, discord.app_commands.MissingPermissions):
            message = "Tu n'as pas la permission d'utiliser cette commande."
        else:
            # Hors bloc except ici : on passe l'exception explicitement.
            client.logger["discord"].error(
                "Unhandled slash command error", exc_info=error
            )
            message = "😓 Une erreur est survenue !"

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
