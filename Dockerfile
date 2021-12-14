FROM python:3.10.1

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils libcairo2 libpango-1.0-0 libpangoft2-1.0-0 \
    libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info ocrmypdf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python - --version 1.1.12

ENV PATH="${PATH}:/root/.local/bin"
WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --no-dev --no-root --no-interaction

COPY locale locale/
RUN pybabel compile -D pdf_bot -d locale

COPY pdf_bot pdf_bot/
CMD exec gunicorn --bind :$PORT --workers 1 --threads 10 --timeout 0 "pdf_bot:create_app()"
