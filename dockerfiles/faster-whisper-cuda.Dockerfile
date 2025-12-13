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
# Stage 2: Runtime with CUDA support
# =============================================================================
FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04

ARG MODEL="small"
ARG LANG="ru"
ARG DEVICE="cuda"
ARG COMPUTE_TYPE="float16"
ARG BEAM_SIZE=5
ARG ENVIRONMENT

ENV ENVIRONMENT=${ENVIRONMENT:-production}
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Required for NVIDIA container runtime
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

RUN mkdir -p /app/models
WORKDIR /app

# Install minimal dependencies
RUN apt-get update && apt-get install --no-install-recommends --yes \
    wget \
    ffmpeg \
    tini \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Python 3.13 via uv
RUN uv python install 3.13
RUN uv venv --python 3.13 /app/.venv

# Copy blya_bot package and install with faster-whisper extra
COPY blya_bot/ /app/blya_bot/
RUN uv pip install --python /app/.venv/bin/python "/app/blya_bot/[faster-whisper]"

ADD utils /app/utils
RUN /app/.venv/bin/python /app/utils/pull_faster_whisper_model.py -m ${MODEL}

# Settings use nested format with __ delimiter
ENV RECOGNITION__ENGINE="faster-whisper"
ENV RECOGNITION__ENGINE_OPTIONS="{\"model\": \"${MODEL}\", \"language\": \"${LANG}\", \"device\": \"${DEVICE}\", \"compute_type\": \"${COMPUTE_TYPE}\", \"beam_size\": ${BEAM_SIZE}}"

# Copy pre-built dictionary from dictgen stage
COPY --from=dictgen /build/fixtures/dict.bb /app/fixtures/dict.bb

ENV PATH="/app/.venv/bin:/app:${PATH}"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "blya_bot"]
