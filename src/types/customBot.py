from discord.ext import commands
from pymongo.asynchronous.collection import AsyncCollection

try:
    from types.db import database_model
except ImportError:
    import sys
    from pathlib import Path
    
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    
    from src.types.db import database_model


class CustomClient(commands.Bot):
    collection: AsyncCollection[database_model] | None
