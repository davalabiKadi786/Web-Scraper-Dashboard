"""Reusable cleaning helpers. Lenient by design: strict checks live in validation."""
import re
import unicodedata
from urllib.parse import urljoin, urlsplit, urlunsplit

import config

MISSING_TOKENS = {"", "n/a", "na", "none", "null", "nan", "-", "--"}
RATING_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}

_WHITESPACE = re.compile(r"\s+")  # also matches non-breaking spaces
_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff"), None)
_PRICE = re.compile(r"\d[\d,]*(?:\.\d+)?|\.\d+")
_QUOTE_PAIRS = {"\u201c": "\u201d", '"': '"'}


def clean_text(value):
    """Trim, collapse every kind of whitespace, drop zero-width chars."""
    if value is None:
        return None
    text = unicodedata.normalize("NFC", str(value)).translate(_ZERO_WIDTH)
    text = _WHITESPACE.sub(" ", text).strip()
    return text or None


def normalize_missing(value):
    """Clean text and turn placeholders such as 'N/A' or '-' into None."""
    text = clean_text(value)
    if text is None or text.casefold() in MISSING_TOKENS:
        return None
    return text


def strip_wrapping_quotes(text):
    """Remove ONE pair of surrounding quotation marks (the site wraps quotes)."""
    if text and len(text) >= 2 and _QUOTE_PAIRS.get(text[0]) == text[-1]:
        return clean_text(text[1:-1])
    return text


def parse_price(value):
    """'\u00a351.77' -> 51.77. None if missing; the cleaned text if unparseable."""
    text = normalize_missing(value)
    if text is None:
        return None
    match = _PRICE.search(text)
    if not match:
        return text  # validation will reject it as invalid_price
    number = round(float(match.group().replace(",", "")), 2)
    return -number if "-" in text[: match.start()] else number


def parse_rating(value):
    """'Three' -> 3, '4' -> 4. None if missing; cleaned text if unrecognised."""
    text = normalize_missing(value)
    if text is None:
        return None
    key = text.casefold()
    if key in RATING_WORDS:
        return RATING_WORDS[key]
    try:
        number = float(key)
    except ValueError:
        return text  # validation will reject it as invalid_rating
    return int(number) if number.is_integer() else number


def normalize_url(url, base=None):
    """Return a clean absolute http(s) URL, or None when it is not valid."""
    text = clean_text(url)
    if text is None:
        return None
    try:
        parts = urlsplit(urljoin(base, text) if base else text)
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        return None
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, "")
    )


def clean_tags(values):
    """List (or comma string) -> lower-cased, de-duplicated list, order kept."""
    if values is None:
        return []
    if isinstance(values, str):
        values = values.split(",")
    seen, result = set(), []
    for value in values:
        tag = clean_text(value)
        if tag is None:
            continue
        tag = tag.casefold()
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


def clean_record(raw):
    """Turn one raw scraped record into a cleaned record with the same columns."""
    source = clean_text(raw.get("source"))
    title = clean_text(raw.get("name_or_title"))
    if source == config.QUOTES_SOURCE:
        title = strip_wrapping_quotes(title)
    return {
        "source": source,
        "name_or_title": title,
        "category": normalize_missing(raw.get("category")),
        "price": parse_price(raw.get("price")),
        "rating": parse_rating(raw.get("rating")),
        "author": normalize_missing(raw.get("author")),
        "tags": clean_tags(raw.get("tags")),
        "availability": normalize_missing(raw.get("availability")),
        "description": normalize_missing(raw.get("description")),
        "source_url": normalize_url(raw.get("source_url")),
        "scraped_at": clean_text(raw.get("scraped_at")),
    }
