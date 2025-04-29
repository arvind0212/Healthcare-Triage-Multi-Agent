from fastapi.testclient import TestClient

# Import the FastAPI app
from mdt_agent_system.app.main import app

# Initialize the TestClient
client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"} 