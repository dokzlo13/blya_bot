# syntax=docker/dockerfile:1

FROM python:3.12.7-bookworm

ARG MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"
ARG ENVIRONMENT
ENV ENVIRONMENT=${ENVIRONMENT:-production}
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/models
WORKDIR /app

RUN pip install --upgrade pip && pip install -U pip poetry==1.8.3
RUN poetry config virtualenvs.create false

RUN apt-get update && apt-get install --no-install-recommends --yes \
    wget \
    zip \
    unzip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Forcing certificates
RUN wget -P /usr/local/share/ca-certificates/cacert.org http://www.cacert.org/certs/root.crt http://www.cacert.org/certs/class3.crt && update-ca-certificates

RUN wget -O /app/models/vosk-model.zip ${MODEL_URL} \
    && unzip /app/models/vosk-model.zip -d /app/models/ \
    && rm /app/models/vosk-model.zip \
    # Extract models path automatically
    && extracted_folder=$(find /app/models/ -mindepth 1 -maxdepth 1 -type d) \
    && echo "export RECOGNITION_ENGINE_OPTIONS='{\"model_path\": \"$extracted_folder\"}'" > /app/models/config.sh;

COPY poetry.lock /app
COPY pyproject.toml /app

RUN poetry install --no-dev --no-root -E "vosk" -E "pymorphy"\
    && if [ "$ENVIRONMENT" = "development" ]; then poetry install --all-extras; fi

ENV RECOGNITION_ENGINE="vosk"
ADD fixtures /app/fixtures
ADD blya_bot /app/blya_bot

ENV PATH="/app:${PATH}"
# Apply env with current model path
CMD ["/bin/bash", "-c", "source /app/models/config.sh && python -m blya_bot"]
