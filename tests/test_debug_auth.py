from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app


def test_debug_without_credentials():
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/debug/scheduler")
    assert response.status_code == 401


def test_debug_with_wrong_credentials():
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/debug/scheduler", auth=("wrong", "creds"))
    assert response.status_code == 401


def test_debug_with_valid_credentials():
    mock_scheduler = MagicMock()
    mock_job = MagicMock()
    mock_job.id = "test_job"
    mock_job.next_run_time = "2026-07-15T12:00:00"
    mock_job.func_ref = "app.scheduler.run_bcv_worker"
    mock_scheduler.get_jobs.return_value = [mock_job]
    app.state.scheduler = mock_scheduler

    client = TestClient(app)
    response = client.get("/debug/scheduler", auth=("admin", "changeme"))
    assert response.status_code == 200
    assert "jobs" in response.json()
    assert len(response.json()["jobs"]) == 1

    del app.state.scheduler