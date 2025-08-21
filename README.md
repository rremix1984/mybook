# Site Crawler

Python project that crawls `https://jhx.553882.xyz/` collecting URL, screenshot, page
metadata and summary into a compact Word document. Supports full and incremental
runs with change tracking in a local SQLite database.

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
python main.py --mode full            # first run: full crawl
python main.py                        # subsequent incremental run
python main.py --max-pages 10         # limit pages
```

Outputs are written to `output/` with screenshots in
`output/screenshots/` and Word documents named
`site-digest-YYYYMMDD-HHMM.docx`.

Logs are stored in `logs/` (if any), and crawl state is recorded in
`crawl.db`.
