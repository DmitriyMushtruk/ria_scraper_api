import json
import logging
import os
import re
from json import JSONDecodeError

from parsel import Selector
from pydantic import ValidationError

from app.scraper.page_fetcher import PageFetcher, RiaException
from app.scraper.schemas import CarSchema

logger = logging.getLogger(__name__)

PHONE_URL = os.getenv("PHONE_URL")

class CarDataFetcher:
    """Class for fetching car data from RIA website."""

    VIN_PATTERN = re.compile(
        r"\b"
        r"[A-HJ-NPR-Z0-9]{8}"
        r"[A-HJ-NPR-Z0-9]"
        r"[A-HJ-NPR-Z0-9]{2}"
        r"[xX]{4}"
        r"[A-HJ-NPR-Z0-9]{2}"
        r"\b",
        flags=re.IGNORECASE,
    )

    def __init__(self, page_fetcher: PageFetcher) -> None:
        self._page_fetcher = page_fetcher

    async def parse_car_page(self, *, html_text: str, url: str) -> CarSchema | None:
        """Parse car data from HTML text and return a CarSchema object."""
        selector: Selector = Selector(text=html_text)

        data = {
            "url": url,
            "title": self._get_car_title(selector=selector),
            "price_usd": self._get_car_price(selector=selector),
            "odometer": self._get_car_odometer(selector=selector),
            "username": self._get_username(html_text=html_text),
            "image_url": self._get_main_image(html_text=html_text),
            "images_count": self._get_images_count(selector=selector),
            "car_number": self._get_car_number(selector=selector),
            "car_vin": self._get_vin(html_text=html_text),
            "phone_number": await self._get_phone(html_text=html_text, url=url),
        }

        try:
            car = CarSchema(**data)
        except ValidationError:
            logger.exception("[Parser] Validation error for %s", url)
            return None
        else:
            return car

    @staticmethod
    def _get_car_title(*, selector: Selector) -> str | None:
        title = selector.css("h1::text").get()
        return title.strip() if title else ""

    @staticmethod
    def _get_car_price(*, selector: Selector) -> str | None:
        text = selector.css("script#ldJson2::text").get()
        if not text:
            return None
        try:
            data = json.loads(text)
            price = data["offers"]["price"]
        except (JSONDecodeError, KeyError, TypeError):
            logger.exception("Error parsing JSON for car price")
            return None
        else:
            return price

    @staticmethod
    def _get_car_odometer(*, selector: Selector) -> str | None:
        text = selector.css("script#ldJson2::text").get()
        if not text:
            return None
        try:
            data = json.loads(text)
            mileage = data.get("mileageFromOdometer")
            if mileage and "value" in mileage:
                return mileage["value"]
        except (JSONDecodeError, KeyError, TypeError):
            logger.exception("Error parsing JSON for odometer")
            return None
        else:
            return None

    def _get_username(self, *, html_text) -> str | None:
        selector = Selector(text=html_text)
        name = selector.css("section#userInfoBlock div.seller_info_name a::text").get()
        if name:
            return name.strip()
        return self._get_username_from_js(html_text)

    @staticmethod
    def _get_username_from_js(html_text) -> str | None:
        match = re.search(r'window\.ria\.userName\s*=\s*"([^"]*)";', html_text)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _get_main_image(*, html_text) -> str | None:
        regex = re.compile(r'window\.ria\.headPhoto\s*=\s*"([^"]+)"')
        match = regex.search(html_text)
        return match.group(1) if match else None

    @staticmethod
    def _get_images_count(*, selector: Selector) -> int | None:
        photo_ids = selector.css("img[data-photo-id]::attr(data-photo-id)").getall()
        return len(set(photo_ids))

    @staticmethod
    def _get_car_number(*, selector: Selector) -> str | None:
        car_number = selector.css("span.state-num.ua::text").get()
        if car_number:
            return re.sub(r"\s+", "", car_number.strip())
        return None

    def _get_vin(self, *, html_text) -> str | None:
        selector = Selector(text=html_text)
        text = selector.css("script#ldJson2::text").get()
        if text:
            data = json.loads(text)
            vin = data.get("vehicleIdentificationNumber")
            if vin is not None:
                return vin

            vin = self._get_masked_vin(html_text=html_text)
            if vin is not None:
                return vin
        return None

    def _get_masked_vin(self, *, html_text: str) -> str | None:
        if not html_text:
            return None
        matches = self.VIN_PATTERN.findall(html_text)
        if matches:
            return matches[0].upper()
        return None

    async def _get_phone(self, *, html_text, url) -> str | None:
        selector = Selector(text=html_text)
        phone_id = self._get_phone_id(selector=selector)
        auto_id = self._get_auto_id(selector=selector)
        user_id = self._get_user_id(selector=selector)

        if all([phone_id, auto_id, user_id]):
            headers = self._page_fetcher.build_phone_headers(url=url)
            payload = self._page_fetcher.build_phone_payload(auto_id=auto_id, user_id=user_id, phone_id=phone_id)
            try:
                response = await self._page_fetcher.post(url=PHONE_URL, headers=headers, payload=payload)
            except RiaException:
                logger.exception(
                    "Error fetching phone number %s. "
                    "Attrs: phone_id=%s, auto_id=%s, user_id=%s.",
                    url, phone_id, auto_id, user_id,
                )
                return None
            else:
                try:
                    data = json.loads(response)
                except JSONDecodeError:
                    logger.exception("Failed to decode phone JSON from %s: %s", url, response[:100])
                    return None
            return self._extract_phone_number(data=data)
        return None

    @staticmethod
    def _get_phone_id(*, selector: Selector) -> str | None:
        phone_id = selector.css("a#openPopupCommentSeller::attr(data-phone-id)").get()
        if phone_id:
            return phone_id.strip()
        return None

    @staticmethod
    def _get_auto_id(*, selector: Selector) -> str | None:
        auto_id = selector.css("body::attr(data-auto-id)").get()
        if auto_id:
            return auto_id.strip()
        return None

    @staticmethod
    def _get_user_id(*, selector: Selector) -> str | None:
        user_id = selector.css("script[data-owner-id]::attr(data-owner-id)").get()
        if user_id:
            return user_id.strip()
        return None

    @staticmethod
    def _extract_phone_number(*, data: dict) -> str | None:
        templates = data.get("templates", [])
        for template in templates:
            action_data = template.get("actionData", {})
            params = action_data.get("params", {})
            phone = params.get("phone")
            if phone:
                return "+380" + str(phone)
        phone = data.get("phone")
        if phone:
            return str(phone)
        return None
