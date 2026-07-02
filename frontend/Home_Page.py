import streamlit as st
import requests
import os
from auth import auth_page, require_authentication  # Import authentication logic
from frontend.config import API_URL  # Import the API_URL from config.py
from frontend.config import PROJECT_ROOT  # Import PROJECT_ROOT
from frontend.ui_utils import inject_global_css, set_background

if "token" not in st.session_state:
    st.set_page_config(page_title="Login Page", layout="centered",page_icon="frontend/assets/dna_logo.jpg", menu_items={}, initial_sidebar_state="collapsed")
else:
    st.set_page_config(page_title="Login Page", layout="centered",page_icon="frontend/assets/dna_logo.jpg", menu_items={}, initial_sidebar_state="expanded")

inject_global_css()

# Set the background image
background_image_path = os.path.join(PROJECT_ROOT, "frontend/assets/img1_dark.jpg")
set_background(background_image_path)

# Inject custom CSS to hide the Streamlit menu
hide_streamlit_menu = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_menu, unsafe_allow_html=True)

# Initialize session state for tracking the previous page
if "previous_page" not in st.session_state:
    st.session_state["previous_page"] = "Home"
st.session_state["previous_page"] = "Home"
# Initialize session state for the Help visibility
if "show_help_SignIn" not in st.session_state:
    st.session_state["show_help_SignIn"] = False
# Initialize session state for the Help visibility
if "show_help_Home" not in st.session_state:
    st.session_state["show_help_Home"] = False


# Add the Help button
if st.sidebar.button("Help"):
    # Toggle the visibility of the help section
    st.session_state["show_help_SignIn"] = not st.session_state["show_help_SignIn"]
    st.session_state["show_help_Home"] = not st.session_state["show_help_Home"]

# Display or hide the help section based on session state
if st.session_state["show_help_SignIn"] and "token" not in st.session_state:
    st.sidebar.markdown("### ℹ️ How to Log In")
    st.sidebar.markdown("""
    1. If you don't have an account, click the **Signup** button to create one (the username must be unique).
    2. If you already have an account, enter your **username** and **password**.
    3. Upon successful login, you will be redirected to the main page of the application.
    4. On the main page, you will see a **Log out** button and another button to **list the models** you have trained so far (which can be downloaded by clicking the link next to them).
    5. Also there is a short description of the application and a section about **inflammation**.
    """)

# Display or hide the help section based on session state
if st.session_state["show_help_SignIn"] and "token" in st.session_state:
    st.sidebar.markdown("### ℹ️ How to Log In")
    st.sidebar.markdown("""
    1. **Zoom In for Better Visibility:**  Use Ctrl + Mouse Scroll or Ctrl + "+" to zoom in and make the text larger. To zoom out, use Ctrl + Mouse Scroll Down or Ctrl + "-".

    2. **Navigate the Application:** Click on the **arrow icon** in the top-left corner to open the navigation bar. Use the navigation bar to switch between different pages of the application.

    3. **Access Help:** Click the **"Help"** button in the sidebar to toggle help section, the Help button give you information about the usage of your page.

    4. **Logout:** To log out, click the **"Logout"** button at the top of the page.
    """)


# Clear Streamlit cache
st.cache_data.clear()
st.cache_resource.clear()

# Authentication check
if "token" not in st.session_state:
    auth_page()  # Show the authentication page if the user is not logged in
    st.stop()  # Stop further execution until the user logs in

# Main app content (only accessible after login)
st.title(f"Hi, {st.session_state['username']}!")

headers = {
    "Authorization": f"Bearer {st.session_state['token']}"  # Ensure the token is stored in session state
}

# Initialize session state for toggling the model list and fetching models
if "show_models" not in st.session_state:
    st.session_state["show_models"] = False  # Default to not showing the models
if "fetch_models" not in st.session_state:
    st.session_state["fetch_models"] = False  # Default to not fetching models

