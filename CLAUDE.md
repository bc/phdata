# CLAUDE.md

## Project Overview

This is an **interview challenge project** for a Machine Learning Principal Solutions Architect role at phData. It analyzes phData's 76 published case studies to identify business growth opportunities, skills alignment, and strategic recommendations. The project includes a web scraper, search engine, scoring algorithms, and an interactive analytics portal.

## Repository Structure

```
phdata/
├── web/                          # Web application (FastAPI + React SPA)
│   ├── app.py                    # FastAPI backend (search API, case study endpoints)
│   └── static/
│       ├── index.html            # SPA entry point
│       ├── app.jsx               # React application (dashboard, search, cart, analytics)
│       ├── styles.css            # Design system (navy/teal palette)
│       ├── ml-framework.md       # Technical ML framework documentation
│       └── logos/                # Client company logos
├── scraper.py                    # Scrapes phData case studies from phdata.io
├── search_engine.py              # BM25 + FTS5 hybrid search engine
├── analyze_fit.py                # Scores case studies against candidate profile
├── update_db.py                  # Populates SQLite DB with case study content
├── client_growth_analysis.py     # Client base growth opportunity analysis
├── phdata_cases.db               # SQLite database (76 case studies)
├── clients/                      # Client data directories
├── .claude/                      # Claude skills (deep-research, grab-logo)
├── SUMMARY.md                    # Executive summary of analysis
├── challenge_description.md      # Original interview challenge brief
├── top_10_interesting_case_studies.md
├── top_5_contribution_fit.md
├── client_growth_strategy.md
├── correspondence-tracker.html   # Interactive dashboard
└── presentation*.html            # Slide presentations
```

## Tech Stack

### Backend
- **Python 3** (no formal package manager — scripts run directly)
- **FastAPI** — web framework for API and static file serving
- **SQLite** — database with FTS5 virtual table for full-text search
- **rank-bm25** — BM25 search algorithm
- **requests** + **beautifulsoup4** — web scraping
- No `requirements.txt` — install dependencies manually: `pip install fastapi uvicorn rank-bm25 requests beautifulsoup4`

### Frontend
- **React 18** — loaded via CDN (no build step)
- **Babel** — in-browser JSX transpilation
- **Leaflet.js** — mapping library
- **Inter** — primary font (Google Fonts)
- Custom CSS design system with CSS variables

## Running the Application

```bash
# Start the web portal (runs on http://localhost:8000)
cd web && python app.py

# Run interactive CLI search
python search_engine.py

# Run analysis scripts
python analyze_fit.py
python client_growth_analysis.py

# Scrape/update case studies
python scraper.py
python update_db.py
```

## Database

- **File:** `phdata_cases.db` (SQLite)
- **Tables:** `case_studies` (main), FTS5 virtual table for search, `google_results` for external data
- **Records:** 76 case studies scraped from phdata.io

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/search?q=...` | BM25 search across case studies |
| `GET /api/case-studies` | List all case studies |
| `GET /api/stats` | Aggregate statistics |
| `GET /api/brian-fit` | Skills alignment scoring |
| `GET /` | Serves React SPA |

## Code Conventions

- **Python:** PEP 8 style, 4-space indentation
- **React:** Functional components with hooks, JSX via Babel
- **CSS:** Custom properties for theming (navy `#091e2c`, teal `#1f7a8f`)
- No linters, formatters, or pre-commit hooks are configured
- No automated tests exist

## Key Design Decisions

- **No build step for frontend** — React and Babel loaded from CDN for simplicity
- **SQLite over external DB** — single-file database for portability
- **BM25 + FTS5 hybrid search** — BM25 for ranking quality, FTS5 as fallback
- **All-in-one FastAPI server** — serves both API and static frontend

## Things to Know

- This is a self-contained project with no external infrastructure dependencies
- The database file (`phdata_cases.db`) is checked into the repo
- There is no CI/CD pipeline, Dockerfile, or deployment configuration
- HTML presentation files are generated artifacts, not source files
- The `.claude/skills/` directory contains Claude Code skills (deep-research, grab-logo) that are tooling, not part of the application
