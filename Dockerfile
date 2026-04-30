# syntax=docker/dockerfile:1.7
# ----------------------------------------------------------------------------
# Multi-stage Dockerfile for the Personal Assistant Agent.
# Stage 1: install dependencies into a virtual environment (cacheable layer).
# Stage 2: copy that venv into a slim runtime image with a non-root user.
# Build:  docker build -t gemini-agent:latest .
# Run:    docker run --rm -it -e GEMINI_API_KEY="$GEMINI_API_KEY" gemini-agent
# ----------------------------------------------------------------------------

FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

COPY requirements.txt ./
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt


FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# tzdata is needed for DateTimeTool to recognise IANA timezone names like
# "Europe/Riga" — the slim image doesn't include the full database.
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && \
    rm -rf /var/lib/apt/lists/*

# Non-root user for safety.
RUN groupadd --system app && useradd --system --gid app --create-home app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app agent.py main.py memory_manager.py observer.py ./
COPY --chown=app:app tools ./tools
COPY --chown=app:app agent_files ./agent_files

USER app

# GEMINI_API_KEY must be passed at runtime via -e or --env-file. Never bake.
ENV GEMINI_MODEL=gemini-2.5-flash \
    AGENT_FILES_DIR=/app/agent_files

ENTRYPOINT ["python", "main.py"]
CMD ["--log-level", "INFO"]
