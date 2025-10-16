## Urban Mobility Data Explorer — Summative

### What this is
This repo tracks the full end-to-end submission for the NYC taxi summative. It covers our raw pipeline, the cleaned data we ship to the database, the backend that exposes it, and the dashboard that tells the story. The goal is to make it trivial for a reviewer to clone the repo, rebuild the stack, and replay our analysis without pinging the team.

### Learning goals we are leaning on
- Apply data cleaning decisions on messy taxi trips and explain the trade-offs.
- Model the data in a relational layout that matches the assignment brief.
- Serve the processed records via a small API that the dashboard can lean on.
- Surface patterns about when, where, and how people move across the city.

### Dataset snapshot
- Source: official training split (`train.csv`) from the NYC TLC public dataset. Raw file lives under `data/train.csv`.
- Cleaning pipeline: see `data/data_cleaner.py` for the transformations, filters, derived features (speed, fare per km, distance buckets, rush-hour flags), and logging.
- Artefacts:
  - `data/cleaned_train_data.csv`: canonical cleaned export pushed into the warehouse.
  - `excluded_records.json`: sample of rows that failed validation, capped at 1k entries for sanity.
  - `cleaning_report.json`: run metadata, retention stats, and column data types for the cleaned output.

### Repo tour
- `data/` — raw file, cleaning script, cleaned export, helper notebooks.
- `backend/` — Flask API (`app.py`), environment loading, and query code targeting MySQL-compatible instances.
- `database/` — schema DDL (`schema.sql`) plus indexes and the denormalized view used by the frontend.
- `frontend/` — vanilla JS dashboard (`index.html`, `app.js`, `style.css`) and an offline mode (`dashboard_standalone.html`).
- `docs/` — architecture and ERD diagrams included with the final submission package.
- `logs/` — placeholder for runtime logs when you rerun the cleaner or API.

### Environment setup
```bash
# 1. Clone the repo
$ git clone <repo-url>
$ cd umde_summative

# 2. Python environment for data prep + backend
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r backend/requirements.txt

# 3. Node environment for the dashboard (optional but recommended)
$ cd frontend
$ npm install
```

### Backend: configuration and run
1. Copy `.env.example` (if present) to `.env` inside `backend/` or export the following vars:
   - `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
2. Create the database schema:
   ```bash
   $ mysql -u <user> -p < database/schema.sql
   ```
3. Load the cleaned data into the relational tables (seed script lives under `backend/` — run it after the schema step).
4. Start the API server:
   ```bash
   $ flask --app app run --host 0.0.0.0 --port 5000
   ```
5. Sanity check: hit `GET /api/health` to validate database connectivity.

### Frontend: dashboard quick start
1. Create a `.env` or config file to point to the backend URL if you are hosting it somewhere other than `http://localhost:5000/api`.
2. Start the dev server (using any static file server; e.g., `npm run dev` if using Vite or `npx serve .`).
3. Open `http://localhost:5173` (or the port you chose) to access the dashboard.
4. If you only have the data files, open `frontend/dashboard_standalone.html` directly in a browser; it uses JSON dumps instead of API calls.

### Algorithms and insight pipeline
- Custom ranking logic for rush-hour congestion: implemented manually in `backend/app.py` without relying on pandas groupby or SQL window shortcuts.
- Rolling outlier detection for fare anomalies: see the helper in `data/data_cleaner.py`.
- Derived metrics such as `trip_speed_kmh`, `fare_per_km`, and contextual buckets shipped to the warehouse for quick slicing.

### Dashboard features
- KPI cards for trip counts, duration, distance, and fare with month-over-month deltas.
- Interactive filters (time window, fare ceiling, distance ceiling, passenger count, borough).
- Charts powered by Chart.js: hourly volume line chart, speed by part of day bar chart, passenger mix doughnut, duration distribution, and a scatter plot for speed vs. fare anomalies.
- Insight feed that summarises noteworthy patterns returned by the insights endpoint.

### Logging and transparency
- Every run of the cleaner writes to `logs/` (timestamped JSON) so we can trace what the script saw.
- Excluded rows and derived feature definitions stay versioned to simplify audits.
- API logs use the standard Flask logger; align with deployment logging when needed.

### Deliverables checklist
- [ ] Video walkthrough link (add once recorded).
- [x] Architecture diagram (`docs/system_architecture_diagram.png`).
- [x] ERD (`docs/erd_diagram.png`).
- [x] Database schema file (`database/schema.sql`).
- [x] Cleaning report (`cleaning_report.json`).
- [ ] Technical PDF report (2–3 pages; to be exported from our final write-up).

### Future improvements if we keep going
- Move to a containerized stack (Docker Compose) for quicker onboarding.
- Tighten the schema by introducing dimensional tables for date/time and vendor metadata.
- Swap Chart.js for a deck.gl layer if we want pickup/dropoff map animations.
- Plug in a job scheduler (Airflow or Prefect) to automate nightly refreshes.

If anything feels off or you hit a broken instruction, open an issue so we can align updates with the grading rubric. Thanks for reviewing!