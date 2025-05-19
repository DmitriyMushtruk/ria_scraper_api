import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.manager import DBManager
from app.scraper.scraper import Scraper

SCRAPE_HOUR = os.getenv("SCRAPE_HOUR")
SCRAPE_MINUTE = os.getenv("SCRAPE_MINUTE")
DUMP_HOUR = os.getenv("DUMP_HOUR")
DUMP_MINUTE = os.getenv("DUMP_MINUTE")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class BaseScheduler:
    """A class responsible for managing scheduling tasks such as scraping and database dumping using an asyncio-based scheduler.

    The class initializes an asynchronous scheduler, defines cron-based triggers
    for tasks, and provides methods to start, stop, and execute the tasks on schedule.
    """

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()

        self.scrape_trigger = CronTrigger(
            hour=int(os.getenv("SCRAPE_HOUR", "12")), minute=int(os.getenv("SCRAPE_MINUTE", "0")),
        )
        self.dump_trigger = CronTrigger(
            hour=int(os.getenv("DUMP_HOUR", "2")), minute=int(os.getenv("DUMP_MINUTE", "0")),
        )
        self.scraper: Scraper = Scraper()
        self.dumper: DBManager = DBManager()

    async def run_scrape_task(self) -> None:
        """Wrap task for running the scraper."""
        logger.info("Running scrubbing on schedule...")
        async with self.scraper as scraper:
            await scraper.start()

    async def run_dump_task(self) -> None:
        """Wrap task for performing a database dump."""
        logger.info("Running a database dump on schedule...")
        await self.dumper.dump()

    def start(self) -> None:
        """Start the scheduler and add tasks."""
        self.scheduler.start()

        self.scheduler.add_job(func=self.run_scrape_task, trigger=self.scrape_trigger)
        self.scheduler.add_job(func=self.run_dump_task, trigger=self.dump_trigger)

        scrape_job = self.scheduler.get_jobs()[0]
        dump_job = self.scheduler.get_jobs()[1]
        logger.info(
            "Scheduler started. Next scrap run: %s, dump: %s",
            scrape_job.next_run_time, dump_job.next_run_time,
        )

    def shutdown(self) -> None:
        """Close the scheduler."""
        self.scheduler.shutdown()

scheduler = BaseScheduler()
