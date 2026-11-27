FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Secrets (ANTHROPIC_API_KEY) and S3_BUCKET are passed at run time, never baked into the image.
EXPOSE 8000
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT:-8000} 'app:create_app()'"]
