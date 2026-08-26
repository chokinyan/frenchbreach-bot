#!/usr/bin/python3

import discord
from discord.ext import commands
from discord.ui import Button, View



### primary (bleu)
### secondary (gris)
### success (vert)
### danger (rouge)

def color2hex(color):
    if color == "rouge":
        color = 0xFF0000
    elif color == "bleu":
        color = 0x0D00FF
    elif color == "orange":
        color = 0xFF8000
    elif color == "jaune":
        color = 0xFFE600
    elif color == "vert":
        color = 0x40FF00
    elif color == "noir":
        color = 0x000000
    elif color == "blanc":
        color = 0xFFFFFF
    
    return color
        
def color2bouton(color):
    if color == "rouge":
        color = discord.ButtonStyle.red
    elif color == "bleu":
        color = discord.ButtonStyle.blurple
    elif color == "vert":
        color = discord.ButtonStyle.green
    elif color == "noir":
        color = discord.ButtonStyle.grey

    return color



def simple_embed(title, description, color):
    embed = discord.Embed(
        title=f"**{title}**",
        description=f"{description}",
        color=color2hex(color),
    )
    return embed    
    





###############################################################################



class ComplexEmbed3(discord.ui.View):
    def __init__(self, admin_role_id: int, mod_role_id: int, buttons: list):
        super().__init__(timeout=None)  # persistance
        self.admin_role_id = admin_role_id
        self.mod_role_id = mod_role_id

        for i, btn in enumerate(buttons):
            custom_id = btn.get("custom_id") or f"btn_{i}"

            button = discord.ui.Button(
                label=btn.get("label", "Bouton"),
                style=color2bouton(btn.get("color", "bleu")),
                custom_id=custom_id
            )

            async def callback(interaction: discord.Interaction, btn_config=btn):
                # Vérification du rôle minimum
                min_role_id = btn_config.get("minimum_role", self.admin_role_id)
                min_role = interaction.guild.get_role(min_role_id)
                if min_role not in interaction.user.roles:
                    await interaction.response.send_message("🚫 Tu n’as pas la permission.", ephemeral=True)
                    return

                # Appel de la fonction callback du bouton
                if "callback" in btn_config and callable(btn_config["callback"]):
                    await btn_config["callback"](interaction, btn_config)

                # Mise à jour de l'embed
                embed = discord.Embed(
                    title=btn_config.get("embed_title", "État"),
                    description=btn_config.get("embed_text", ""),
                    color=color2hex(btn_config.get("embed_color", "bleu"))
                )
                await interaction.message.edit(embed=embed, view=self)
                await interaction.response.defer()

            button.callback = callback
            self.add_item(button)