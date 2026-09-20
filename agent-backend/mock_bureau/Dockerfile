FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mock_bureau ./mock_bureau

EXPOSE 9000

CMD ["uvicorn", "mock_bureau.main:app", "--host", "0.0.0.0", "--port", "9000"]
