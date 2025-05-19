from datetime import datetime

from pydantic import BaseModel, conint, constr


class CarSchema(BaseModel):
    """Schema for car listing data extracted during scraping."""

    url: str
    title: str | None
    price_usd: float | None
    odometer: conint(ge=0) | None
    username: str | None
    phone_number: constr(strip_whitespace=True) | None
    image_url: str | None
    images_count: conint(ge=0) | None
    car_number: constr(strip_whitespace=True) | None
    car_vin: str | None
    datetime_found: datetime | None = None

    class Config:
        from_attributes = True
