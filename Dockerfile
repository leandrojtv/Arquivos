# Dockerfile for Flask cadastro app
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    PORT=8000

# JRE necessário para carregar drivers JDBC (ex.: Teradata)
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/drivers/teradata

EXPOSE 8000

CMD ["sh", "-c", "flask run --host=0.0.0.0 --port=${PORT:-8000}"]
