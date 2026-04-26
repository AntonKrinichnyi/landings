FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default CMD — overridden in docker-compose to run migrations first
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