# Button to toggle the visibility of the model list
if st.button("List previous trained models"):
    # Toggle the visibility of the model list
    st.session_state["show_models"] = not st.session_state["show_models"]
    st.session_state["fetch_models"] = st.session_state["show_models"]  # Fetch models only if showing

# Fetch models from the backend if needed
if st.session_state["fetch_models"]:
    try:
        response = requests.get(f"{API_URL}/train/list/", headers=headers, verify=False)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])

            if not models:
                st.info("No trained models found.")
                st.session_state["models"] = []  # Clear the models list
            else:
                st.session_state["models"] = models  # Store models in session state
        else:
            st.error(f"❌ Error: {response.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error communicating with the backend: {e}")
    finally:
        st.session_state["fetch_models"] = False  # Reset fetch flag after fetching

# Display models from session state if the toggle is active
if st.session_state["show_models"] and st.session_state.get("models"):
    st.write("### Trained Models")
    for model in st.session_state["models"]:
        col1, col2, col3 = st.columns([5, 2, 2])
        col1.write(f"**{model['model_filename']}**")

        # Generate the download button
        backend_url = f"{API_URL}/train/download_model/{model['model_id']}"
        try:
            response = requests.get(backend_url, headers=headers, verify=False)
            if response.status_code == 200:
                content_disp = response.headers.get("content-disposition", "")
                model_filename = "model.joblib"
                if "filename=" in content_disp:
                    model_filename = content_disp.split("filename=")[-1].strip().strip('"')

                col2.download_button(
                    label="⬇️ Download Model",
                    data=response.content,
                    file_name=model_filename,
                    mime="application/octet-stream",
                    key=f"download_{model['model_id']}"
                )
            else:
                col2.error(f"❌ Failed to prepare download: {response.status_code}")
        except requests.exceptions.RequestException as e:
            col2.error(f"❌ Error communicating with the backend: {e}")

        # Add the Delete button
        if col3.button("🗑️ Delete", key=f"delete_{model['model_id']}"):
            st.session_state["delete_model_id"] = model["model_id"]
            st.rerun()

# Handle delete action after rerun
if "delete_model_id" in st.session_state:
    model_id = st.session_state.pop("delete_model_id")
    delete_response = requests.delete(
        f"{API_URL}/train/delete_model/{model_id}",
        headers=headers,
        verify=False
    )
    if delete_response.status_code == 200:
        st.success("✅ Model deleted successfully.")
        st.session_state["models"] = [
            m for m in st.session_state["models"] if m["model_id"] != model_id
        ]
        st.rerun()
    else:
        st.error(f"❌ Failed to delete model: {delete_response.status_code} - {delete_response.text}")


# Logout button
if st.button("Logout"):
    st.session_state.clear()
    st.rerun()

# Add a welcome title
st.title("Welcome to the Inflammatory Biological Age Predictor!")

# Add the description
st.markdown("""
On this platform, you can explore training datasets based on inflammation-related genes and use them to predict biological age on your data. 
Additionally, if you have sufficient epigenetic data (DNA methylation data), you can train your biological clock using three of the most commonly used models in research: 
**ElasticNet**, **XGBoost**, and **Random Forest**. You can also restrict the CpG sites to your specific gene set.
""")

# Add a section for inflammation
st.markdown("### What is inflammation and why is it important in aging?")
st.markdown("""
Inflammation is part of the biological response of body tissues to harmful 
stimuli, such as pathogens, damaged cells, or irritants. The five cardinal signs are heat, pain, 
redness, swelling, and loss of function.
Inflammation is a protective response involving immune cells, blood vessels, and molecular mediators.
The function of inflammation is to eliminate the initial cause of cell injury, clear out damaged cells
and tissues, and initiate tissue repair. Too weak inflammation could lead to progressive tissue
destruction by harmful stimuli (e.g. bacteria) and compromise the survival of the organism.
However, inflammation can also have negative effects. Too much inflammation, in the form of chronic
inflation is associated with various diseases, such as hay fever, periodontal disease,
atherosclerosis, and osteoarthritis.
https://en.wikipedia.org/wiki/Inflammation
""")