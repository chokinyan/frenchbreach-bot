from pydantic import BaseModel


class Article(BaseModel):
    id: str | None
    title: str | None
    description: str | None
    date: str | None
    source: str | None
    logo: str | None
    slug: str | None
    status: str | None
    is_scheduled: int | None
    published_at: str | None
    seo_title: str | None
    google_index_hash: str | None
    dataTypes: list[str | None] | None
    affectedCount: int | None
    dataVolumeGb: float | None
    headerImage: str | None
    lastModified: str | None
    breachStatus: str | None
    shortUrl: str | None


class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class Stats(BaseModel):
    count: int


class ArticlesResponse(BaseModel):
    articles: list[Article]
    pagination: Pagination
    stats: Stats
