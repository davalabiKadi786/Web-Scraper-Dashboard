# AI Usage

## Tools used
* Claude (Anthropic) - generated the first full draft of the project from the
  assignment PDF.

## What it was used for
* Project structure, data model and pipeline design.
* Scrapers, cleaning, validation, deduplication, logging and retry code.
* Unit tests and the README.

## Representative prompt
"Create a project based on the company requirements (assignment PDF). Give the code
in one PDF file that I can run in VS Code."

## AI-assisted parts
All of the code, tests and documentation in this submission was generated with AI
assistance. I (the candidate) must review and be able to explain every module.

## Issues found in AI output / changes after review
* The first file-creation command used a shell shortcut that did not create the
  sub-folders; it was noticed and the files were re-created.
* A design choice to review: category is collected from the 50 category pages instead
  of 1,000 book pages, to keep the run short (see README).
* <Add your own findings here after you run and read the code. Example: anything you
  changed, any selector you had to fix on the live site.>

## How it was verified
* 31 offline unit tests (cleaning, validation, deduplication, scrapers with fake HTML,
  retry logic against a local test server, full pipeline).
* An end-to-end run of `main.py` against a local mock server.
* The Books to Scrape home page structure was checked against the live site
  (1,000 results, 50 pages, 50 categories, next link, title attribute, price format).
* NOT done by the AI: a complete live run against both websites (no internet access
  in the build environment). Quote-site selectors come from the standard layout of
  that site.
* <Add after YOUR live run: rows in the CSV, the summary_report.json totals, and
  a few records you compared by hand with the website.>
