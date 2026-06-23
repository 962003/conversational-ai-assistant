# Build from the repository root so we can include both the backend and the KB:
#   docker build -t acme-support-ai .
#   docker run -p 8000:8000 -e GEMINI_API_KEY=... acme-support-ai
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY knowledge_base ./knowledge_base

ENV KNOWLEDGE_BASE_DIR=/app/knowledge_base
ENV DATABASE_PATH=/app/data/analytics.db
ENV GEMINI_MODEL=gemini-2.5-flash

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
