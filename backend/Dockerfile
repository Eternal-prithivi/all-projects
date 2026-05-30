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
ENV TF_PLUGIN_CACHE_DIR=/app/terraform-plugin-cache

# Pre-download AWS provider plugins (speeds up first user terraform init on Render)
RUN mkdir -p /app/terraform-plugin-cache \
    && cd /app/terraform \
    && terraform init -backend=false -input=false -no-color

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.getenv('PORT','8000'), timeout=3)"

# Render sets PORT; default 8000 for local Docker
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
