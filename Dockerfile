# Dockerfile
FROM python:3.12-slim

# System deps (ffmpeg is the key)
RUN apt-get update \
  && apt-get install -y --no-install-recommends ffmpeg \
  && rm -rf /var/lib/apt/lists/*

# App setup
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your code (ensures templates/ comes too)
COPY . .

# Gunicorn is production-ready; Flask dev server is not
ENV PYTHONUNBUFFERED=1
ENV PORT=5000
EXPOSE 5000

# Start the web server
CMD ["sh", "-c", "gunicorn -w 2 -k gthread -t 120 -b 0.0.0.0:${PORT} app:app"]
