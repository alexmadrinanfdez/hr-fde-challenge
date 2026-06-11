# Inbound Carrier Sales

Backend API and reporting dashboard for inbound carrier call performance and freight matching.

## Project Structure

```text
api/           API (FastAPI)
common/        Shared database connection
dashboard/     Reporting dashboard (Streamlit)
scripts/       CSV import scripts
data/          Seed CSV files
schema.sql     PostgreSQL schema
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| GET | `/loads` | API key | List loads (supports query filters) |
| POST | `/calls` | API key | Record a call |

Pass `X-Api-Key` header for protected endpoints. 

## Setup

### Native

#### Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.template .env
```

Edit `.env` with your PostgreSQL connection string.

#### Database

```bash
createdb inbound_carrier_sales
psql -d inbound_carrier_sales -f schema.sql
python scripts/import_loads.py
python scripts/import_calls.py
```

Loads must be imported before calls (to satisfy foreign key checks).

#### API Server

```bash
uvicorn api.main:app --reload
```

Docs at `http://127.0.0.1:8000/docs`.

##### API Key

Generate a key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add it to `.env`:

```text
API_KEY=your_generated_key_here
```

Leave `API_KEY` empty to disable authentication during local development.

#### Dashboard

```bash
python -m streamlit run dashboard/app.py
```

Opens at `http://localhost:8501`.

### Container

#### Start services

```bash
docker compose up --build
```

#### Seed data

```bash
docker compose --profile seed up seed
```

#### Set the API key

Pass it via environment variable:

```bash
API_KEY=your_generated_key_here docker compose up --build
```

Or add it to a `.env` file in the project root (Docker Compose reads it automatically).

#### Services

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Dashboard | http://localhost:8501 |

## Notes

- The dashboard reads directly from PostgreSQL, not through the API.
- Import scripts shift timestamps using configurable anchor offsets to keep demo data current.
- Run Streamlit with `python -m streamlit` to avoid import path issues.