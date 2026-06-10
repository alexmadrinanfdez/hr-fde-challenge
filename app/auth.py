import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader


API_KEY = os.environ.get("API_KEY", "")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(key: str = Security(api_key_header)):
    if not API_KEY:
        return
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")