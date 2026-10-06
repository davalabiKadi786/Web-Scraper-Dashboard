# Multi-Source Web Scraping and Data Consolidation

A small ETL pipeline that scrapes two practice sites, cleans and validates the data,
removes duplicates and writes ONE consolidated CSV plus a JSON summary report.

    Scrape (both sites) -> Clean -> Validate -> Deduplicate -> Consolidate -> Save

Sources: https://books.toscrape.com/ (1,000 books, 50 pages) and
https://quotes.toscrape.com/ (100 quotes, 10 pages).

## Python version
Python 3.10, 3.11 or 3.12.

## Setup
    python -m venv .venv
    # Windows:      .venv\Scripts\activate
    # macOS/Linux:  source .venv/bin/activate
    pip install -r requirements.txt

## Dependencies
requests (HTTP), beautifulsoup4 (HTML search), lxml (fast HTML parser).
Everything else is the standard library (csv, json, logging, re, urllib.parse,
hashlib, unicodedata, argparse, unittest ...). No accounts or API keys.

## How to run
    python main.py                      # full run, ~1,100 records, about 2-4 minutes
    python main.py --max-pages 2        # quick trial run
    python main.py --sources quotes     # one source only
    python main.py --no-categories      # skip the extra category crawl for books
    python main.py --with-details       # also fetch each book page for its description
                                        # (1,000 extra requests, ~10 minutes)
    python main.py --delay 1.0 --log-level DEBUG

Run the tests (offline, no internet needed):

    python -m unittest discover -s tests -v

Outputs (created in `output/` and `logs/`):

| File                          | Content                                            |
|-------------------------------|----------------------------------------------------|
| output/final_dataset.csv      | one row per unique, valid record, same columns     |
| output/summary_report.json    | per-source counts, reasons, duration, self-checks  |
| output/excluded_records.json  | every rejected / duplicate record with the reason  |
| logs/scraper_<timestamp>.log  | every request, warning, retry and error            |

## Step 1 - Observations about the sources
* Books: 20 books per listing page, "Page 1 of 50", 1,000 results. A relative
  `li.next a` link leads to the next page (`catalogue/page-2.html`, then `page-3.html`
  ... resolved against the CURRENT page URL with `urljoin`).
* Books: title text is truncated ("A Light in the ...") but the link's `title`
  attribute has the full title. Price is `p.price_color` (pound sign + 51.77). The rating is a
  CSS class (`star-rating Three`). Availability is `p.availability`.
* Books: the category is NOT on listing pages. It is on each book page or on the
  50 category listing pages (sidebar). We crawl the category pages (~65 requests)
  instead of 1,000 book pages.
* Quotes: 10 quotes per page in `div.quote`: `span.text` (wrapped in curly quotes),
  `small.author`, `a.tag`. Same `li.next a` pagination (`/page/2/`).
* The sites share nothing: a book has price/rating/category, a quote has
  author/tags. That is why a common schema with nullable columns is needed.

## Data model (common schema)
`source, name_or_title, category, price, rating, author, tags, availability,
description, source_url, scraped_at`

* `name_or_title` holds the book title or the quote text, so both fit one column.
* Fields that do not apply to a source stay empty (None / empty CSV cell). Nothing is
  invented: a quote has no price, a book has no author.
