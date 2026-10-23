FROM python:3.12-slim

WORKDIR /app

ENV HF_HOME=/app/.hf

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_lg \
    && printf "enable_metrics=false\nuse_remote_inferencing=false\n" > /root/.guardrailsrc

COPY app ./app
COPY scripts ./scripts

# Test-only files (see tests/README.md) — not needed to run the service,
# but pytest needs them present in the image to find/collect anything.
COPY pytest.ini .
COPY tests ./tests

EXPOSE 8000

CMD ["uvicorn", "app.backend:app", "--host", "0.0.0.0", "--port", "8000"]
