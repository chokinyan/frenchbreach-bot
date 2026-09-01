import discord
from discord import app_commands
from pydantic import BaseModel, Field

SECTORS: list[str] = [
    "commerce",
    "secteur-public",
    "education",
    "sante",
    "technologie",
    "industrie",
    "telecom-media",
    "finance",
    "transport",
    "telecom",
]


async def secteur_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=secteur, value=secteur)
        for secteur in SECTORS
        if current.lower() in secteur.lower()
    ][:25]


class Leak(BaseModel):
    id: str
    title: str
    description: str
    date: str
    affected_count: int = 0
    data_volume_gb: float | None = None
    source: str | None = None
    sector: str | None = None
    data_types: list[str] = Field(default_factory=list)
    url: str
    short_url: str | None = None


class DetailLeak(Leak):
    header_image: str | None = None
    logo: str | None = None
    last_modified: str | None = None
    status: str | None = None
