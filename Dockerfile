FROM python:3.11-slim

LABEL maintainer="promptInjector"
LABEL description="Security testing tool for identifying prompt injection vulnerabilities in AI assistants"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Install the package in editable mode
RUN pip install --no-cache-dir -e .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Default entrypoint
ENTRYPOINT ["promptinjector"]

# Default command shows help
CMD ["--help"]
