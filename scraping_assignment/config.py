"""Central configuration: source names, output schema, rules and defaults."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"

# ---- Sources -------------------------------------------------------------
BOOKS_SOURCE = "Books to Scrape"
QUOTES_SOURCE = "Quotes to Scrape"
BOOKS_URL = "https://books.toscrape.com/"
QUOTES_URL = "https://quotes.toscrape.com/"
KNOWN_SOURCES = {BOOKS_SOURCE, QUOTES_SOURCE}

# ---- Common output schema (column order of the CSV) ----------------------
SCHEMA = [
    "source",
    "name_or_title",   # book title OR quote text
    "category",        # books only
    "price",           # books only (GBP, float)
    "rating",          # books only (1-5, int)
    "author",          # quotes only
    "tags",            # quotes only (joined with TAG_SEPARATOR in the CSV)
    "availability",    # books only
    "description",     # books only, and only with --with-details
    "source_url",
    "scraped_at",
]
TAG_SEPARATOR = "|"

# ---- Validation rules ----------------------------------------------------
REQUIRED_FIELDS = {
    BOOKS_SOURCE: ("name_or_title", "price", "rating", "source_url", "scraped_at"),
    QUOTES_SOURCE: ("name_or_title", "author", "source_url", "scraped_at"),
}
RATING_MIN, RATING_MAX = 1, 5

# ---- Duplicate detection: fields that identify "the same record" ---------
DEDUP_KEYS = {
    BOOKS_SOURCE: ("name_or_title", "price"),
    QUOTES_SOURCE: ("name_or_title", "author"),
}

# ---- HTTP behaviour --------------------------------------------------------
USER_AGENT = "assignment-scraper/1.0 (educational project)"
DEFAULT_DELAY = 0.5       # seconds between requests
TIMEOUT = 15              # seconds per request
MAX_RETRIES = 3           # attempts per URL
BACKOFF = 1.0             # 1s, 2s, 4s ... between retries
MAX_CONSECUTIVE_PAGE_FAILURES = 2
