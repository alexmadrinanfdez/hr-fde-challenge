from fastapi import FastAPI

from api.routers import calls, loads
from common.db import get_connection


app = FastAPI(title="Inbound Carrier Sales API")


app.include_router(loads.router)
app.include_router(calls.router)


@app.on_event("startup")
def startup_check():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
    except Exception as e:
        raise RuntimeError(f"Database connection failed during startup: {e}") from e


@app.get("/health")
def health_check():
    return {"status": "ok"}