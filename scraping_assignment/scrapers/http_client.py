"""HTTP layer: rate limiting, timeouts, retries with exponential backoff."""
import logging
import time

import requests
from bs4 import BeautifulSoup

import config

log = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class HttpClient:
    """Polite GET client. Never raises for network problems: returns None."""

    def __init__(
        self,
        delay=config.DEFAULT_DELAY,
        timeout=config.TIMEOUT,
        max_retries=config.MAX_RETRIES,
        backoff=config.BACKOFF,
    ):
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self.request_count = 0
        self._last_request_at = 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})

    def _respect_rate_limit(self):
        wait = self.delay - (time.monotonic() - self._last_request_at)
        if wait > 0:
            time.sleep(wait)

    def get_html(self, url):
        """Return the page HTML as text, or None after all retries failed."""
        for attempt in range(1, self.max_retries + 1):
            self._respect_rate_limit()
            reason = None
            try:
                response = self.session.get(url, timeout=self.timeout)
            except (requests.Timeout, requests.ConnectionError) as exc:
                response, reason = None, type(exc).__name__
            except requests.RequestException as exc:  # e.g. invalid URL
                log.error("Request to %s failed permanently: %s", url, exc)
                return None
            self._last_request_at = time.monotonic()
            self.request_count += 1

            if response is not None:
                if response.status_code == 200:
                    response.encoding = "utf-8"  # sites omit charset; avoid mojibake
                    log.info("GET %s -> 200", url)
                    return response.text
                if response.status_code not in RETRYABLE_STATUS:
                    log.error("GET %s -> HTTP %s (not retried)", url, response.status_code)
                    return None
                reason = f"HTTP {response.status_code}"

            log.warning(
                "GET %s failed (%s) - attempt %d/%d",
                url, reason, attempt, self.max_retries,
            )
            if attempt < self.max_retries:
                time.sleep(self.backoff * 2 ** (attempt - 1))

        log.error("Giving up on %s after %d attempts", url, self.max_retries)
        return None

    def get_soup(self, url):
        """Return a parsed BeautifulSoup tree, or None when the fetch failed."""
        html = self.get_html(url)
        if html is None:
            return None
        return BeautifulSoup(html, "lxml")
