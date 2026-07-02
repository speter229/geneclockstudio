import streamlit as st
import requests
from frontend.config import API_URL  # Import the API_URL from config.py


def auth_page():
    st.title("Welcome to the Inflammatory Biological Age Predictor!")
    mode = st.radio("Login or if you do not have an account yet, then Signup", ["Login", "Signup"], horizontal=True)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")  # Built-in password masking

    # Display password criteria during signup
    if mode == "Signup":
        st.markdown(
            """
            **Password must meet the following criteria:**
            - At least 7 characters long
            - Contains at least one uppercase letter
            - Contains at least one lowercase letter
            - Contains at least one number
            """
        )

    if mode == "Login":
        if st.button("Login"):
            if username and password:
                response = requests.post(
                    f"{API_URL}/authenticate/login",
                    data={"username": username, "password": password},
                    verify=False  # Disable SSL verification for self-signed certificate
                )
                if response.status_code == 200:
                    
                    st.session_state["token"] = response.json()["access_token"]
                    st.session_state["username"] = username
                    st.success(f"✅ Logged in as: {username}")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials.")
            else:
                st.warning("Please enter both fields.")
    else:
        if st.button("Sign up"):
            if username and password:
                # Sign up the user
                response = requests.post(
                    f"{API_URL}/authenticate/signup",
                    json={"username": username, "password": password},
                    verify=False  # Disable SSL verification for self-signed certificate
                )
                if response.status_code == 200:
                    st.success("✅ Signup successful. Logging you in...")
                    # Automatically log in the user after signup
                    login_response = requests.post(
                        f"{API_URL}/authenticate/login",
                        data={"username": username, "password": password},
                        verify=False  # Disable SSL verification for self-signed certificate
                    )
                    if login_response.status_code == 200:
                        st.session_state["token"] = login_response.json()["access_token"]
                        st.session_state["username"] = username
                        st.success(f"✅ Logged in as: {username}")
                        st.rerun()
                    else:
                        st.error("❌ Login failed after signup. Please try logging in manually.")
                else:
                    st.error(response.json().get("detail", "Signup failed"))
            else:
                st.warning("Please enter both fields.")

def require_authentication():
    if "token" not in st.session_state:
        st.warning("You are not logged in. Please log in first.")
        st.stop()