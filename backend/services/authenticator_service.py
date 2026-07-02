import time
import json
import os
import re  
from typing import Dict
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Request, Query
from fastapi.security import OAuth2PasswordBearer
from backend.config import PROJECT_ROOT 

# Constants
SECRET_KEY = "supersecretkey"  # Secret key for JWT encoding/decoding
ALGORITHM = "HS256"  # Algorithm used for JWT
ACCESS_TOKEN_EXPIRE_SECONDS = 4*3600  # Token expiration time in seconds
USERS_FILE = os.path.join(PROJECT_ROOT, "backend/data/users.json")  # Path to persist user data

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # Password hashing context

# Load users from file or initialize empty
def load_users() -> Dict[str, Dict[str, str]]:
    """Loads users from a JSON file or initializes an empty dictionary if the file doesn't exist."""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

# Save users to file
def save_users(users: Dict[str, Dict[str, str]]):
    """Saves the user database to a JSON file."""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)  # Ensure the directory exists
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# Persistent user store
users_db = load_users()  # Load users into memory

def verify_password(plain_password, hashed_password):
    """Verifies if a plain password matches a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password):
    """Hashes a plain password using bcrypt."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_SECONDS):
    """Creates a JWT access token with an expiration time."""
    to_encode = data.copy()
    to_encode["exp"] = time.time() + expires_delta
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    """Decodes a JWT token and retrieves the username if valid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in users_db:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_user(username: str):
    """Retrieves a user from the user database by username."""
    return users_db.get(username)

def add_user(username: str, password: str):
    """Adds a new user to the user database and persists it to disk."""
    # Check if the username already exists
    if username in users_db:
        raise HTTPException(status_code=400, detail="❌ Username already exists.")

    # Validate the password
    if not validate_password(password):
        raise HTTPException(
            status_code=400,
            detail="❌ Password must contain at least one uppercase letter, one lowercase letter, one number, and be at least 7 characters long."
        )

    # Hash the password and save the user
    users_db[username] = {
        "username": username,
        "hashed_password": hash_password(password)
    }
    save_users(users_db)  # Persist to disk

def validate_password(password: str) -> bool:
    """Validates the password against the required policy."""
    # Regex for password validation
    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{7,}$"
    return bool(re.match(pattern, password))

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")  # OAuth2 scheme for extracting tokens

def get_current_user(request: Request, token: str = Query(default=None)):
    
    # Try to get token from header or fallback to query param
    auth_header = request.headers.get("Authorization")
    jwt_token = None

    if auth_header and auth_header.startswith("Bearer "):
        jwt_token = auth_header.split(" ")[1]
    elif token:
        jwt_token = token
    if not jwt_token:
        raise HTTPException(status_code=401, detail="Token not provided")
    try:
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in users_db:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return username
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")
