"""Books to Scrape: all selectors and parsing rules for this site live here."""
import logging
import re
from urllib.parse import urljoin

import config
from scrapers.base_scraper import (
    BaseScraper, ScrapeResult, attr_of, blank_record, text_of, utc_now_iso,
)

log = logging.getLogger(__name__)


class BooksScraper(BaseScraper):
    name = config.BOOKS_SOURCE
    start_url = config.BOOKS_URL

    def __init__(
        self, client, start_url=None, max_pages=None,
        fetch_categories=True, fetch_details=False,
    ):
        super().__init__(client, start_url, max_pages)
        self.fetch_categories = fetch_categories
        self.fetch_details = fetch_details

    # ---- listing pages -----------------------------------------------------
    def parse_page(self, soup, page_url):
        scraped_at = utc_now_iso()
        items = soup.select("article.product_pod")
        if not items:
            log.warning("No book entries found on %s", page_url)
        records, errors = [], 0
        for item in items:
            try:
                records.append(self._parse_item(item, page_url, scraped_at))
            except Exception:  # one broken entry must not stop the page
                errors += 1
                log.warning("Skipping unparseable book on %s", page_url, exc_info=True)
        return records, errors

    def _parse_item(self, item, page_url, scraped_at):
        link = item.select_one("h3 a")
        href = attr_of(link, "href")

        rating_word = None  # rating is a CSS class: "star-rating Three"
        rating_tag = item.select_one("p.star-rating")
        if rating_tag is not None:
            words = [c for c in rating_tag.get("class", []) if c != "star-rating"]
            rating_word = words[0] if words else None

        record = blank_record(self.name)
        record.update(
            # the title attribute holds the full title; link text is truncated
            name_or_title=attr_of(link, "title") or text_of(link),
            price=text_of(item.select_one("p.price_color")),
            rating=rating_word,
            availability=text_of(item.select_one("p.availability")),
            source_url=urljoin(page_url, href) if href else None,
            scraped_at=scraped_at,
        )
        return record

    def guess_next_url(self, page_url):
        match = re.search(r"page-(\d+)\.html$", page_url)
        if match:
            return page_url[: match.start()] + f"page-{int(match.group(1)) + 1}.html"
        if page_url.endswith("index.html"):  # first page of a category
            return page_url[: -len("index.html")] + "page-2.html"
        return urljoin(page_url, "catalogue/page-2.html")  # home page

    # ---- optional enrichment -----------------------------------------------
    def scrape(self):
        result = super().scrape()
        if self.fetch_categories and result.records:
            self._attach_categories(result)
        if self.fetch_details and result.records:
            self._attach_details(result)
        return result

    def _attach_categories(self, result):
        """Category is not on listing pages, so crawl each category listing."""
        home = self.client.get_soup(self.start_url)
        if home is None:
            log.error("Could not load home page; categories left empty")
            return
        categories = []
        for link in home.select("div.side_categories ul li ul li a"):
            name, href = text_of(link), attr_of(link, "href")
            if name and href:
                categories.append((name.strip(), urljoin(self.start_url, href)))
        log.info("Found %d categories", len(categories))

        mapping = {}
        aux = ScrapeResult(source=self.name)
        for name, url in categories:
            def on_page(soup, page_url, name=name):
                for anchor in soup.select("article.product_pod h3 a"):
                    href = attr_of(anchor, "href")
                    if href:
                        mapping[urljoin(page_url, href)] = name

            self.crawl(url, on_page, aux)

        result.extra_pages_fetched += aux.pages_fetched
        result.extra_pages_failed += aux.pages_failed
        result.failed_urls.extend(aux.failed_urls)
        for record in result.records:
            record["category"] = mapping.get(record["source_url"])
        missing = sum(1 for r in result.records if r["category"] is None)
        log.info("Categories attached; %d books without a category", missing)

    def _attach_details(self, result):
        """Slow (one request per book): adds description, fills missing category."""
        for record in result.records:
            url = record["source_url"]
            if not url:
                continue
            soup = self.client.get_soup(url)
            if soup is None:
                result.extra_pages_failed += 1
                result.failed_urls.append(url)
                continue
            result.extra_pages_fetched += 1
            record["description"] = text_of(soup.select_one("#product_description + p"))
            if record["category"] is None:
                crumbs = soup.select("ul.breadcrumb li a")  # Home > Books > Category
                if len(crumbs) >= 3:
                    record["category"] = text_of(crumbs[2])
