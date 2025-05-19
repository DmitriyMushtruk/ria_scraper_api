import logging
import secrets
from typing import Literal

from aiohttp import ClientResponseError, ClientSession

from app.scraper.utils import USER_AGENTS

logger = logging.getLogger(__name__)

class RiaException(Exception):
    """Exception raised for errors related to RIA scraper operations."""


class PageFetcher:
    """Class for fetching web pages using aiohttp sessions, handling GET and POST requests."""

    def __init__(self, *, session: ClientSession) -> None:
        self._session = session

    async def request(
            self,
            *,
            method: Literal["get", "post"],
            url: str,
            headers: dict | None = None,
            payload: dict | None = None,
    ) -> str | None:
        """Perform a request to the given URL with the given payload and headers."""
        try:
            func = getattr(self._session, method)
            async with func(url=url, headers=headers, json=payload) as response:
                response.raise_for_status()
                data: bytes = await response.read()
                return data.decode(response.charset, errors="ignore")
        except ClientResponseError as exc:
            logger.exception(
                "HTTP error for %s %s: %s %s. Payload: %r. Headers: %r.",
                method.upper(), url, exc.status, exc.message, payload, headers,
            )
            raise RiaException from exc

    async def get(self, *, url: str) -> str:
        """Perform a GET request to the given URL with default headers."""
        headers = self.build_default_headers(url=url)
        return await self.request(method="get", url=url, headers=headers)

    async def post(self, *, url: str, headers: dict, payload: dict) -> str:
        """Perform a POST request to the given URL with the given payload and headers."""
        return await self.request(method="post", url=url, headers=headers, payload=payload)

    @staticmethod
    def get_random_user_agent() -> str:
        """Return a random User-Agent string."""
        return secrets.choice(USER_AGENTS)

    def build_default_headers(self, *, url: str) -> dict:
        """Construct HTTP headers with randomized User-Agent for requests."""
        user_agent = self.get_random_user_agent()
        return {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;"
                      "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
                      "application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": url,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }

    def build_phone_headers(self, *, url: str) -> dict:
        """Construct HTTP headers with randomized User-Agent for requests."""
        user_agent = self.get_random_user_agent()
        return {
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Origin": "https://auto.ria.com",
            "Referer": url,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }

    @staticmethod
    def build_phone_payload(*, auto_id, user_id, phone_id) -> dict:
        """Build payload for POST request to fetch the phone number page."""
        return  {
            "blockId": "autoPhone",
            "popUpId": "autoPhone",
            "isLoginRequired": False,
            "autoId": auto_id,
            "data": [
                ["userId", str(user_id)],
                ["phoneId", str(phone_id)],
                ["title", ""],
                ["isCheckedVin", "1"],
                ["companyId", ""],
                ["companyEng", ""],
                ["avatar", ""],
                ["userName", ""],
                ["isCardPayer", "1"],
                ["dia", ""],
                ["isOnline", ""],
                ["isCompany", ""],
                ["srcAnalytic", "main_side_sellerInfo_sellerInfoHiddenPhone_sellerInfoPhone_showBottomPopUp"],
            ],
            "params": {
                "userId": str(user_id),
                "phoneId": str(phone_id),
                "title": "",
                "isCheckedVin": "1",
                "companyId": "",
                "companyEng": "",
                "avatar": "",
                "userName": "",
                "isCardPayer": "1",
                "dia": "",
                "isOnline": "",
                "isCompany": "",
            },
            "target": {},
            "formId": None,
            "langId": 2,
            "device": "desktop-web",
        }
