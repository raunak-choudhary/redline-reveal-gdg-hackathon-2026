FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy backend project files
COPY backend/pyproject.toml ./pyproject.toml

# Install dependencies (no dev deps)
RUN uv pip install --system --no-cache \
    fastapi \
    "uvicorn[standard]" \
    websockets \
    httpx \
    python-dotenv \
    google-adk \
    fastmcp \
    pydantic \
    google-cloud-bigquery

# Copy all source
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Set working directory to backend
WORKDIR /app/backend

# Environment
ENV PYTHONPATH=/app/backend
ENV GOOGLE_GENAI_USE_VERTEXAI=0

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
