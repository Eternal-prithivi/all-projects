"""Celery tasks for Terraform apply/destroy (provision worker queue)."""

from __future__ import annotations

import logging

from app.celery_worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="provision.terraform_apply", bind=True, max_retries=0)
def terraform_apply_task(self, deployment_id: str, username: str) -> dict:
    from app.provision.terraform_jobs import run_terraform_apply_sync

    return run_terraform_apply_sync(deployment_id, username)


@celery_app.task(name="provision.terraform_destroy", bind=True, max_retries=0)
def terraform_destroy_task(self, deployment_id: str, username: str) -> dict:
    from app.provision.terraform_jobs import run_terraform_destroy_sync

    return run_terraform_destroy_sync(deployment_id, username)
