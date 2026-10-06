"""Entry point:  python main.py   (see README.md for options)."""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import config
from pipeline import run_pipeline
from scrapers.books_scraper import BooksScraper
from scrapers.http_client import HttpClient
from scrapers.quotes_scraper import QuotesScraper


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Scrape Books to Scrape and Quotes to Scrape into one dataset."
    )
    parser.add_argument("--sources", nargs="+", choices=["books", "quotes"],
                        default=["books", "quotes"], help="which sources to scrape")
    parser.add_argument("--max-pages", type=int, default=None,
                        help="limit pages per crawl (quick trial runs)")
    parser.add_argument("--no-categories", action="store_true",
                        help="skip the extra category crawl for books")
    parser.add_argument("--with-details", action="store_true",
                        help="fetch every book page for its description (slow)")
    parser.add_argument("--delay", type=float, default=config.DEFAULT_DELAY,
                        help="seconds between requests (default 0.5)")
    parser.add_argument("--output-dir", default=str(config.DEFAULT_OUTPUT_DIR))
    parser.add_argument("--log-dir", default=str(config.DEFAULT_LOG_DIR))
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args(argv)
    if args.max_pages is not None and args.max_pages < 1:
        parser.error("--max-pages must be at least 1")
    if args.delay < 0:
        parser.error("--delay cannot be negative")
    return args


def setup_logging(log_dir, level):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_path = Path(log_dir) / f"scraper_{datetime.now():%Y%m%d_%H%M%S}.log"
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"),
                  logging.StreamHandler()],
        force=True,
    )
    return log_path


def main(argv=None):
    args = parse_args(argv)
    log_path = setup_logging(args.log_dir, args.log_level)
    client = HttpClient(delay=args.delay)

    scrapers = []
    if "books" in args.sources:
        scrapers.append(BooksScraper(
            client, max_pages=args.max_pages,
            fetch_categories=not args.no_categories,
            fetch_details=args.with_details,
        ))
    if "quotes" in args.sources:
        scrapers.append(QuotesScraper(client, max_pages=args.max_pages))

    summary = run_pipeline(scrapers, args.output_dir, run_args=vars(args))

    print("\n=== Summary ===")
    for name, stats in summary["sources"].items():
        print(f"{name}: scraped={stats['scraped']} rejected={stats['rejected']} "
              f"duplicates={stats['duplicates_removed']} final={stats['final']} "
              f"(pages ok/failed: {stats['pages_fetched']}/{stats['pages_failed']})")
    print(f"Total final records: {summary['totals']['final']}")
    print(f"Checks: {summary['checks']}")
    print(f"Output: {args.output_dir}\nLog:    {log_path}")
    return 0 if summary["totals"]["final"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
if _name_ == "_main_":
    print("Starting the application via app.py...")
    main()