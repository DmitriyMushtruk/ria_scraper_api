import asyncio
import functools
import logging
import os
import time
from collections.abc import Callable, Coroutine
from types import TracebackType
from typing import Any

from aiohttp import ClientSession, TCPConnector

from app.db.manager import DBManager
from app.scraper.car_data_fetcher import CarDataFetcher
from app.scraper.link_fetcher import LinkFetcher
from app.scraper.page_fetcher import PageFetcher, RiaException

DEFAULT_URL = os.getenv("DEFAULT_URL")
MAX_WORKERS = os.getenv("MAX_WORKERS")
MAX_CONCURRENT_REQUESTS = os.getenv("MAX_CONCURRENT_REQUESTS")

logger = logging.getLogger(__name__)


class Scraper:
    """Asynchronous scraper for collecting car data from RIA website."""

    def __init__(self) -> None:
        self.default_url: str = DEFAULT_URL
        self.batch_size: int = 10
        self.max_concurrent_requests: int = int(MAX_CONCURRENT_REQUESTS)
        self.max_workers: int = int(MAX_WORKERS)

        self.session: ClientSession | None = None
        self.page_fetcher: PageFetcher | None = None
        self.link_fetcher: LinkFetcher | None = None
        self.car_fetcher: CarDataFetcher | None = None
        self.db_manager: DBManager | None = None

        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.semaphore: asyncio.Semaphore | None = None

    async def __aenter__(self) -> "Scraper":
        """Enter the asynchronous context and initialize scraper resources."""
        self.session = ClientSession(connector=TCPConnector(limit=100, limit_per_host=20))
        self.page_fetcher = PageFetcher(session=self.session)
        self.link_fetcher = LinkFetcher()
        self.car_fetcher = CarDataFetcher(page_fetcher=self.page_fetcher)
        self.db_manager = DBManager()
        self.semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: TracebackType | None) -> None:
        """Exit the asynchronous context and close resources."""
        await self.session.close()

    @staticmethod
    def async_timed(func) -> Callable[[tuple[Any, ...], dict[str, Any]], Coroutine[Any, Any, Any]]:
        """Decorate to measure and log the execution time of asynchronous functions."""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> callable:
            """Wrap function to measure execution time."""
            start_time = time.perf_counter()
            result = await func(*args, **kwargs)
            end_time = time.perf_counter()
            elapsed = end_time - start_time
            logger.info("[TIMING] Function '%s' executed in %.2f seconds", func.__name__, elapsed)
            return result

        return wrapper

    @async_timed
    async def start(self) -> None:
        """Start the scraping process by launching producer and worker tasks."""
        producer = asyncio.create_task(self._producer())
        workers = [
            asyncio.create_task(self._worker(i)) for i in range(self.max_workers)
        ]

        await producer
        await self.queue.join()

        producer.cancel()
        [workers.cancel() for workers in workers]
        await asyncio.gather(*workers, return_exceptions=True)

    async def _producer(self, page: int = 1, max_empty_pages: int = 10) -> None:
        empty_pages = 0

        while True:
            url: str = f"{self.default_url}?page={page}"
            logger.info("[Producer] Scraping page %s: %s", page, url)

            try:
                html_text: str = await self.page_fetcher.get(url=url)
            except RiaException:
                logger.exception("[Producer] Error fetching list page %s", url)
                page += 1
                continue

            links: list[str] = self.link_fetcher.extract_links(html_text=html_text)
            logger.info("[Producer] Founded %s links on page %s: %s", len(links), page, url)

            if not links:
                empty_pages += 1
                logger.warning("[Producer] No links on page %s. %s empty pages in a row.", page, empty_pages)
                if empty_pages >= max_empty_pages:
                    logger.info("[Producer] Reached %s empty pages in a row → stopping ...", max_empty_pages)
                    break
            else:
                empty_pages = 0
                for link in links:
                    await self.queue.put(link)
            page += 1

    async def _worker(self, index: int) -> None:
        while True:
            try:
                url = await self.queue.get()
                logger.info("[Worker-%s] Scraping %s", index, url)
            except asyncio.CancelledError:
                break

            async with self.semaphore:
                try:
                    html = await self.page_fetcher.get(url=url)
                    data = await self.car_fetcher.parse_car_page(url=url, html_text=html)
                except RiaException:
                    logger.exception("[Worker-%s] Error fetching %s", index, url)
                else:
                    await self.db_manager.write_car(data=data)
                finally:
                    self.queue.task_done()
