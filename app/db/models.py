from sqlalchemy import Column, DateTime, Integer, Numeric, String, func

from app.db.connection import Base


class Car(Base):
    """SQLAlchemy model for the 'cars' table."""

    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=True)
    price_usd = Column(Numeric, nullable=True)
    odometer = Column(Integer, nullable=True)
    username = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    images_count = Column(Integer, nullable=True)
    car_number = Column(String, nullable=True)
    car_vin = Column(String, nullable=True)
    datetime_found = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
