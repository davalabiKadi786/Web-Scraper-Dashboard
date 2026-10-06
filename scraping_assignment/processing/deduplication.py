"""Duplicate detection based on normalised key fields (see config.DEDUP_KEYS)."""
import hashlib
import re
import unicodedata

import config

_NON_WORD = re.compile(r"[\W_]+")


def normalize_for_key(value):
    """Case-fold, NFKC-normalise, drop punctuation and collapse spaces.

    '  Example Book Title ', 'EXAMPLE BOOK TITLE' and 'Example, Book Title!'
    all become 'example book title'.
    """
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    return _NON_WORD.sub(" ", text).strip()


def record_key(record):
    """SHA-256 fingerprint of the source plus the source's key fields."""
    fields = config.DEDUP_KEYS.get(record.get("source"), ("name_or_title",))
    parts = [str(record.get("source"))]
    parts += [normalize_for_key(record.get(name)) for name in fields]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def deduplicate(records):
    """Keep the first record of each key. Returns (unique, duplicates).

    Each duplicate entry says which kept record it duplicates, so removals
    can be audited.
    """
    first_seen, unique, duplicates = {}, [], []
    for record in records:
        key = record_key(record)
        if key in first_seen:
            duplicates.append(
                {
                    "record": record,
                    "duplicate_of": first_seen[key]["source_url"],
                    "key": key,
                }
            )
        else:
            first_seen[key] = record
            unique.append(record)
    return unique, duplicates
