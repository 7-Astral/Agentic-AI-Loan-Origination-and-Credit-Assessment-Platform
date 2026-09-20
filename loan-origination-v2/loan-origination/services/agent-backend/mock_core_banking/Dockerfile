FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mock_core_banking ./mock_core_banking

EXPOSE 9000

CMD ["uvicorn", "mock_core_banking.main:app", "--host", "0.0.0.0", "--port", "9000"]