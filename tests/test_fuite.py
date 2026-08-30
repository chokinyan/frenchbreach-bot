"""
Suite de tests pour src/fuite/fuite.py.

Exécution :
    pytest tests/test_fuite.py -v

"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from diskcache import Cache

try:
    from ..types.fuite import ArticlesResponse
    from ..fuite import fuite
except ImportError:
    # Allow running this file directly in debug mode.
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.fuite import fuite
    from src.types.fuite import ArticlesResponse


def make_articles_payload(count: int, article_count_field: int | None = None) -> dict[str, Any]:
    articles = [
        {
            "id": str(i),
            "title": f"Fuite {i}",
            "description": f"Description de la fuite {i}",
            "date": "2025-01-01",
            "source": "test-source",
            "logo": "https://example.com/logo.png",
            "slug": f"fuite-{i}",
            "status": "published",
            "is_scheduled": 0,
            "published_at": None,
            "seo_title": f"Fuite {i} - SEO",
            "google_index_hash": "abc123",
            "dataTypes": ["email", "password"],
            "affectedCount": 1000 * (i + 1),
            "dataVolumeGb": None,
            "headerImage": "https://example.com/header.png",
            "lastModified": "2025-01-01",
            "breachStatus": "confirmed",
            "shortUrl": f"https://short.url/{i}",
        }
        for i in range(count)
    ]
    return {
        "articles": articles,
        "pagination": {"page": 1, "limit": 20, "total": count, "pages": 1},
        "stats": {"count": article_count_field if article_count_field is not None else count},
    }


def make_response(count: int, article_count_field: int | None = None) -> ArticlesResponse:
    return ArticlesResponse.model_validate(
        make_articles_payload(count, article_count_field)
    )


class FakeHTTPResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def install_fake_client(monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any] | None) -> None:
    fake_client = MagicMock()
    fake_client.get = AsyncMock(return_value=FakeHTTPResponse(payload or {}))
    fake_client.aclose = AsyncMock(return_value=None)

    def fake_async_client(*args: Any, **kwargs: Any) -> MagicMock:
        return fake_client

    monkeypatch.setattr(fuite.httpx, "AsyncClient", fake_async_client)


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    test_cache = Cache(str(tmp_path / "cache"))
    monkeypatch.setattr(fuite, "cache", test_cache)
    yield test_cache
    test_cache.close()


@pytest.mark.asyncio
async def test_get_leak_returns_valid_data(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = make_articles_payload(count=3)
    install_fake_client(monkeypatch, payload)

    result = await fuite._get_leak(year=2025)

    assert result is not None
    assert result.stats.count == 3
    assert len(result.articles) == 3
    assert result.articles[0].title == "Fuite 0"


@pytest.mark.asyncio
async def test_get_leak_returns_none_on_invalid_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_client(monkeypatch, payload=None)

    result = await fuite._get_leak(year=2025)

    assert result is None


@pytest.mark.asyncio
async def test_write_then_read_leak_list_uses_cache(
        monkeypatch: pytest.MonkeyPatch, isolated_cache: Cache
) -> None:
    payload = make_articles_payload(count=2)
    install_fake_client(monkeypatch, payload)

    written = await fuite.write_leak_list(year=2025)
    assert written is not None
    assert written.stats.count == 2

    def broken_client(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("read_leak_list n'aurait pas dû appeler le réseau")

    monkeypatch.setattr(fuite.httpx, "AsyncClient", broken_client)

    read_back = await fuite.read_leak_list(year=2025)

    assert read_back is not None
    assert read_back.stats.count == 2
    assert read_back.articles[0].title == "Fuite 0"


@pytest.mark.asyncio
async def test_read_leak_list_fetches_when_cache_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = make_articles_payload(count=1)
    install_fake_client(monkeypatch, payload)

    result = await fuite.read_leak_list(year=2025)

    assert result is not None
    assert result.stats.count == 1

    cached = fuite.cache.get(fuite._cache_key(2025))
    assert cached is not None
    assert cached.stats.count == 1


@pytest.mark.asyncio
async def test_cache_is_partitioned_by_year(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_client(monkeypatch, make_articles_payload(count=5))
    await fuite.write_leak_list(year=2024)

    install_fake_client(monkeypatch, make_articles_payload(count=9))
    await fuite.write_leak_list(year=2025)

    data_2024 = await fuite.read_leak_list(year=2024)
    data_2025 = await fuite.read_leak_list(year=2025)

    assert data_2024 is not None and data_2024.stats.count == 5
    assert data_2025 is not None and data_2025.stats.count == 9


@pytest.mark.asyncio
async def test_check_new_leak_returns_none_without_prior_cache(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_client(monkeypatch, make_articles_payload(count=3))

    result = await fuite.check_new_leak(year=2025)

    assert result is None


@pytest.mark.asyncio
async def test_check_new_leak_detects_new_articles(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_client(monkeypatch, make_articles_payload(count=2))
    await fuite.write_leak_list(year=2025)

    install_fake_client(monkeypatch, make_articles_payload(count=5))
    new_articles = await fuite.check_new_leak(year=2025)

    assert new_articles is not None
    assert len(new_articles) == 3

    updated = await fuite.read_leak_list(year=2025)
    assert updated is not None
    assert updated.stats.count == 5


@pytest.mark.asyncio
async def test_check_new_leak_returns_none_when_no_change(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_client(monkeypatch, make_articles_payload(count=4))
    await fuite.write_leak_list(year=2025)

    install_fake_client(monkeypatch, make_articles_payload(count=4))
    result = await fuite.check_new_leak(year=2025)

    assert result is None


@pytest.mark.asyncio
async def test_check_new_leak_returns_none_on_fetch_failure(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_client(monkeypatch, make_articles_payload(count=2))
    await fuite.write_leak_list(year=2025)

    install_fake_client(monkeypatch, payload=None)
    result = await fuite.check_new_leak(year=2025)

    assert result is None

    untouched = fuite.cache.get(fuite._cache_key(2025))
    assert untouched is not None
    assert untouched.stats.count == 2


@pytest.mark.asyncio
async def test_cache_expires_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fuite, "CACHE_TTL", 1)
    install_fake_client(monkeypatch, make_articles_payload(count=1))

    await fuite.write_leak_list(year=2025)
    assert fuite.cache.get(fuite._cache_key(2025)) is not None

    await asyncio.sleep(1.5)

    assert fuite.cache.get(fuite._cache_key(2025)) is None
