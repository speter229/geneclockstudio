import pytest
from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import patch
from backend.services import authenticator_service

client = TestClient(app)

def test_signup_success(mocker):
    """
    Test /authenticate/signup endpoint when a new user registers successfully.
    """
    mocker.patch("backend.routers.authenticator_router.add_user")

    response = client.post("/authenticate/signup", json={"username": "testuser", "password": "testpass"})
    assert response.status_code == 200
    assert response.json() == {"message": "User 'testuser' registered successfully."}


def test_login_success(mocker):
    """
    Test /authenticate/login endpoint with correct username and password.
    """
    # Mock dependencies
    mock_user = {"username": "testuser", "hashed_password": "hashed"}
    mocker.patch("backend.routers.authenticator_router.get_user", return_value=mock_user)
    mocker.patch("backend.routers.authenticator_router.verify_password", return_value=True)
    mocker.patch("backend.routers.authenticator_router.create_access_token", return_value="test_token")

    # OAuth2 sends data as form, not JSON
    response = client.post("/authenticate/login", data={"username": "testuser", "password": "testpass"})
    assert response.status_code == 200
    assert response.json() == {"access_token": "test_token", "token_type": "bearer"}


def test_login_invalid_credentials(mocker):
    """
    Test /authenticate/login endpoint with wrong password or missing user.
    """
    # Case 1: User not found
    mocker.patch("backend.routers.authenticator_router.get_user", return_value=None)

    response = client.post("/authenticate/login", data={"username": "nouser", "password": "wrongpass"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Incorrect username or password"}

    # Case 2: Wrong password
    mocker.patch("backend.routers.authenticator_router.get_user", return_value={"username": "testuser", "hashed_password": "hashed"})
    mocker.patch("backend.routers.authenticator_router.verify_password", return_value=False)

    response = client.post("/authenticate/login", data={"username": "testuser", "password": "wrongpass"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Incorrect username or password"}
