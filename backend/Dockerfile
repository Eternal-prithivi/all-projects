FROM python:3.11-slim

WORKDIR /app

# Terraform >= 1.10.0 (see backend/terraform/main.tf required_version)
ARG TERRAFORM_VERSION=1.10.5

# System deps + Terraform CLI for /api/provision on Render
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ca-certificates \
    curl \
    unzip \
    && curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
        -o /tmp/terraform.zip \
    && unzip -q /tmp/terraform.zip -d /usr/local/bin \
    && rm /tmp/terraform.zip \
    && terraform version \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application + Terraform modules (provision copies modules into per-deploy workspaces)
COPY app ./app
COPY terraform ./terraform

# Writable per-deployment workspaces (ephemeral disk on Render)
RUN mkdir -p /app/terraform_workspaces

ENV TERRAFORM_ROOT=/app/terraform

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Render sets PORT; default 8000 for local Docker
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
