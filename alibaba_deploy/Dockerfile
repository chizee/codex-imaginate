FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run the web server
CMD ["uvicorn", "web_ui.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]