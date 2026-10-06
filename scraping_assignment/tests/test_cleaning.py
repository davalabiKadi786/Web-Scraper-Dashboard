import unittest

from processing import cleaning as c


class CleaningTests(unittest.TestCase):
    def test_clean_text_collapses_whitespace_and_nbsp(self):
        self.assertEqual(c.clean_text("  A\u00a0 Light \n in\tthe Attic  "),
                         "A Light in the Attic")
        self.assertIsNone(c.clean_text("   "))
        self.assertIsNone(c.clean_text(None))

    def test_normalize_missing(self):
        for value in ("N/A", " none ", "-", "", None):
            self.assertIsNone(c.normalize_missing(value))
        self.assertEqual(c.normalize_missing(" Poetry "), "Poetry")

    def test_parse_price(self):
        self.assertEqual(c.parse_price("\u00a351.77"), 51.77)
        self.assertEqual(c.parse_price("\u00c2\u00a351.77"), 51.77)  # mojibake
        self.assertEqual(c.parse_price(" \u00a3 1,234.50 "), 1234.5)
        self.assertEqual(c.parse_price("-\u00a35.00"), -5.0)
        self.assertIsNone(c.parse_price(None))
        self.assertEqual(c.parse_price("free"), "free")  # left for validation

    def test_parse_rating(self):
        self.assertEqual(c.parse_rating("Three"), 3)
        self.assertEqual(c.parse_rating(" FIVE "), 5)
        self.assertEqual(c.parse_rating("4.0"), 4)
        self.assertIsNone(c.parse_rating(None))
        self.assertEqual(c.parse_rating("Seven"), "Seven")

    def test_normalize_url(self):
        self.assertEqual(
            c.normalize_url("../a/index.html", "https://Books.toscrape.com/x/y.html"),
            "https://books.toscrape.com/a/index.html",
        )
        self.assertIsNone(c.normalize_url("javascript:void(0)"))
        self.assertIsNone(c.normalize_url("not a url"))
        self.assertIsNone(c.normalize_url(None))

    def test_clean_tags(self):
        self.assertEqual(c.clean_tags([" Love ", "love", "", "Life "]), ["love", "life"])
        self.assertEqual(c.clean_tags(None), [])

    def test_strip_wrapping_quotes_only_removes_one_pair(self):
        self.assertEqual(c.strip_wrapping_quotes("\u201cHello.\u201d"), "Hello.")
        self.assertEqual(c.strip_wrapping_quotes("It's fine"), "It's fine")

    def test_clean_record_quote(self):
        raw = {"source": "Quotes to Scrape", "name_or_title": "\u201c Hi  there \u201d",
               "author": " Jane ", "tags": ["A", "a"], "price": None,
               "source_url": "https://quotes.toscrape.com/page/2/",
               "scraped_at": "2026-01-01T00:00:00+00:00"}
        cleaned = c.clean_record(raw)
        self.assertEqual(cleaned["name_or_title"], "Hi there")
        self.assertEqual(cleaned["author"], "Jane")
        self.assertEqual(cleaned["tags"], ["a"])
        self.assertIsNone(cleaned["price"])


if __name__ == "__main__":
    unittest.main()
