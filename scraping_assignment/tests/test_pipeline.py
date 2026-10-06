import csv
import json
import tempfile
import unittest
from pathlib import Path

from helpers import FakeClient, book_item, books_page, quote_item, quotes_page
from pipeline import run_pipeline
from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper


class PipelineTests(unittest.TestCase):
    def test_end_to_end_counts_add_up(self):
        pages = {
            "https://books.test/": books_page([
                book_item("Example Book Title", "catalogue/a_1/index.html"),
                book_item("  EXAMPLE BOOK title ", "catalogue/a_2/index.html"),  # dup
                book_item("Cheap Book", "catalogue/b_3/index.html", price=None),  # bad
                book_item("Odd Rating", "catalogue/c_4/index.html", rating="Nine"),
                book_item("Good Book", "catalogue/d_5/index.html", price="\u00a312.50"),
            ]),
            "https://quotes.test/": quotes_page([
                quote_item("Be yourself.", "Oscar Wilde", ["Life"]),
                quote_item("be  yourself", "oscar wilde", ["life"]),  # dup
                quote_item("No author here.", "", []),                # bad
            ]),
        }
        client = FakeClient(pages)
        scrapers = [
            BooksScraper(client, start_url="https://books.test/",
                         fetch_categories=False),
            QuotesScraper(client, start_url="https://quotes.test/"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_pipeline(scrapers, tmp)

            books = summary["sources"]["Books to Scrape"]
            quotes = summary["sources"]["Quotes to Scrape"]
            self.assertEqual((books["scraped"], books["rejected"],
                              books["duplicates_removed"], books["final"]),
                             (5, 2, 1, 2))
            self.assertEqual((quotes["scraped"], quotes["rejected"],
                              quotes["duplicates_removed"], quotes["final"]),
                             (3, 1, 1, 1))
            self.assertEqual(books["rejection_reasons"],
                             {"missing_price": 1, "invalid_rating": 1})
            self.assertTrue(summary["checks"]["csv_rows_match_final_total"])
            self.assertTrue(
                summary["checks"]["scraped_equals_rejected_plus_duplicates_plus_final"])

            with open(Path(tmp) / "final_dataset.csv", encoding="utf-8-sig",
                      newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 3)
            self.assertEqual({r["source"] for r in rows},
                             {"Books to Scrape", "Quotes to Scrape"})
            good = next(r for r in rows if r["name_or_title"] == "Good Book")
            self.assertEqual((good["price"], good["rating"]), ("12.5", "3"))
            self.assertEqual(good["author"], "")  # not applicable -> empty

            for name in ("summary_report.json", "excluded_records.json"):
                self.assertTrue(json.loads((Path(tmp) / name).read_text("utf-8")))

    def test_crashing_source_does_not_stop_the_other(self):
        class Boom:
            name = "Broken Source"

            def scrape(self):
                raise RuntimeError("boom")

        client = FakeClient({"https://quotes.test/": quotes_page(
            [quote_item("Hello there.", "Someone", ["a"])])})
        scrapers = [Boom(), QuotesScraper(client, start_url="https://quotes.test/")]
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_pipeline(scrapers, tmp)
        self.assertIn("boom", summary["sources"]["Broken Source"]["scraper_error"])
        self.assertEqual(summary["totals"]["final"], 1)


if __name__ == "__main__":
    unittest.main()
