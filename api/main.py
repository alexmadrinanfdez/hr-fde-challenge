from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from api.routers import carriers, calls, loads
from common.db import get_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
    except Exception as e:
        raise RuntimeError(f"Database connection failed during startup: {e}") from e
    yield


app = FastAPI(title="Inbound Carrier Sales API", lifespan=lifespan)


app.include_router(carriers.router)
app.include_router(loads.router)
app.include_router(calls.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}