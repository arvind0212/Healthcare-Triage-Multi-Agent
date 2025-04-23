import pytest
from pydantic import ValidationError
from mdt_agent_system.app.core.schemas import PatientCase, MDTReport, StatusUpdate
from datetime import datetime

def test_patient_case_validation():
    # Test valid patient case
    patient_data = {
        "patient_id": "P12345",
        "demographics": {"age": 45, "gender": "F"},
        "medical_history": [{"condition": "Diabetes", "diagnosed": "2018-03-15"}],
        "current_condition": {"primary_complaint": "Chest pain"}
    }
    patient = PatientCase(**patient_data)
    assert patient.patient_id == "P12345"
    assert patient.demographics["age"] == 45
    
    # Test optional fields
    assert patient.imaging_results is None
    assert patient.pathology_results is None
    assert patient.lab_results is None
    
    # Test created_at auto-generation
    assert isinstance(patient.created_at, datetime)

def test_mdt_report_validation():
    # Test valid MDT report
    report_data = {
        "patient_id": "P12345",
        "summary": "Test summary",
        "ehr_analysis": {"key_findings": ["Finding 1"]},
        "guideline_recommendations": [{"guideline": "Test", "recommendation": "Test"}],
        "specialist_assessment": {"opinion": "Test opinion"},
        "treatment_options": [{"option": "Test option"}]
    }
    report = MDTReport(**report_data)
    assert report.patient_id == "P12345"
    assert report.summary == "Test summary"
    
    # Test optional fields
    assert report.evaluation_score is None
    assert report.evaluation_comments is None
    
    # Test timestamp auto-generation
    assert isinstance(report.timestamp, datetime)

def test_status_update_validation():
    # Test valid status update
    status_data = {
        "agent_id": "test_agent",
        "status": "ACTIVE",
        "message": "Test message",
        "run_id": "sim_123"
    }
    status = StatusUpdate(**status_data)
    assert status.agent_id == "test_agent"
    assert status.status == "ACTIVE"
    assert status.message == "Test message"
    
    # Test timestamp auto-generation
    assert isinstance(status.timestamp, datetime)
    
    # Test invalid status value
    with pytest.raises(ValueError):
        StatusUpdate(
            agent_id="test_agent",
            status="INVALID",  # Invalid status
            message="Test",
            run_id="sim_123"
        )

def test_required_fields():
    # Test PatientCase required fields
    with pytest.raises(ValueError):
        PatientCase(demographics={})  # Missing patient_id
    
    # Test MDTReport required fields
    with pytest.raises(ValueError):
        MDTReport(patient_id="P12345")  # Missing other required fields
    
    # Test StatusUpdate required fields
    with pytest.raises(ValueError):
        StatusUpdate(agent_id="test_agent")  # Missing status and message 