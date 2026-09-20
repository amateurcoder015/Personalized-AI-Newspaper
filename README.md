# Personal AI Daily Newspaper

An automated, AI-powered daily executive newspaper that ingests RSS news feeds, cleans and deduplicates articles, clusters event stories, ranks content based on personal interests and company watchlists, synthesizes executive briefs using LLM providers (FreeLLMAPI / OpenAI compatible), generates a modern digital HTML newspaper edition, archives previous editions in SQLite, and delivers via Email/WhatsApp.

---

## 📰 Today's Edition Preview — 20 September 2026

The generated PDF edition features a 14-section modern executive publication design rendered dynamically:

| Page 1: Cover & Market Snapshot | Page 2: What Changed & India | Page 3: Financial Markets | Page 4: Precious Metals & Sectors |
| :---: | :---: | :---: | :---: |
| ![Page 1](docs/images/pdf_page_1.png) | ![Page 2](docs/images/pdf_page_2.png) | ![Page 3](docs/images/pdf_page_3.png) | ![Page 4](docs/images/pdf_page_4.png) |

| Page 5: Companies & Watchlist | Page 6: AI & Tech / GitHub Finds | Page 7: Connect The Dots | Page 8: Finance Concept of the Day |
| :---: | :---: | :---: | :---: |
| ![Page 5](docs/images/pdf_page_5.png) | ![Page 6](docs/images/pdf_page_6.png) | ![Page 7](docs/images/pdf_page_7.png) | ![Page 8](docs/images/pdf_page_8.png) |

---


## Key Features

- **Automated Collection**: RSS feed collection from business, technology, economy, and global finance feeds.
- **Multi-Level Deduplication**: URL hash checking, title similarity matching (RapidFuzz), and event story clustering.
- **Personalized Ranking**: Scoring based on global importance + personal relevance (company watchlist matches for Reliance, TCS, HDFC Bank, NVIDIA, Microsoft, Apple, etc.).
- **LLM Editorial Engine**: Replaceable LLM provider abstraction layer generating 2-4 sentence summaries, Why-It-Matters insights, Finance Concept of the Day, and What-to-Watch items.
- **Modern Digital Newspaper Design**: Jinja2 rendered HTML daily brief with serif headlines, dark/light theme accents, market ticker bar, and clickable original source links.
- **Delivery Adapters**: HTML Email delivery via SMTP and optional WhatsApp notifications.
- **Zero-Lock-in Architecture**: Easily configurable via `config.yaml` and `.env`.

---

## Directory Structure

```
Personalized-newspaper/
├── app/
│   ├── collectors/       # RSS and Web collectors
│   ├── processing/       # Cleaner, Deduplicator, Story Clusterer, Ranker
│   ├── llm/              # LLMProvider abstraction, FreeLLMAPI, Prompts, LLMEditor
│   ├── newspaper/        # Jinja2 Generator, newspaper.html template, style.css
│   ├── delivery/         # Email & WhatsApp delivery adapters
│   ├── database/         # SQLite models & DatabaseManager
│   ├── config.py         # Config loader
│   └── pipeline.py       # Orchestration pipeline
├── data/                 # SQLite database & HTML editions archive
├── tests/                # Automated Pytest suite
├── scripts/              # Automation cron runner
├── config.yaml           # User interests, watchlist, feeds & scoring weights
├── .env.example          # Environment variable template
├── main.py               # CLI entrypoint
└── requirements.txt      # Dependencies
```

---

## Quick Start

### 1. Setup Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Credentials & Preferences
Copy `.env.example` to `.env` and fill in your options:
```bash
cp .env.example .env
```

Edit `config.yaml` to customize your topic interests, watchlist companies, and RSS feeds.

### 3. Run Pipeline (Dry Run Mode)
Run the pipeline locally without sending emails:
```bash
python3 main.py --dry-run
```
The generated HTML newspaper will be saved to `data/editions/EDITION_YYYYMMDD.html`.

---

## CLI Usage Flags

- `python3 main.py --dry-run` : Execute complete pipeline and generate HTML edition locally.
- `python3 main.py --collect` : Run RSS news collection only and store in SQLite.
- `python3 main.py --generate` : Generate newspaper HTML from stored articles.
- `python3 main.py --send` : Deliver the latest edition via configured Email/WhatsApp.
- `python3 main.py --test-email` : Verify SMTP email login credentials.
- `python3 main.py --test-llm` : Test connection to configured LLM endpoint.

---

## Running Unit Tests

Run the full pytest suite:
```bash
pytest tests/ -v
```

---

## Daily Automation (macOS / Linux cron)

To run the pipeline every morning at 7:00 AM:
```bash
crontab -e
```
Add line:
```cron
0 7 * * * /path/to/Personalized-newspaper/scripts/daily_cron.sh
```
