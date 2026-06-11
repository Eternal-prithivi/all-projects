"""Unit and API tests for provision intent analysis and template mapping."""

import pytest

from app.provision.intent_analyzer import analyze_provision_intent
from app.provision.template_mapper import recommend_from_text
from app.provision.review_summary import build_review_summary
from app.provision.provision_defaults import skeleton_config_for_template


def test_recommend_static_site():
    rec = recommend_from_text("I need a static HTML landing page for my portfolio")
    assert rec.template == "static-site"
    assert rec.confidence >= 40


def test_recommend_serverless_db():
    rec = recommend_from_text("PostgreSQL database with nightly backups and 500GB data")
    assert rec.template in ("serverless-db", "backend-app")


def test_recommend_backend_app():
    rec = recommend_from_text("Node.js API with Docker for 1000 requests per minute")
    assert rec.template == "backend-app"


def test_analyze_provision_intent_shape():
    result = analyze_provision_intent("Web API for a small startup", None)
    assert "recommendation" in result
    assert "readiness" in result
    assert "follow_up_questions" in result
    assert result["recommendation"]["template"] in (
        "static-site",
        "backend-app",
        "serverless-db",
    )


def test_review_summary_backend_app():
    cfg = skeleton_config_for_template("AWS", "backend-app", size_profile="micro")
    summary = build_review_summary(cfg)
    assert summary["plain_english_bullets"]
    assert summary["csp"] == "AWS"
    assert "estimated_monthly" in summary


@pytest.mark.integration
def test_analyze_intent_api(client, auth_headers):
    headers, _user = auth_headers()
    res = client.post(
        "/api/provision/analyze-intent",
        json={"workload_description": "Small Node.js API with PostgreSQL"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["recommendation"]["template"] in ("static-site", "backend-app", "serverless-db")
    assert "follow_up_questions" in data


@pytest.mark.integration
def test_review_summary_api(client, auth_headers):
    headers, _user = auth_headers()
    res = client.post(
        "/api/provision/review-summary",
        json={
            "csp": "AWS",
            "template": "backend-app",
            "environment": "dev",
            "enable_vpc": True,
            "enable_ec2": True,
            "instance_type": "t2.micro",
            "disk_size_gb": 30,
            "deployment_display_name": "test-api",
        },
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["plain_english_bullets"]
    assert data["csp"] == "AWS"


@pytest.mark.integration
def test_deployment_handoff_404(client, auth_headers):
    headers, _user = auth_headers()
    res = client.get(
        "/api/provision/deployments/nonexistent-deploy/handoff",
        headers=headers,
    )
    assert res.status_code == 404
