import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import uuid
from datetime import datetime

from backend.main import app
from backend.db.session import get_db
from backend.db.models import SessionStatus

# Create a shared mock database session
mock_db = AsyncMock()

async def override_get_db():
    yield mock_db

# Register dependency override globally for API tests
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_db_mock():
    mock_db.reset_mock()
    yield

def test_create_session_success():
    payload = {
        "company_name": "Test Acme",
        "website": "https://acme.org",
        "objective": "Pitching software solutions"
    }
    
    response = client.post("/api/sessions", json=payload)
    assert response.status_code == 201
    
    res_json = response.json()
    assert "data" in res_json
    assert res_json["data"]["company_name"] == "Test Acme"
    assert "request_id" in res_json
    
    # Verify DB calls were made on mock_db
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

def test_create_session_validation_error():
    payload = {
        "company_name": "Acme",
        "website": "invalid-url",
        "objective": "pitch"
    }
    
    response = client.post("/api/sessions", json=payload)
    assert response.status_code == 422
    assert "error" in response.json()

def test_list_sessions():
    # Mock SQL execution return value
    mock_session_row = MagicMock()
    mock_session_row.id = uuid.uuid4()
    mock_session_row.company_name = "Acme"
    mock_session_row.website = "https://acme.com"
    mock_session_row.objective = "pitch"
    mock_session_row.status = MagicMock()
    mock_session_row.status.value = "pending"
    mock_session_row.created_at = datetime.utcnow()
    mock_session_row.updated_at = None

    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = [mock_session_row]
    mock_db.execute.return_value = mock_execute_result

    response = client.get("/api/sessions")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert response.json()["data"][0]["company_name"] == "Acme"

def test_get_session_not_found():
    # Mock select result returning None
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_execute_result
    
    rand_uuid = uuid.uuid4()
    response = client.get(f"/api/sessions/{rand_uuid}")
    assert response.status_code == 404
    assert "not found" in response.json()["error"]

def test_run_session_workflow_not_found():
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_execute_result
    
    rand_uuid = uuid.uuid4()
    response = client.post(f"/api/sessions/{rand_uuid}/run")
    assert response.status_code == 404

@patch("backend.api.workflow.BackgroundTasks.add_task")
def test_run_session_workflow_success(mock_add_task):
    # Mock select session status pending
    mock_session_row = MagicMock()
    mock_session_row.id = uuid.uuid4()
    mock_session_row.status = SessionStatus.PENDING
    
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = mock_session_row
    mock_db.execute.return_value = mock_execute_result
    
    response = client.post(f"/api/sessions/{mock_session_row.id}/run")
    assert response.status_code == 202
    assert response.json()["data"]["status"] == "queued"
    mock_add_task.assert_called_once()
