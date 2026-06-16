"""Celery app for Terraform provision worker (provision queue only)."""

from app.celery_worker import celery_app as celery_app

# Re-export shared broker config; worker listens on provision queue via CLI -Q provision
