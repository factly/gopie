FROM python:3.12 as requirements-stage
WORKDIR /tmp
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY uv.lock* ./pyproject.toml ./.python-version /tmp/
RUN uv export --no-hashes --format requirements-txt -o requirements.txt

FROM python:3.12 as build-stage
RUN python -m venv /code/venv
ENV PATH="/code/venv/bin:$PATH"
COPY --from=requirements-stage /tmp/requirements.txt requirements.txt
RUN pip install -r requirements.txt

FROM python:3.12
WORKDIR /code
COPY --from=build-stage /code/venv /code/venv
ENV PATH="/code/venv/bin:$PATH"
COPY . .