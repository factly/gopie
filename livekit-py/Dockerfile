FROM python:3.11-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
COPY uv.lock ./
COPY .python-version ./

# Copy application code
COPY main.py .

# Run the application
CMD ["uv", "run", "main.py", "start"]
