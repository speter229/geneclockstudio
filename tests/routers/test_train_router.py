import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.main import app
from backend.services.authenticator_service import get_current_user
import pandas as pd
import os

client = TestClient(app)

# Override the get_current_user dependency
def override_get_current_user():
    return "test_user"

app.dependency_overrides[get_current_user] = override_get_current_user

def test_train_model_success(mocker):
    """
    Test the /train/train_model/ endpoint for successful model training.
    """
    # Mock the process_training_job function
    mocker.patch(
        "backend.routers.train_router.process_training_job",
        return_value={
            "y_test": [30, 40],
            "y_pred": [32, 38],
            "mae": 2.0,
            "r_value": 0.95,
            "download_path": "/train/download_model/test_model_id",
        },
    )

    # Mock file existence checks
    mocker.patch("os.path.exists", return_value=True)

    # Mock file removal
    mocker.patch("os.remove")

    # Mock file reading
    mocker.patch("pandas.read_csv", return_value=pd.DataFrame({"A": [1, 2], "B": [3, 4]}))

    # Mock dataframe cache
    mocker.patch(
        "backend.routers.train_router.dataframe_cache",
        return_value={
            "test_user": {
                "df_betas": pd.DataFrame({"A": [1, 2], "B": [3, 4]}),
                "df_meta": pd.DataFrame({"A": [30, 40], "B": [50, 60]}),
            }
        },
    )

    # Prepare request data
    request_data = {
        "betas_path": "test_betas.csv",
        "metadata_path": "test_metadata.csv",
        "model_name": "ElasticNet",
        "model_params": '{"alpha": 0.1, "l1_ratio": 0.5}',
        "gene_filter_path": None,
        "is_promoter_only": False,
    }

    response = client.post("/train/train_model/", json=request_data)
    assert response.status_code == 200
    assert response.json() == {
        "y_test": [30, 40],
        "y_pred": [32, 38],
        "mae": 2.0,
        "r_value": 0.95,
        "download_path": "/train/download_model/test_model_id",
    }

def test_train_model_invalid_request_data(mocker):
    """
    Test the /train/train_model/ endpoint with invalid request data.
    """
    # Mock the process_training_job function to ensure it is not called
    mock_process_training_job = mocker.patch("backend.routers.train_router.process_training_job")

    # Prepare invalid request data (missing required fields)
    request_data = {
        "metadata_path": "test_metadata.csv",  # Missing 'betas_path' and 'model_name'
        "model_params": '{"alpha": 0.1, "l1_ratio": 0.5}',
    }

    # Call the endpoint
    response = client.post("/train/train_model/", json=request_data)

    # Assert the response
    assert response.status_code == 422  # FastAPI raises 422 for validation errors
    assert "detail" in response.json()  # Ensure error details are included
    assert mock_process_training_job.call_count == 0  # Ensure the function is not called

def test_list_user_models(mocker):
    """
    Test the /train/list endpoint for listing user models.
    """
    # Mock the model registry
    mock_registry = {
        "model1": {"username": "test_user", "model_filename": "model1.pkl"},
        "model2": {"username": "other_user", "model_filename": "model2.pkl"},
    }
    mocker.patch("builtins.open", mocker.mock_open(read_data="{}"))
    mocker.patch("json.load", return_value=mock_registry)

    response = client.get("/train/list")
    assert response.status_code == 200
    assert response.json() == {
        "models": [
            {
                "model_id": "model1",
                "model_filename": "model1.pkl",
                "download_link": "/train/download_model/model1.pkl",
            }
        ]
    }

def test_list_user_models_no_models(mocker):
    """
    Test the /train/list endpoint when no models exist for the user.
    """
    # Mock the model registry to be empty
    mocker.patch("os.path.exists", return_value=True)  # Mock that the registry file exists
    mocker.patch("builtins.open", mocker.mock_open(read_data="{}"))  # Mock an empty JSON file
    mocker.patch("json.load", return_value={})  # Mock the registry as an empty dictionary

    # Call the endpoint
    response = client.get("/train/list")

    # Assert the response
    assert response.status_code == 200
    assert response.json() == {"models": []}  # Expect an empty list of models
