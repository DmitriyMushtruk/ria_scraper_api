import asyncio
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db import AsyncSessionLocal, Car
from app.scraper.schemas import CarSchema

logger = logging.getLogger(__name__)

class DBManager:
    """Database manager for handling car-related operations."""

    class DumpException(Exception):
        """Exception for handling database dump errors."""

    @staticmethod
    async def read_one(car_id: int) -> Car | None:
        """Read a car record by its ID."""
        async with AsyncSessionLocal() as session:
            stmt = select(Car).where(Car.id == car_id)
            result = await session.execute(stmt)
            return result.scalars().first()

    @staticmethod
    async def read_list(limit: int = 10, offset: int = 0) -> list[Car] | None:
        """Read a list of car records."""
        async with AsyncSessionLocal() as session:
            stmt = select(Car).limit(limit).offset(offset)
            result = await session.execute(stmt)
            return result.scalars().all()

    @staticmethod
    async def write_car(*, data: CarSchema) -> None:
        """Insert or update a car record based on the URL."""
        car = data.model_dump(exclude_unset=True)
        stmt = insert(Car).values(**car)
        stmt = stmt.on_conflict_do_update(
            index_elements=["url"],
            set_={key: value for key, value in car.items() if key != "url"},
        )

        async with AsyncSessionLocal() as db_session:
            try:
                await db_session.execute(stmt)
                await db_session.commit()
                logger.info("[DB-Manager] Inserted %s", car["url"])
            except IntegrityError as exc:
                await db_session.rollback()
                logger.warning("[DB-Manager] Integrity error for car %s: %s", car["url"], exc)
            except SQLAlchemyError:
                await db_session.rollback()
                logger.exception("[DB-Manager] Error upserting car %s", car["url"])

    async def dump(self) -> str:
        """Generate a database dump file and saves it in the "dumps" directory.

        If the dumping process fails, an exception is raised detailing the error.
        The method relies on a subprocess handling mechanism to create the dump
        and retrieves the standard error output if there's an issue.
        """
        Path("dumps").mkdir(parents=True, exist_ok=True)
        filename = f"dumps/dump_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.sql"
        process, stderr = await DBManager._run_dump_subprocess(filename)

        decoded_stderr = stderr.decode()
        if process.returncode != 0:
            message = f"Dump error: {decoded_stderr}"
            raise self.DumpException(message) from None
        logger.info("[DB-Manager] Database dump created: %s", filename)
        return filename

    @staticmethod
    async def _run_dump_subprocess(filename: str) -> tuple[asyncio.subprocess.Process, bytes]:
        """Execute an asynchronous subprocess to create a PostgreSQL database dump using the `pg_dump` utility.

        This static method handles setting up the
        necessary environment variables and executing the appropriate command with
        the provided parameters.

        The database dump is saved to the specified file, with details such as user,
        host, password, and port being retrieved from the environment variables:
        POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, and
        POSTGRES_DB. The process returns the subprocess information and any
        standard error output.
        """
        env = os.environ.copy()
        env["PGPASSWORD"] = os.getenv("POSTGRES_PASSWORD")

        args = [
            "pg_dump",
            "-U", os.getenv("POSTGRES_USER"),
            "-h", os.getenv("POSTGRES_HOST"),
            "-p", os.getenv("POSTGRES_PORT"),
            "-F", "c",
            "-b",
            "-v",
            "-f", filename,
            os.getenv("POSTGRES_DB"),
        ]

        process = await asyncio.create_subprocess_exec(
            *args,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        _, stderr = await process.communicate()
        return process, stderr
