from pydantic import BaseModel


class database_model(BaseModel):
    _id: int
    channel_id: int
    guild_id: int
