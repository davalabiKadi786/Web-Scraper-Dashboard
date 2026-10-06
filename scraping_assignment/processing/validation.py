"""Strict record checks. Rejected records are kept with their reasons."""
import math
from collections import Counter

import config
from processing.cleaning import normalize_url


def _is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def validate_record(record):
    """Return a list of reason codes. An empty list means the record is valid."""
    source = record.get("source")
    if source not in config.KNOWN_SOURCES:
        return ["unknown_source"]

    reasons = []
    for name in config.REQUIRED_FIELDS[source]:
        if record.get(name) in (None, ""):
            reasons.append(f"missing_{name}")

    price = record.get("price")
    if price is not None and not (_is_number(price) and price >= 0):
        reasons.append("invalid_price")

    rating = record.get("rating")
    if rating is not None:
        in_range = _is_number(rating) and config.RATING_MIN <= rating <= config.RATING_MAX
        if not in_range:
            reasons.append("invalid_rating")

    url = record.get("source_url")
    if url and normalize_url(url) is None:
        reasons.append("invalid_source_url")
    return reasons


def validate_records(records):
    """Split records into (valid, rejected). rejected = [{record, reasons}]."""
    valid, rejected = [], []
    for record in records:
        reasons = validate_record(record)
        if reasons:
            rejected.append({"record": record, "reasons": reasons})
        else:
            valid.append(record)
    return valid, rejected


def count_reasons(rejected):
    return Counter(reason for item in rejected for reason in item["reasons"])
