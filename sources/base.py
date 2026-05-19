from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class RomResult:
    title: str
    system: str
    source: str
    page_url: str
    download_url: str | None = None
    size: str | None = None

    @property
    def best_url(self) -> str:
        return self.download_url or self.page_url

    @property
    def has_direct_download(self) -> bool:
        return self.download_url is not None


class Source(ABC):
    name: str
    base_url: str

    @abstractmethod
    async def search(
        self, client: httpx.AsyncClient, query: str, system: str | None = None
    ) -> list[RomResult]: ...


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def make_client(timeout: float = 30.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9,es;q=0.8"},
    )
