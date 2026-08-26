import asyncio
import json
from datetime import datetime
from pathlib import Path

import httpx
from pydantic import ValidationError

try:
    from ..types.fuite import ArticlesResponse
except ImportError:
    # Allow running this file directly in debug mode.
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.types.fuite import ArticlesResponse

base_url: str = "https://frenchbreaches.com/api/articles_api.php?year="
json_path: Path = Path(__file__).resolve().parents[1] / "json" / "data.json"
"""
{
    "articles" : Array<
        {
            "id" : str,
            "title" : str,
            "description" : str,
            "date" : str,
            "source" : str,
            "logo" : str,
            "slug" : str,
            "status" : str,
            "is_scheduled" : int,
            "published_at" : ?,
            "seo_title" : str,
            "google_index_hash" : str,
            "dataTypes" : Array<str>,
            "affectedCount" : int,
            "dataVolumeGb" : ?,
            "headerImage" : str,
            "lastModified" : str,
            "breachStatus" : str,
            "shortUrl" : str
        }
    >,
    "pagination" : {
        "page" : int,
        "limit" : int,
        "total" : int,
        "pages" : int
    },
    "stats" : {
        "count" : int
    }
}
"""


async def get_liste_fuite(year: int = datetime.now().year) -> ArticlesResponse | None:  # noqa: DTZ005
    url: str = base_url + str(year)
    client = httpx.AsyncClient()

    rep = await client.get(url)

    await client.aclose()

    try:
        data: ArticlesResponse = ArticlesResponse.model_validate(rep.json())
    except ValidationError as e:
        print(f"erreur lors du parsing des data : {e}")
        return None

    return data


async def write_liste_fuite() -> bool:
    info: ArticlesResponse | None = await get_liste_fuite()
    if info is None:
        return False
    json_path.open("w").close()
    string_info: str = info.model_dump_json().encode('utf-8')
    await asyncio.to_thread(json_path.write_bytes, string_info)
    print("fichier crée avec succès")
    return True


async def read_liste_fuite() -> ArticlesResponse | None:
    if not (json_path.exists()):
        success: bool = await write_liste_fuite()
        if success is None:
            return None
    try:
        data: ArticlesResponse = ArticlesResponse.model_validate(
            json.loads(json_path.read_text("utf-8"))
        )
    except ValidationError as e:
        print(f"cant read correct data : {e}")
        return None
    return data