import pytest
from fastapi.testclient import TestClient
from backend.main import app
import os

client = TestClient(app)

def test_predict_endpoint_success(mocker):
    """
    Test the /predictions/predict/ endpoint with a valid file and mocked prediction.
    """
    # Mock the predict_biological_age function
    mocker.patch(
        "backend.routers.predictions_router.predict_biological_age",
        return_value=[{"sample_id": "sample1", "PredictedAge": 45.0}]
    )

    # Create a temporary CSV file for testing
    test_file_path = "test_file.csv"
    with open(test_file_path, "w") as f:
        f.write("sample_id,value\nsample1,0.5")

    try:
        response = client.post(
            "/predictions/predict/",
            json={"model_name": "ElasticNet", "file_path": test_file_path}
        )
        assert response.status_code == 200
        assert response.json()["predictions"] == [{"sample_id": "sample1", "PredictedAge": 45.0}]
    finally:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)