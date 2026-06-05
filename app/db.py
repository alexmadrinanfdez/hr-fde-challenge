import os

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


load_dotenv()

def get_database_url() -> str:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL is required. Set it in the environment or in a .env file."
        )
    return db_url

def get_connection():
    return psycopg.connect(get_database_url(), row_factory=dict_row)