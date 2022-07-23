# syntax = docker/dockerfile:1.0-experimental

FROM python:3.10.1-slim-buster

ARG ENVIRONMENT
ENV ENVIRONMENT=${ENVIRONMENT:-production}
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/models
WORKDIR /app

RUN pip install -U pip poetry==1.1.14
RUN poetry config virtualenvs.create false

RUN apt-get update && apt-get install --no-install-recommends --yes \
    wget \
    zip \
    unzip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN wget -O /app/models/vosk-model-small-ru-0.22.zip https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip \
    && unzip '/app/models/vosk-model-small-ru-0.22.zip' -d /app/models/ && rm /app/models/vosk-model-small-ru-0.22.zip || true;
ENV VOSK_MODEL_PATH="/app/models/vosk-model-small-ru-0.22"

COPY poetry.lock /app
COPY pyproject.toml /app

RUN poetry install --no-dev --no-root \
    && if [ "$ENVIRONMENT" = "development" ]; then poetry install; fi

ADD blya_bot /app/blya_bot

ENV PATH="/app:${PATH}"
CMD ["python", "-m", "blya_bot"]
