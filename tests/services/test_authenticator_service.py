import unittest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from backend.services.authenticator_service import (
    load_users,
    save_users,
    verify_password,
    hash_password,
    create_access_token,
    decode_token,
    get_user,
    add_user,
    get_current_user,
)
from jose import jwt
import os
import json
import tempfile

class TestAuthenticatorService(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for the users database
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()  # Close the file so it can be used by the tests
        self.test_users = {
            "test_user": {
                "username": "test_user",
                "hashed_password": hash_password("test_password"),
            }
        }
        with open(self.temp_file.name, "w") as f:
            json.dump(self.test_users, f)

        # Patch USERS_FILE to use the temporary file
        self.patcher = patch("backend.services.authenticator_service.USERS_FILE", self.temp_file.name)
        self.patcher.start()

    def tearDown(self):
        # Stop patching and delete the temporary file
        self.patcher.stop()
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_load_users(self):
        users = load_users()
        self.assertIn("test_user", users)
        self.assertEqual(users["test_user"]["username"], "test_user")

    def test_save_users(self):
        new_users = {
            "new_user": {
                "username": "new_user",
                "hashed_password": hash_password("new_password"),
            }
        }
        save_users(new_users)
        with open(self.temp_file.name, "r") as f:
            saved_users = json.load(f)
        self.assertIn("new_user", saved_users)
        self.assertEqual(saved_users["new_user"]["username"], "new_user")

    def test_verify_password(self):
        hashed_password = hash_password("test_password")
        self.assertTrue(verify_password("test_password", hashed_password))
        self.assertFalse(verify_password("wrong_password", hashed_password))

    def test_hash_password(self):
        hashed_password = hash_password("test_password")
        self.assertNotEqual("test_password", hashed_password)
        self.assertTrue(verify_password("test_password", hashed_password))

    def test_create_access_token(self):
        data = {"sub": "test_user"}
        token = create_access_token(data)
        decoded_data = jwt.decode(token, "supersecretkey", algorithms=["HS256"])
        self.assertEqual(decoded_data["sub"], "test_user")

    @patch("backend.services.authenticator_service.users_db", {"test_user": {"username": "test_user"}})
    def test_decode_token_valid(self):
        data = {"sub": "test_user"}
        token = create_access_token(data)
        username = decode_token(token)
        self.assertEqual(username, "test_user")

    def test_decode_token_invalid(self):
        with self.assertRaises(HTTPException):
            decode_token("invalid_token")

    @patch("backend.services.authenticator_service.users_db", {"test_user": {"username": "test_user"}})
    def test_get_user(self):
        user = get_user("test_user")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "test_user")

    @patch("backend.services.authenticator_service.users_db", {})
    @patch("backend.services.authenticator_service.save_users")
    def test_add_user(self, mock_save_users):
        from backend.services.authenticator_service import users_db  # Import users_db after patching
        add_user("new_user", "ValidPass1")  # Use a valid password
        self.assertIn("new_user", users_db)
        self.assertTrue(verify_password("ValidPass1", users_db["new_user"]["hashed_password"]))
        mock_save_users.assert_called_once()

    @patch("backend.services.authenticator_service.users_db", {"test_user": {"username": "test_user"}})
    def test_add_user_existing(self):
        with self.assertRaises(HTTPException):
            add_user("test_user", "new_password")

    @patch("backend.services.authenticator_service.jwt.decode")
    @patch("backend.services.authenticator_service.users_db", {"test_user": {"username": "test_user"}})
    def test_get_current_user_valid(self, mock_jwt_decode):
        mock_jwt_decode.return_value = {"sub": "test_user"}
        request = MagicMock()
        request.headers = {"Authorization": "Bearer valid_token"}
        username = get_current_user(request)
        self.assertEqual(username, "test_user")

    @patch("backend.services.authenticator_service.jwt.decode")
    def test_get_current_user_invalid_token(self, mock_jwt_decode):
        mock_jwt_decode.side_effect = jwt.JWTError()
        request = MagicMock()
        request.headers = {"Authorization": "Bearer invalid_token"}
        with self.assertRaises(HTTPException):
            get_current_user(request)

    @patch("backend.services.authenticator_service.jwt.decode")
    def test_get_current_user_no_token(self, mock_jwt_decode):
        request = MagicMock()
        request.headers = {}
        with self.assertRaises(HTTPException):
            get_current_user(request)

    def test_validate_password(self):
        """
        Test the validate_password function for various password strengths.
        """
        from backend.services.authenticator_service import validate_password

        # Valid passwords
        self.assertTrue(validate_password("ValidPass1"))
        self.assertTrue(validate_password("Another1Valid"))

        # Invalid passwords
        self.assertFalse(validate_password("short"))  # Too short
        self.assertFalse(validate_password("nouppercase1"))  # No uppercase letter
        self.assertFalse(validate_password("NOLOWERCASE1"))  # No lowercase letter
        self.assertFalse(validate_password("NoNumber"))  # No number

if __name__ == "__main__":
    unittest.main()