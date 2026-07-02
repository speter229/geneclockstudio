from fastapi import APIRouter, Depends, Body, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from backend.services.authenticator_service import get_user, verify_password, create_access_token, add_user

router = APIRouter()

# Signup endpoint
@router.post("/signup")
def signup(username: str = Body(...), password: str = Body(...)):
    add_user(username, password)
    return {"message": f"User '{username}' registered successfully."}

# Login endpoint
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    token = create_access_token({"sub": user["username"]})
    return {"access_token": token,   "token_type": "bearer"}
