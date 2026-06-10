# Inbound Carrier Sales

Backend API and reporting dashboard for inbound carrier freight calls.

## Setup

### General

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.template .env
```

Edit `.env` with your PostgreSQL connection string.

### Database

```bash
createdb inbound_carrier_sales
psql -d inbound_carrier_sales -f schema.sql
python scripts/import_loads.py
python scripts/import_calls.py
```

Loads must be imported before calls (to satisfy foreign key checks).

### API

```bash
uvicorn app.main:app --reload
```
#### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/loads` | List loads (supports query filters) |
| POST | `/calls` | Record a call |

Docs at `http://127.0.0.1:8000/docs`.

### Dashboard

```bash
python -m streamlit run dashboard/app.py
```

Opens at `http://localhost:8501`.

## Project Structure

```text
app/           API (FastAPI)
common/        Shared database connection
dashboard/     Reporting dashboard (Streamlit)
scripts/       CSV import scripts
data/          Seed CSV files
schema.sql     PostgreSQL schema
```

## Notes

- The dashboard reads directly from PostgreSQL, not through the API.
- Import scripts shift timestamps using configurable anchor offsets to keep demo data current.
- Run Streamlit with `python -m streamlit` to avoid import path issues.