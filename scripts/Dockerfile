FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/
COPY data/ ./data/

CMD ["sh", "-c", "python scripts/import_loads.py && python scripts/import_calls.py"]