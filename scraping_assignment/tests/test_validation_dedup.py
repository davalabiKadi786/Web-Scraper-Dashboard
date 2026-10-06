import unittest

import config
from processing.deduplication import deduplicate, normalize_for_key, record_key
from processing.validation import validate_record, validate_records


def book(**overrides):
    record = {name: None for name in config.SCHEMA}
    record.update(
        source=config.BOOKS_SOURCE, name_or_title="Example Book Title", price=10.0,
        rating=3, source_url="https://books.toscrape.com/catalogue/x_1/index.html",
        scraped_at="2026-01-01T00:00:00+00:00", tags=[],
    )
    record.update(overrides)
    return record


def quote(**overrides):
    record = {name: None for name in config.SCHEMA}
    record.update(
        source=config.QUOTES_SOURCE, name_or_title="Be yourself.", author="Oscar Wilde",
        source_url="https://quotes.toscrape.com/", tags=["life"],
        scraped_at="2026-01-01T00:00:00+00:00",
    )
    record.update(overrides)
    return record


class ValidationTests(unittest.TestCase):
    def test_valid_records(self):
        self.assertEqual(validate_record(book()), [])
        self.assertEqual(validate_record(quote()), [])

    def test_rejections(self):
        self.assertEqual(validate_record(book(source="Other")), ["unknown_source"])
        self.assertIn("missing_name_or_title", validate_record(book(name_or_title=None)))
        self.assertIn("missing_price", validate_record(book(price=None)))
        self.assertIn("invalid_price", validate_record(book(price="free")))
        self.assertIn("invalid_price", validate_record(book(price=-1.0)))
        self.assertIn("invalid_rating", validate_record(book(rating=9)))
        self.assertIn("invalid_rating", validate_record(book(rating="Seven")))
        self.assertIn("missing_source_url", validate_record(book(source_url=None)))
        self.assertIn("invalid_source_url", validate_record(book(source_url="ftp://x")))
        self.assertIn("missing_author", validate_record(quote(author=None)))

    def test_validate_records_splits(self):
        valid, rejected = validate_records([book(), book(price=None)])
        self.assertEqual(len(valid), 1)
        self.assertEqual(rejected[0]["reasons"], ["missing_price"])


class DeduplicationTests(unittest.TestCase):
    def test_normalize_for_key(self):
        variants = ["Example Book Title", " Example Book Title ",
                    "EXAMPLE BOOK TITLE", "Example, Book  Title!"]
        self.assertEqual({normalize_for_key(v) for v in variants},
                         {"example book title"})

    def test_equivalent_books_are_duplicates(self):
        records = [book(), book(name_or_title="  EXAMPLE book title "),
                   book(name_or_title="Another Book")]
        unique, duplicates = deduplicate(records)
        self.assertEqual(len(unique), 2)
        self.assertEqual(len(duplicates), 1)

    def test_same_title_different_price_is_kept(self):
        unique, duplicates = deduplicate([book(), book(price=11.0)])
        self.assertEqual((len(unique), len(duplicates)), (2, 0))

    def test_quotes_use_text_and_author(self):
        records = [quote(), quote(name_or_title="BE YOURSELF"), quote(author="Other")]
        unique, duplicates = deduplicate(records)
        self.assertEqual((len(unique), len(duplicates)), (2, 1))

    def test_sources_never_collide(self):
        self.assertNotEqual(record_key(book(name_or_title="x", price=None)),
                            record_key(quote(name_or_title="x", author=None)))


if __name__ == "__main__":
    unittest.main()
