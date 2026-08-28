from pathlib import Path

try:
    from ..types.customBot import CustomClient
except ImportError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.types.customBot import CustomClient

COGS_DIR: Path = Path(__file__).resolve().parents[1] / "cogs"


async def load_extensions(client: CustomClient) -> None:
    for path in COGS_DIR.iterdir():
        if path.suffix == ".py":
            await client.load_extension(f"cogs.{path.stem}")
