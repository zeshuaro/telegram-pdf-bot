FROM python:3.9.6

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils libcairo2 libpango-1.0-0 libpangoft2-1.0-0 \
    libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info ocrmypdf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /bot
COPY . /bot
RUN pip install -r requirements.txt

RUN pybabel compile -D pdf_bot -d locale

CMD exec gunicorn --bind :$PORT --workers 1 --threads 10 --timeout 0 "pdf_bot:create_app()"
