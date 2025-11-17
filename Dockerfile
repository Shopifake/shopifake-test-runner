# ===== Stage 1 — Build dependencies =====
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies in virtual environment
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt


# ===== Stage 2 — Runtime =====
FROM python:3.12-slim AS runtime

LABEL maintainer="Shopifake Team" \
      description="Shopifake Test Runner - System, Load, and Chaos Tests" \
      version="1.0.0"

# Create non-root user for security
RUN useradd -m -u 1000 testrunner

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv

# Configure environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install curl for debugging and health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

WORKDIR /app

# Copy application code
COPY --chown=testrunner:testrunner ./src ./src

# Create reports and pytest cache directories
RUN mkdir -p reports .pytest_cache && \
    chown -R testrunner:testrunner reports .pytest_cache

# Switch to non-root user
USER testrunner

# Entrypoint using the CLI module
ENTRYPOINT ["python", "-m", "src.cli"]

# Default: run system tests in staging mode
CMD ["--mode", "staging", "--suite", "system"]
