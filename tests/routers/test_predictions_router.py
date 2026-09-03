import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import TEMP_PATH
from backend.services.authenticator_service import get_current_user
import os

client = TestClient(app)

TEST_USER = "pytest_user"


@pytest.fixture
def authenticated():
    """Overrides the auth dependency so the endpoint sees a logged-in user.

    Restores whatever override was in place before (other test modules install
    their own at import time on the same shared app object).
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
    """Removes any auth override installed by other test modules on the shared app."""
    previous = app.dependency_overrides.pop(get_current_user, None)
    yield
    if previous is not None:
        app.dependency_overrides[get_current_user] = previous


@pytest.fixture
def user_beta_file():
    """Creates a small beta file inside the user's temp folder (an allowed path)."""
    user_dir = os.path.join(TEMP_PATH, TEST_USER)
    os.makedirs(user_dir, exist_ok=True)
    path = os.path.join(user_dir, "test_file.csv")
    with open(path, "w") as f:
        f.write("sample_id,value\nsample1,0.5")
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_predict_endpoint_success(mocker, authenticated, user_beta_file):
    """
    Test the /predictions/predict/ endpoint with a valid file and mocked prediction.
    """
    # Mock the predict_biological_age function
    mocker.patch(
        "backend.routers.predictions_router.predict_biological_age",
        return_value=[{"sample_id": "sample1", "PredictedAge": 45.0}]
    )

    response = client.post(
        "/predictions/predict/",
        json={"model_name": "ElasticNet", "file_path": user_beta_file}
    )
    assert response.status_code == 200
    assert response.json()["predictions"] == [{"sample_id": "sample1", "PredictedAge": 45.0}]


def test_predict_endpoint_requires_authentication(unauthenticated, user_beta_file):
    """Without a token the endpoint must not run a prediction at all."""
    response = client.post(
        "/predictions/predict/",
        json={"model_name": "ElasticNet", "file_path": user_beta_file}
    )
    assert response.status_code == 401


def test_predict_endpoint_rejects_paths_outside_user_data(mocker, authenticated):
    """A client must not be able to point the endpoint at other server files."""
    predict_mock = mocker.patch(
        "backend.routers.predictions_router.predict_biological_age"
    )

    response = client.post(
        "/predictions/predict/",
        json={
            "model_name": "ElasticNet",
            "file_path": "backend/data/inflammation_cg_means.csv.enc",
        },
    )
    assert response.status_code == 400
    predict_mock.assert_not_called()


def test_calculate_percent_requires_authentication(unauthenticated, user_beta_file):
    """The coverage endpoint is also gated, so it cannot be probed anonymously."""
    response = client.post(
        "/predictions/calculate_percent/",
        json={"file_path": user_beta_file}
    )
    assert response.status_code == 401
