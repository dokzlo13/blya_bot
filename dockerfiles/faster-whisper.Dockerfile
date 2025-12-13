# syntax=docker/dockerfile:1

# =============================================================================
# Stage 1: Build dictionary with morphing
# =============================================================================
FROM python:3.13-bookworm AS dictgen

WORKDIR /build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy source files needed for dictgen
COPY blya_bot/ /build/blya_bot/
COPY dictgen/ /build/dictgen/
COPY fixtures/bad_words.txt /build/fixtures/

# Install blya_bot and dictgen, then generate packed dictionary
RUN uv pip install --system /build/blya_bot/ /build/dictgen/
RUN python -m dictgen -i /build/fixtures/bad_words.txt -o /build/fixtures/dict.bb --morphing

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.13-bookworm

ARG MODEL="small"
ARG LANG="ru"
ARG DEVICE="cpu"
ARG COMPUTE_TYPE="int8"
ARG BEAM_SIZE=5
ARG ENVIRONMENT

ENV ENVIRONMENT=${ENVIRONMENT:-production}
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/models
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install --no-install-recommends --yes \
    wget \
    ffmpeg \
    tini \
    # Required for git-based python packages installations (whisper)
    git \
    && rm -rf /var/lib/apt/lists/*

RUN wget -P /usr/local/share/ca-certificates/cacert.org http://www.cacert.org/certs/root.crt http://www.cacert.org/certs/class3.crt && update-ca-certificates

# Copy blya_bot package and install
COPY blya_bot/ /app/blya_bot/
RUN uv pip install --system "/app/blya_bot/[faster-whisper]"

ADD utils /app/utils
RUN python /app/utils/pull_faster_whisper_model.py -m ${MODEL}

# Settings use nested format with __ delimiter
ENV RECOGNITION__ENGINE="faster-whisper"
ENV RECOGNITION__ENGINE_OPTIONS="{\"model\": \"${MODEL}\", \"language\": \"${LANG}\", \"device\": \"${DEVICE}\", \"compute_type\": \"${COMPUTE_TYPE}\", \"beam_size\": ${BEAM_SIZE}}"

# Copy pre-built dictionary from dictgen stage
COPY --from=dictgen /build/fixtures/dict.bb /app/fixtures/dict.bb

ENV PATH="/app:${PATH}"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "blya_bot"]
