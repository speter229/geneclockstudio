import pytest
from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import patch

client = TestClient(app)

def test_get_dataset_success(mocker):
    """
    Test the /dataset/{dataset_name} endpoint for a valid dataset.
    """
    # Mock the get_dataset_info function
    mocker.patch(
        "backend.routers.dataset_router.get_dataset_info",
        return_value={
            "description": "Test dataset description",
            "metadata": {"Sample1": {"age": 30}, "Sample2": {"age": 40}},
            "ages": [30, 40],
            "trained_clocks": "Test Clock",
            "study_description_1": "Study 1 description",
            "study_description_2": "Study 2 description",
            "study_scatterplot_1": "scatterplot1.png",
            "study_scatterplot_2": "scatterplot2.png",
            "study_boxplot_1": "boxplot1.png",
            "study_description_3": None,  # Add this field
        },
    )

    response = client.get("/datasets/GSE40279")
    assert response.status_code == 200
    assert response.json() == {
        "description": "Test dataset description",
        "metadata": {"Sample1": {"age": 30}, "Sample2": {"age": 40}},
        "ages": [30, 40],
        "trained_clocks": "Test Clock",
        "study_description_1": "Study 1 description",
        "study_description_2": "Study 2 description",
        "study_scatterplot_1": "scatterplot1.png",
        "study_scatterplot_2": "scatterplot2.png",
        "study_boxplot_1": "boxplot1.png",
        "study_description_3": None,  # Add this field
    }

def test_get_dataset_not_found(mocker):
    """
    Test the /dataset/{dataset_name} endpoint for a non-existent dataset.
    """
    # Mock the get_dataset_info function to raise a ValueError
    mocker.patch(
        "backend.routers.dataset_router.get_dataset_info",
        side_effect=ValueError("Dataset not found"),
    )

    response = client.get("/dataset/InvalidDataset")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}

def test_get_dataset_invalid_name(mocker):
    """
    Test the /dataset/{dataset_name} endpoint with an invalid dataset name.
    """
    # Mock the get_dataset_info function to raise a ValueError for invalid dataset names
    mocker.patch(
        "backend.routers.dataset_router.get_dataset_info",
        side_effect=ValueError("Dataset not found"),
    )

    # Call the endpoint with an invalid dataset name
    response = client.get("/dataset/InvalidDataset")

    # Assert the response
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}