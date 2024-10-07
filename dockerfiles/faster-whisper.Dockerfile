# syntax=docker/dockerfile:1

FROM python:3.12.7-bookworm

ARG MODEL="small"
ARG LANG="ru"
ARG ENVIRONMENT
ENV ENVIRONMENT=${ENVIRONMENT:-production}
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/models
WORKDIR /app

RUN pip install --upgrade pip && pip install -U pip poetry==1.8.3
RUN poetry config virtualenvs.create false

RUN apt-get update && apt-get install --no-install-recommends --yes \
    wget \
    ffmpeg \
    # Required for git-based python packages installations (whisper)
    git \
    && rm -rf /var/lib/apt/lists/*

RUN wget -P /usr/local/share/ca-certificates/cacert.org http://www.cacert.org/certs/root.crt http://www.cacert.org/certs/class3.crt && update-ca-certificates

COPY poetry.lock /app
COPY pyproject.toml /app

RUN poetry install --no-dev --no-root -E "faster-whisper" -E "pymorphy" \
    && if [ "$ENVIRONMENT" = "development" ]; then poetry install --all-extras ; fi

ADD utils /app/utils
RUN python /app/utils/pull_faster_whisper_model.py -m ${MODEL}

ENV RECOGNITION_ENGINE="faster-whisper"
ENV RECOGNITION_ENGINE_OPTIONS="{\"model\": \"${MODEL}\", \"language\": \"${LANG}\", \"device\": \"cpu\", \"compute_type\": \"int8\", \"beam_size\": 5}"

ADD fixtures /app/fixtures
ADD blya_bot /app/blya_bot

ENV PATH="/app:${PATH}"
CMD ["python", "-m", "blya_bot"]
