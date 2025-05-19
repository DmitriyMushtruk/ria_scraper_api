import os

from parsel import Selector

BASE_URL = os.getenv("BASE_URL")

class LinkFetcher:
    """Class for extracting links from the HTML text."""

    @staticmethod
    def extract_links(*, html_text: str) -> list[str]:
        """Extract links from the HTML text."""
        selector = Selector(text=html_text)
        return [
            BASE_URL + div.attrib["data-link-to-view"]
            for div in selector.css("div.hide[data-link-to-view]")
            if "/auto_" in div.attrib.get("data-link-to-view", "")
        ]
