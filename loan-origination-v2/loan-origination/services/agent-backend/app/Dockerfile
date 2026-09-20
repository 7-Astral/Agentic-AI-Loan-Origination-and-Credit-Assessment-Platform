FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# Test-only files (see tests/README.md) — not needed to run the service,
# but pytest needs them present in the image to find/collect anything.
COPY pytest.ini .
COPY tests ./tests

EXPOSE 8000

CMD ["uvicorn", "app.backend:app", "--host", "0.0.0.0", "--port", "8000"]