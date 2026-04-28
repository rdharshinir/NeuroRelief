FROM python:3.10-slim AS base
WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code only
COPY app/ ./app/
COPY seed.py .

EXPOSE 8000

# Run with proxy headers for reverse proxy setups
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