* `tags` is joined with `|`. `price` is in GBP (the site's currency).
* `source_url` is the book's own page; quotes have no page of their own, so it is the
  listing page where the quote appeared. `scraped_at` is UTC ISO-8601.
* `description` is only filled with `--with-details`.

## How pagination works
`BaseScraper.crawl()` starts at the first page, parses it, finds the `li.next a`
link, resolves it to a full URL and repeats until there is no next link. No page
number is hard-coded. A `visited` set prevents infinite loops.

If a page fails after all retries, its "next" link is unknown, so the scraper guesses
the next URL from the site's pattern (`page-N.html`, `/page/N/`) and continues. After
2 consecutive failures the crawl for that source stops.

## Cleaning approach (processing/cleaning.py)
* Whitespace: trim and collapse spaces, tabs, newlines and non-breaking spaces;
  drop zero-width characters.
* Placeholders such as "N/A", "none", "-" become None.
* Price: pound-sign text such as "51.77" -> 51.77 (float). Rating words:
  "Three" -> 3.
* Quote text: one pair of surrounding curly quotes is removed.
* Tags: trimmed, lower-cased, de-duplicated, order kept.
* URLs: made absolute, scheme and host lower-cased, fragment removed; non-http(s) or
  host-less URLs become None.
* Cleaning is lenient: a value that cannot be parsed (price "free") is passed on
  unchanged so that validation can reject it with a clear reason.

## Validation approach (processing/validation.py)
Each record gets a list of reason codes; an empty list means valid.
* `unknown_source`
* `missing_<field>` for required fields: books need title, price, rating, URL,
  timestamp; quotes need text, author, URL, timestamp.
* `invalid_price` (not a number or negative), `invalid_rating` (not a number in 1-5),
  `invalid_source_url`.
Rejected records are never dropped silently: they are counted per reason in the summary
and saved in `excluded_records.json`.

## Deduplication approach (processing/deduplication.py)
Exact comparison is not enough ("Example Book Title", " Example Book Title ",
"EXAMPLE BOOK TITLE"). Each record gets a fingerprint:

    SHA-256( source + normalised key fields )

Key fields (`config.DEDUP_KEYS`): books = title + price, quotes = text + author.
Normalisation = Unicode NFKC, case-fold, punctuation removed, spaces collapsed.
So "Example, Book  Title!" equals "example book title". The source is part of the
fingerprint, so a book and a quote can never collide. Price is part of the book key so
two different books that happen to share a title are not merged.

Strategy: the FIRST record is kept and later ones are removed (not just flagged),
because the final dataset must be one row per unique item. Removals stay auditable:
`excluded_records.json` lists each removed record and which kept record it duplicates.
The live practice sites contain no duplicates, so a real run is expected to report 0;
the logic is proven by the unit tests, which use deliberately messy duplicates.

## Error-handling approach
* HTTP (scrapers/http_client.py): timeout on every request; retries (3 attempts,
  exponential backoff 1s, 2s, 4s) for timeouts, connection errors and HTTP
  429/500/502/503/504; other errors such as 404 are not retried. The client returns
  None instead of raising.
* Pages: a failed page is logged and skipped; the crawl continues (see pagination).
* Elements: missing HTML elements give None values (`text_of`, `attr_of`), and each
  item is parsed inside its own try/except so one bad entry cannot stop a page.
* Sources: if a scraper crashes, the other source still runs.
* Data: bad values are rejected with reasons, never crash the run.
* Rate limiting: at least 0.5 s between requests (`--delay`).
* Logging: console + `logs/scraper_<timestamp>.log`.

## Self-checks in the summary report
* `scraped == rejected + duplicates_removed + final` for every source.
* CSV row count (re-read from disk) equals the final total in the JSON.

## Assumptions
* The two sites keep their current HTML structure.
* Book price is in GBP and book availability is the text shown on the listing page.
* Two quotes with the same text and author are the same quote.

## Known limitations
* Sequential scraping (polite, 2-4 minutes); no async or parallel requests.
* No checkpoint/resume: an interrupted run starts again.
* Quote `source_url` is the listing page, not a unique URL per quote.
* Author biography pages of the quotes site are not scraped.
* Pages are parsed with CSS selectors; a redesign of the sites would need selector
  updates in `scrapers/books_scraper.py` and `scrapers/quotes_scraper.py` only.

## If this had to run in production
Scheduler (cron/Airflow), checkpointing and incremental runs, a database instead of
CSV, metrics/alerts on rejected and failed counts, and a proxy-aware async client.

## AI usage summary
See AI_USAGE.md.
