from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Query

from app.db import Car
from app.db.manager import DBManager
from app.scraper.schemas import CarSchema
from app.scraper.scraper import Scraper

api = APIRouter()


@api.get("/cars/{car_id}", response_model=CarSchema)
async def get_car(car_id: Annotated[int, Path(..., ge=1)]) -> Car:
    """Fetch a car object from the database based on the provided car ID.

    Returns it as a structured response. Raises an HTTPException if no car is found for the specified ID.
    The car ID must be a positive integer.
    """
    car = await DBManager.read_one(car_id)
    if not car:
        raise HTTPException(status_code=404, detail=f"Car with id={car_id} not found")
    return car

@api.get("/cars/", response_model=list[CarSchema])
async def list_cars(
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Car]:
    """Fetch a paginated list of cars from the database.

    This function retrieves a list of car objects based on the provided limit
    and offset query parameters. The results are returned in accordance
    with the response model `List[CarSchema]`.
    """
    return await DBManager.read_list(limit=limit, offset=offset)

@api.post("/dump/")
async def trigger_dump(background_tasks: BackgroundTasks) -> dict[str, str]:
    """Trigger a database dump task asynchronously."""
    async def dump_task() -> None:
        await DBManager().dump()
    background_tasks.add_task(dump_task)
    return {"message": "Database dump initiated"}

@api.post("/scrape/")
async def fetch_cars(background_tasks: BackgroundTasks) -> dict[str, str]:
    """Trigger a scraping task asynchronously."""
    async def scraping_task() -> None:
        async with Scraper() as scraper:
            await scraper.start()

    background_tasks.add_task(scraping_task)
    return {"message": "Scraping process initiated"}
