import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.authenticator_service import get_current_user
from unittest.mock import patch

client = TestClient(app)

TEST_USER = "pytest_user"


@pytest.fixture(autouse=True)
def authenticated():
    """The dataset endpoint now requires a login, so every case here needs a user.

    Restores whatever override was in place before (other test modules install their
    own at import time on the same shared app object).
    """
    previous = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    yield TEST_USER
    if previous is None:
        app.dependency_overrides.pop(get_current_user, None)
    else:
        app.dependency_overrides[get_current_user] = previous


@pytest.fixture
def unauthenticated():
    """Removes any auth override so the endpoint sees an anonymous caller."""
    previous = app.dependency_overrides.pop(get_current_user, None)
    yield
    if previous is not None:
        app.dependency_overrides[get_current_user] = previous


def test_get_dataset_requires_authentication(unauthenticated):
    """The clock/dataset endpoints must not be reachable without a login."""
    response = client.get("/datasets/GSE40279")
    assert response.status_code in (401, 403)


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
