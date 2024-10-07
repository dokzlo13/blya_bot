# syntax=docker/dockerfile:1

FROM python:3.12.7-bookworm

ARG MODEL="small"
# ENV MODEL=$MODEL

ARG LANG="ru"
# ENV LANG=$LANG

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

RUN poetry install --no-dev --no-root -E "pywhispercpp" -E "pymorphy" \
    && if [ "$ENVIRONMENT" = "development" ]; then poetry install --all-extras ; fi

ADD utils /app/utils
RUN python /app/utils/pull_whispercpp_model.py -m ${MODEL}

ENV RECOGNITION_ENGINE="pywhispercpp"
ENV RECOGNITION_ENGINE_OPTIONS="{\"model\": \"${MODEL}\", \"language\": \"${LANG}\"}"

ADD fixtures /app/fixtures
ADD blya_bot /app/blya_bot

ENV PATH="/app:${PATH}"
CMD ["python", "-m", "blya_bot"]
