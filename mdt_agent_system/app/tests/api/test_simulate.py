import json
import io
import pytest
from fastapi.testclient import TestClient

# Revert to original absolute import
from mdt_agent_system.app.main import app

client = TestClient(app)

@pytest.fixture
def valid_patient_case_data():
    # Provide a minimal valid PatientCase structure for testing
    return {
        "patient_id": "test-001",
        "demographics": {"age": 65, "gender": "Male"},
        "medical_history": [{"condition": "Hypertension"}],
        "current_condition": {"description": "Presenting with chest pain"}
        # Add other required fields if any, based on your latest PatientCase schema
    }

@pytest.fixture
def invalid_patient_case_data():
    # Missing required fields (e.g., demographics)
    return {
        "patient_id": "test-002",
        "medical_history": [],
        "current_condition": {}
    }

def test_simulate_success(valid_patient_case_data):
    """Test successful simulation request with valid JSON."""
    json_data = json.dumps(valid_patient_case_data).encode('utf-8')
    file = io.BytesIO(json_data)

    response = client.post(
        "/simulate",
        files={"file": ("test_case.json", file, "application/json")}
    )

    assert response.status_code == 202  # HTTP 202 Accepted
    response_data = response.json()
    assert "run_id" in response_data
    assert isinstance(response_data["run_id"], str)
    assert response_data["message"] == "Simulation request accepted and is being processed."

def test_simulate_invalid_content_type(valid_patient_case_data):
    """Test simulation request with incorrect content type."""
    json_data = json.dumps(valid_patient_case_data).encode('utf-8')
    file = io.BytesIO(json_data)

    response = client.post(
        "/simulate",
        files={"file": ("test_case.txt", file, "text/plain")}  # Incorrect content type
    )

    assert response.status_code == 400  # Bad Request
    assert response.json() == {"detail": "Invalid file type. Only JSON is accepted."}

def test_simulate_invalid_json_format():
    """Test simulation request with malformed JSON."""
    invalid_json_data = b'{"patient_id": "test-003", "demographics": {"age": 50,}' # Malformed JSON
    file = io.BytesIO(invalid_json_data)

    response = client.post(
        "/simulate",
        files={"file": ("invalid.json", file, "application/json")}
    )

    assert response.status_code == 400  # Bad Request
    assert response.json() == {"detail": "Invalid JSON file."}

def test_simulate_schema_validation_error(invalid_patient_case_data):
    """Test simulation request with data failing PatientCase schema validation."""
    json_data = json.dumps(invalid_patient_case_data).encode('utf-8')
    file = io.BytesIO(json_data)

    response = client.post(
        "/simulate",
        files={"file": ("invalid_schema.json", file, "application/json")}
    )

    assert response.status_code == 422  # Unprocessable Entity
    response_data = response.json()
    assert "detail" in response_data
    assert "PatientCase validation failed:" in response_data["detail"]
    # Check for specific validation errors if needed, e.g.:
    # assert "'demographics'" in response_data["detail"]
    # assert "Field required" in response_data["detail"] 