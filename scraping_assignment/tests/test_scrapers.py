import unittest

from helpers import FakeClient, book_item, books_page, quote_item, quotes_page
from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper

HOME = "https://books.test/"
P2 = "https://books.test/catalogue/page-2.html"
P3 = "https://books.test/catalogue/page-3.html"


def three_page_books_site(skip=()):
    pages = {
        HOME: books_page(
            [book_item("Book One", "catalogue/one_1/index.html")],
            "catalogue/page-2.html"),
        P2: books_page(
            [book_item("Book Two", "two_2/index.html", rating="Five")],
            "page-3.html"),
        P3: books_page([book_item("Book Three", "three_3/index.html")]),
    }
    return {url: html for url, html in pages.items() if url not in skip}


class BooksScraperTests(unittest.TestCase):
    def test_follows_next_links_to_the_last_page(self):
        client = FakeClient(three_page_books_site())
        result = BooksScraper(client, start_url=HOME, fetch_categories=False).scrape()
        self.assertEqual(result.pages_fetched, 3)
        self.assertEqual(
            [r["name_or_title"] for r in result.records],
            ["Book One", "Book Two", "Book Three"])
        self.assertEqual(result.records[1]["source_url"],
                         "https://books.test/catalogue/two_2/index.html")
        self.assertEqual(result.records[1]["rating"], "Five")  # raw value

    def test_failed_page_is_skipped_and_crawl_continues(self):
        client = FakeClient(three_page_books_site(skip=(P2,)))
        result = BooksScraper(client, start_url=HOME, fetch_categories=False).scrape()
        self.assertEqual(result.pages_failed, 1)
        self.assertEqual(result.failed_urls, [P2])
        self.assertEqual([r["name_or_title"] for r in result.records],
                         ["Book One", "Book Three"])

    def test_two_consecutive_failures_stop_the_crawl(self):
        client = FakeClient(three_page_books_site(skip=(P2, P3)))
        result = BooksScraper(client, start_url=HOME, fetch_categories=False).scrape()
        self.assertEqual(result.pages_failed, 2)
        self.assertEqual(len(result.records), 1)

    def test_max_pages(self):
        client = FakeClient(three_page_books_site())
        result = BooksScraper(
            client, start_url=HOME, max_pages=2, fetch_categories=False).scrape()
        self.assertEqual(result.pages_fetched, 2)

    def test_missing_elements_do_not_crash(self):
        page = books_page([book_item("No Price", "np_1/index.html", price=None)])
        client = FakeClient({HOME: page})
        result = BooksScraper(client, start_url=HOME, fetch_categories=False).scrape()
        self.assertEqual(len(result.records), 1)
        self.assertIsNone(result.records[0]["price"])

    def test_category_enrichment(self):
        sidebar = (
            '<div class="side_categories"><ul><li><a href="x">Books</a><ul>'
            '<li><a href="catalogue/category/books/travel_2/index.html">'
            "\n  Travel\n</a></li></ul></li></ul></div>")
        home = books_page(
            [book_item("Book One", "catalogue/one_1/index.html")], sidebar=sidebar)
        category = books_page(
            [book_item("Book One", "../../../one_1/index.html")])
        client = FakeClient({
            HOME: home,
            "https://books.test/catalogue/category/books/travel_2/index.html": category,
        })
        result = BooksScraper(client, start_url=HOME).scrape()
        self.assertEqual(result.records[0]["category"], "Travel")
        self.assertEqual(result.extra_pages_fetched, 1)


class QuotesScraperTests(unittest.TestCase):
    def test_parses_quotes_and_paginates(self):
        home, page2 = "https://quotes.test/", "https://quotes.test/page/2/"
        client = FakeClient({
            home: quotes_page([quote_item("Be yourself.", "Oscar Wilde", ["life", "x"])],
                              "/page/2/"),
            page2: quotes_page([quote_item("Stay hungry.", "Steve Jobs", [])]),
        })
        result = QuotesScraper(client, start_url=home).scrape()
        self.assertEqual(result.pages_fetched, 2)
        self.assertEqual(len(result.records), 2)
        first = result.records[0]
        self.assertEqual(first["author"], "Oscar Wilde")
        self.assertEqual(first["tags"], ["life", "x"])
        self.assertEqual(result.records[1]["source_url"], page2)
        self.assertIsNone(first["price"])  # not applicable -> None, not invented

    def test_failed_first_page_uses_guessed_next_page(self):
        page2 = "https://quotes.test/page/2/"
        client = FakeClient(
            {page2: quotes_page([quote_item("Hi.", "Someone", ["a"])])})
        result = QuotesScraper(client, start_url="https://quotes.test/").scrape()
        self.assertEqual(result.pages_failed, 1)
        self.assertEqual(len(result.records), 1)


if __name__ == "__main__":
    unittest.main()
