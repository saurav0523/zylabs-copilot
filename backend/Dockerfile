FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create the backend directory structure so imports like `from backend.db...` work
COPY . /app/backend

# Switch working directory to where alembic.ini and main.py live
WORKDIR /app/backend

# Tell Python that the root module directory is /app
ENV PYTHONPATH=/app

EXPOSE 8000

# Start script running migrations and the app
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
