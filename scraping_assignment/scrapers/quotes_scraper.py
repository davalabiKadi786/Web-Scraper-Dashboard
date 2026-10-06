"""Quotes to Scrape: all selectors and parsing rules for this site live here."""
import logging
import re
from urllib.parse import urljoin

import config
from scrapers.base_scraper import BaseScraper, blank_record, text_of, utc_now_iso

log = logging.getLogger(__name__)


class QuotesScraper(BaseScraper):
    name = config.QUOTES_SOURCE
    start_url = config.QUOTES_URL

    def parse_page(self, soup, page_url):
        scraped_at = utc_now_iso()
        items = soup.select("div.quote")
        if not items:
            log.warning("No quotes found on %s", page_url)
        records, errors = [], 0
        for item in items:
            try:
                record = blank_record(self.name)
                record.update(
                    name_or_title=text_of(item.select_one("span.text")),
                    author=text_of(item.select_one("small.author")),
                    tags=[tag.get_text() for tag in item.select("div.tags a.tag")],
                    source_url=page_url,  # quotes have no page of their own
                    scraped_at=scraped_at,
                )
                records.append(record)
            except Exception:
                errors += 1
                log.warning("Skipping unparseable quote on %s", page_url, exc_info=True)
        return records, errors

    def guess_next_url(self, page_url):
        match = re.search(r"/page/(\d+)/?$", page_url)
        if match:
            return page_url[: match.start()] + f"/page/{int(match.group(1)) + 1}/"
        return urljoin(page_url, "/page/2/")
