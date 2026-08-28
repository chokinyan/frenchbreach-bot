import discord
from discord.ext import commands


def setup_handlers(client: commands.Bot) -> None:
    @client.event
    async def on_ready() -> None:
        for guild in client.guilds:
            client.tree.copy_global_to(guild=guild)
            await client.tree.sync(guild=guild)
        print(f"bot pret : {client.user}")

    @client.event
    async def on_error(event, *args, **kwargs) -> None:
        print(f"Event error : {event}\n\targ : {args}\n\tkwargs : {kwargs}")

    @client.tree.error
    async def on_app_command_error(
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            message = f"Cooldown actif. Réessaye dans {error.retry_after:.2f}s."
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        else:
            print(f"Unhandled slash command error: {error}")
