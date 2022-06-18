FROM --platform=linux/amd64 python:3.10.5-slim AS build

ARG COMMIT_HASH

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends git

RUN pip install -U pip && pip install poetry
COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.in-project true \
    && poetry install --no-dev --no-root --no-interaction
ENV PATH="/build/.venv/bin:${PATH}"

COPY locale locale/
RUN pybabel compile -D pdf_bot -d locale \
    && find locale -type f -name '*.po' -delete

FROM --platform=linux/amd64 python:3.10.5-slim AS deploy

ARG COMMIT_HASH
ENV SENTRY_RELEASE $COMMIT_HASH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ghostscript libpango-1.0-0 \
    libpangoft2-1.0-0 ocrmypdf poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=build /build/.venv/ /build/.venv/
ENV PATH="/build/.venv/bin:${PATH}"

COPY --from=build /build/locale /app/locale/
COPY pdf_bot pdf_bot/
COPY main.py .

CMD ["python", "main.py"]
