import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader


api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)


async def verify_api_key(key: str | None = Security(api_key_header)):
    api_key = os.environ.get("API_KEY", "")
    if not api_key:
        return
    if key != api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")