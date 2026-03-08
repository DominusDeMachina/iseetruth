"""Tests for Celery app configuration."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _mock_settings():
    """Provide mock settings so celery_app module can import without real env."""
    mock_settings = type(
        "Settings",
        (),
        {
            "celery_broker_url": "redis://localhost:6379/0",
            "celery_result_backend": "redis://localhost:6379/1",
        },
    )()
    with patch("app.worker.celery_app.get_settings", return_value=mock_settings):
        yield


def test_celery_app_exists():
    from app.worker.celery_app import celery_app

    assert celery_app.main == "osint"


def test_celery_task_serializer_is_json():
    from app.worker.celery_app import celery_app

    assert celery_app.conf.task_serializer == "json"


def test_celery_acks_late_enabled():
    from app.worker.celery_app import celery_app

    assert celery_app.conf.task_acks_late is True


def test_celery_prefetch_multiplier_is_one():
    from app.worker.celery_app import celery_app

    assert celery_app.conf.worker_prefetch_multiplier == 1
