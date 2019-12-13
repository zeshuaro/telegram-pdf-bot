FROM python:3.8.0

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils=0.71.* libcairo2=1.16.* libpango-1.0-0=1.42.* \
    libpangocairo-1.0-0=1.42.* libgdk-pixbuf2.0-0=2.38.* libffi-dev=3.2.* shared-mime-info=1.10-* ocrmypdf=8.0.* \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /bot
COPY requirements.txt /bot/requirements.txt
RUN pip install -r requirements.txt
COPY . /bot

RUN pybabel compile -D pdf_bot -d locale

EXPOSE ${PORT}

ENV APP_URL ${APP_URL}
ENV TELE_TOKEN ${TELE_TOKEN}
ENV DEV_TELE_ID ${DEV_TELE_ID}
ENV GCP_CRED ${GCP_CRED}
ENV GCP_KEY ${GCP_KEY}
ENV SLACK_TOKEN ${SLACK_TOKEN}
ENV STRIPE_TOKEN ${STRIPE_TOKEN}

CMD ["python", "bot.py"]