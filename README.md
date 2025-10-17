## Urban Mobility Data Explorer — Summative

### What this is
This repo tracks the full end-to-end submission for the NYC taxi summative. It covers our raw pipeline, the cleaned data we ship to the database, the backend that exposes it, and the dashboard that tells the story. The goal is to make it trivial for a reviewer to clone the repo, rebuild the stack, and replay our analysis without pinging the team.

### Video Walkthrough
https://youtu.be/HVIKl4HwkhE

### Learning goals we are leaning on
- Apply data cleaning decisions on messy taxi trips and explain the trade-offs.
- Model the data in a relational layout that matches the assignment brief.
- Serve the processed records via a small API that the dashboard can lean on.
- Surface patterns about when, where, and how people move across the city.

### Dataset snapshot
- Source: official training split (`train.csv`) from the NYC TLC public dataset. Raw file lives under `data/train.csv`.
- Cleaning pipeline: see `scripts/data_cleaner.py` for the transformations, filters, derived features (speed, fare per km, distance buckets, rush-hour flags), and logging.
- Artefacts:
  - `data/cleaned_train_data.csv`: canonical cleaned export pushed into the warehouse.
  - `logs/excluded_records.json`: sample of rows that failed validation, capped at 1k entries for sanity.
  - `logs/cleaning_report.json`: run metadata, retention stats, and column data types for the cleaned output.

### Repo tour
- `data/` — raw file and cleaned export.
- `backend/` — Flask API (`app.py`), environment loading, and query code targeting MySQL-compatible instances.
- `database/` — schema DDL (`schema.sql`) and a denormalized view used by the API.
- `frontend/` — vanilla JS dashboard (`index.html`, `app.js`, `style.css`) and an offline mode (`dashboard_standalone.html`).
- `docs/` — architecture and ERD diagrams, plus API spec and technical report.
- `logs/` — placeholder for runtime logs when you rerun the cleaner or API.

### Quickstart (fully runnable)
```bash
# 0) Prerequisites
# - Python 3.10+
# - MySQL 8.x (macOS: brew install mysql && brew services start mysql)

# 1) Clone
git clone <repo-url>
cd umde_summative

# 2) Dataset: download train.zip and place CSV at data/train.csv
mkdir -p data
# (Extract your train.csv here so it exists as data/train.csv)

# 3) Python env + deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 4) Database schema
mysql -u <user> -p < database/schema.sql

# 5) Backend env
cp backend/.env.example backend/.env
# edit DB_* values in backend/.env

# 6) Cleaning (writes logs into ./logs if run from logs/)
mkdir -p logs
(cd logs && python ../scripts/data_cleaner.py)
# results: data/cleaned_train_data.csv, logs/excluded_records.json, logs/cleaning_report.json

# 7) Load cleaned data
python scripts/load_data.py --csv data/cleaned_train_data.csv --batch-size 2000

# 8) Run backend API
flask --app backend/app run --host 0.0.0.0 --port 5000
# verify: curl http://localhost:5000/api/health

# 9) Run frontend (new terminal)
cd frontend
run index.html with your live server
# open the printed URL; ensure API_BASE_URL in frontend/app.js points to http://localhost:5000/api
```

### Backend: configuration and run
1. Export the following vars:
   - `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
2. Create the database schema:
   ```bash
   $ mysql -u <user> -p < database/schema.sql
   ```
3. Load the cleaned data into the relational tables:
   ```bash
   $ python scripts/load_data.py --csv data/cleaned_train_data.csv --batch-size 2000
   ```
4. Start the API server:
   ```bash
   $ flask --app backend/app run --host 0.0.0.0 --port 5000
   ```
5. Sanity check: `GET /api/health` to validate database connectivity.

### Frontend: dashboard quick start
1. Ensure `API_BASE_URL` in `frontend/app.js` points to the backend (default `http://localhost:5000/api`).
2. Serve `frontend/` with any static server; e.g. `npx serve .` if you have node but liveserver works too.

### Documentation
- API spec: `docs/API_SPEC.yaml`
- Data dictionary: `docs/DATA_DICTIONARY.md`
- Technical report: `docs/TECHNICAL_REPORT.md`

### Deliverables checklist
- [x] Architecture diagram (`docs/system_architecture_diagram.png`).
- [x] ERD (`docs/erd_diagram.png`).
- [x] Database schema file (`database/schema.sql`).
- [x] Cleaning report (`logs/cleaning_report.json`).
- [x] API spec (`docs/API_SPEC.yaml`).
- [x] Technical report (`docs/TECHNICAL_REPORT.md`).

### Future improvements if we keep going
- Add `time_dimensions` and `trip_facts` tables; update loader and queries.
- Add backend alias endpoints to match current frontend paths.
- Containerize (Docker Compose) for quicker onboarding; add CI for lint + smoke tests.
