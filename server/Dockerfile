FROM python:3.11-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry==1.6.1

# Copy pyproject.toml and poetry.lock (if available)
COPY pyproject.toml ./
COPY poetry.lock* ./

# Configure poetry not to create a virtual environment
RUN poetry config virtualenvs.create false && \
  poetry install --no-interaction --no-ansi --no-dev

# Copy the application
COPY . .

EXPOSE 8000

CMD ["python", "-m", "app.main:start"]