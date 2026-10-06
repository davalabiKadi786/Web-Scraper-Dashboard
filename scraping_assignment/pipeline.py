"""Orchestrates: scrape -> clean -> validate -> deduplicate -> consolidate -> save."""
import csv
import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import config
from processing.cleaning import clean_record
from processing.deduplication import deduplicate
from processing.validation import validate_records
from scrapers.base_scraper import ScrapeResult

log = logging.getLogger(__name__)


def consolidate(records):
    """One common row layout for every source (CSV-ready, None -> empty)."""
    rows = []
    for record in records:
        row = {name: record.get(name) for name in config.SCHEMA}
        row["tags"] = config.TAG_SEPARATOR.join(record.get("tags") or [])
        rows.append({k: ("" if v is None else v) for k, v in row.items()})
    return rows


def write_csv(rows, path):
    # utf-8-sig so Excel shows pound signs and accents correctly
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=config.SCHEMA)
        writer.writeheader()
        writer.writerows(rows)


def count_csv_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _source_stats(result, cleaned, rejected, duplicates, unique, clean_failures):
    name = result.source
    rejected_here = [r for r in rejected if r["record"].get("source") == name]
    reasons = Counter(x for r in rejected_here for x in r["reasons"])
    return {
        "pages_fetched": result.pages_fetched,
        "pages_failed": result.pages_failed,
        "supporting_pages_fetched": result.extra_pages_fetched,
        "supporting_pages_failed": result.extra_pages_failed,
        "failed_urls": result.failed_urls,
        "parse_errors": result.parse_errors,
        "scraper_error": result.error,
        "scraped": len(result.records),
        "cleaned": len(result.records) - clean_failures[name],
        "rejected": len(rejected_here),
        "rejection_reasons": dict(reasons),
        "duplicates_removed": sum(
            1 for d in duplicates if d["record"].get("source") == name
        ),
        "final": sum(1 for r in unique if r.get("source") == name),
    }


def run_pipeline(scrapers, output_dir, run_args=None):
    started = datetime.now(timezone.utc)
    timer = time.perf_counter()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Scrape - a crashing source must not stop the other source
    results = []
    for scraper in scrapers:
        log.info("=== Scraping %s ===", scraper.name)
        try:
            results.append(scraper.scrape())
        except Exception as exc:
            log.exception("Scraper %s crashed; continuing", scraper.name)
            results.append(ScrapeResult(source=scraper.name, error=repr(exc)))

    # 2. Clean
    log.info("=== Cleaning ===")
    cleaned, clean_rejected = [], []
    clean_failures = Counter()
    for result in results:
        for raw in result.records:
            try:
                cleaned.append(clean_record(raw))
            except Exception:
                log.exception("Cleaning failed for %s", raw.get("source_url"))
                clean_failures[result.source] += 1
                clean_rejected.append({"record": raw, "reasons": ["cleaning_error"]})

    # 3. Validate
    log.info("=== Validating %d records ===", len(cleaned))
    valid, rejected = validate_records(cleaned)
    rejected.extend(clean_rejected)
    for item in rejected:
        log.warning("Rejected %s: %s", item["record"].get("source_url"), item["reasons"])

    # 4. Deduplicate
    log.info("=== Deduplicating %d valid records ===", len(valid))
    unique, duplicates = deduplicate(valid)
    for item in duplicates:
        log.info("Duplicate removed: %r", item["record"].get("name_or_title"))

    # 5. Consolidate + save
    rows = consolidate(unique)
    csv_path = output_dir / "final_dataset.csv"
    write_csv(rows, csv_path)
    csv_rows = count_csv_rows(csv_path)

    sources = {
        r.source: _source_stats(r, cleaned, rejected, duplicates, unique, clean_failures)
        for r in results
    }
    totals = {
        key: sum(s[key] for s in sources.values())
        for key in ("scraped", "cleaned", "rejected", "duplicates_removed", "final")
    }
    reconciles = all(
        s["scraped"] == s["rejected"] + s["duplicates_removed"] + s["final"]
        for s in sources.values()
    )
    finished = datetime.now(timezone.utc)
    summary = {
        "run": {
            "started_at": started.isoformat(timespec="seconds"),
            "finished_at": finished.isoformat(timespec="seconds"),
            "duration_seconds": round(time.perf_counter() - timer, 2),
            "arguments": run_args or {},
        },
        "sources": sources,
        "totals": totals,
        "checks": {
            "scraped_equals_rejected_plus_duplicates_plus_final": reconciles,
            "csv_rows": csv_rows,
            "csv_rows_match_final_total": csv_rows == totals["final"] == len(unique),
        },
    }
    with open(output_dir / "summary_report.json", "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
    with open(output_dir / "excluded_records.json", "w", encoding="utf-8") as handle:
        json.dump(
            {"rejected": rejected, "duplicates": duplicates},
            handle, indent=2, ensure_ascii=False,
        )
    log.info("Done: %s", totals)
    return summary
