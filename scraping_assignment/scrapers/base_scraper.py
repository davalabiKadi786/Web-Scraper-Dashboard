"""Shared scraper machinery: pagination loop and safe extraction helpers."""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urljoin

import config

log = logging.getLogger(__name__)


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def text_of(element):
    """Text of a BeautifulSoup element, or None when the element is missing."""
    return element.get_text() if element is not None else None


def attr_of(element, name):
    """String attribute of an element, or None when missing."""
    if element is None:
        return None
    value = element.get(name)
    return value if isinstance(value, str) else None


def blank_record(source):
    """A record with every schema column present (None = not applicable)."""
    record = {name: None for name in config.SCHEMA}
    record["source"] = source
    return record


@dataclass
class ScrapeResult:
    source: str
    records: list = field(default_factory=list)
    pages_fetched: int = 0
    pages_failed: int = 0
    failed_urls: list = field(default_factory=list)
    parse_errors: int = 0
    extra_pages_fetched: int = 0   # supporting pages (categories / details)
    extra_pages_failed: int = 0
    error: str = None


class BaseScraper:
    """Pagination loop shared by all sources. Subclasses add selectors."""

    name = ""
    start_url = ""

    def __init__(self, client, start_url=None, max_pages=None):
        self.client = client
        self.start_url = start_url or self.start_url
        self.max_pages = max_pages

    # ---- to be provided by subclasses ------------------------------------
    def parse_page(self, soup, page_url):
        """Return (records, number_of_items_that_failed_to_parse)."""
        raise NotImplementedError

    def guess_next_url(self, page_url):
        """Fallback used only when a page failed and its 'next' link is unknown."""
        return None

    # ---- shared behaviour -------------------------------------------------
    def find_next_url(self, soup, page_url):
        href = attr_of(soup.select_one("li.next a"), "href")
        return urljoin(page_url, href) if href else None

    def crawl(self, start_url, on_page, stats):
        """Follow 'next' links from start_url. Calls on_page(soup, url) per page."""
        url, visited, failures, attempted = start_url, set(), 0, 0
        while url and url not in visited:
            if self.max_pages is not None and attempted >= self.max_pages:
                log.info("Reached max_pages=%d, stopping this crawl", self.max_pages)
                break
            visited.add(url)
            attempted += 1

            soup = self.client.get_soup(url)
            if soup is None:
                stats.pages_failed += 1
                stats.failed_urls.append(url)
                failures += 1
                if failures >= config.MAX_CONSECUTIVE_PAGE_FAILURES:
                    log.error("%d consecutive page failures - stopping crawl", failures)
                    break
                url = self.guess_next_url(url)
                log.warning("Page failed; continuing with guessed next page: %s", url)
                continue

            failures = 0
            stats.pages_fetched += 1
            on_page(soup, url)
            url = self.find_next_url(soup, url)

    def scrape(self):
        result = ScrapeResult(source=self.name)

        def on_page(soup, url):
            records, errors = self.parse_page(soup, url)
            result.records.extend(records)
            result.parse_errors += errors
            log.info("Parsed %d records from %s", len(records), url)

        self.crawl(self.start_url, on_page, result)
        log.info(
            "%s: %d records, %d pages ok, %d pages failed",
            self.name, len(result.records), result.pages_fetched, result.pages_failed,
        )
        return result
