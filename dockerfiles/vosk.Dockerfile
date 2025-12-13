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

ARG MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"
ARG ENVIRONMENT
ENV ENVIRONMENT=${ENVIRONMENT:-production}
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/models
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install --no-install-recommends --yes \
    wget \
    zip \
    unzip \
    ffmpeg \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Forcing certificates
RUN wget -P /usr/local/share/ca-certificates/cacert.org http://www.cacert.org/certs/root.crt http://www.cacert.org/certs/class3.crt && update-ca-certificates

RUN wget -O /app/models/vosk-model.zip ${MODEL_URL} \
    && unzip /app/models/vosk-model.zip -d /app/models/ \
    && rm /app/models/vosk-model.zip \
    # Extract models path automatically
    && extracted_folder=$(find /app/models/ -mindepth 1 -maxdepth 1 -type d) \
    && echo "export RECOGNITION__ENGINE_OPTIONS='{\"model_path\": \"$extracted_folder\"}'" > /app/models/config.sh;

# Copy blya_bot package and install
COPY blya_bot/ /app/blya_bot/
RUN uv pip install --system "/app/blya_bot/[vosk]"

# Settings use nested format with __ delimiter
ENV RECOGNITION__ENGINE="vosk"

# Copy pre-built dictionary from dictgen stage
COPY --from=dictgen /build/fixtures/dict.bb /app/fixtures/dict.bb

ENV PATH="/app:${PATH}"

ENTRYPOINT ["/usr/bin/tini", "--"]
# Apply env with current model path
CMD ["/bin/bash", "-c", "source /app/models/config.sh && python -m blya_bot"]
