import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import numpy as np
import os
import tempfile
from frontend.config import API_URL
from auth import require_authentication
import base64
from frontend.config import PROJECT_ROOT
from frontend.utils import extract_age_row
from backend.services.temp_service import temp_remove  
from backend.config import TEMP_PATH
from frontend.ui_utils import inject_global_css, set_background
from frontend.utils import cleanup_temp_files_and_session_state_2nd_page
import datetime
import io

st.set_page_config(page_title="Biological Age Predictor", layout="centered",page_icon="frontend/assets/dna_logo.jpg")

inject_global_css()

background_image_path = os.path.join(PROJECT_ROOT, "frontend/assets/img2_dark.jpg")
set_background(background_image_path)

# Inject custom CSS to hide the Streamlit menu
hide_streamlit_menu = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_menu, unsafe_allow_html=True)

if "previous_page" not in st.session_state or st.session_state["previous_page"] != "Apply built-in aging clocks":
    # Call the cleanup function if we came from another page
    cleanup_temp_files_and_session_state_2nd_page()

if "previous_page" not in st.session_state:
    st.session_state["previous_page"] = "Apply built-in aging clocks"
st.session_state["previous_page"] = "Apply built-in aging clocks"

# Initialize session state for the Help visibility
if "show_help_2" not in st.session_state:
    st.session_state["show_help_2"] = False

# Add the Help button to the sidebar
if st.sidebar.button("Help"):
    # Toggle the visibility of the help section
    st.session_state["show_help_2"] = not st.session_state["show_help_2"]

# Display or hide the help section based on session state
if st.session_state["show_help_2"]:
    st.sidebar.markdown("### ℹ️ How to Use This Page")
    st.sidebar.markdown("""
    1. **Start New Predictions**: If you want to start a new predicting session, click the "🔄 Start New Predictions" button at the top of the page. You will be able to upload a new dataset and select the aging clock model parameters according to your preferences.
    2. **Upload methylation data**: Upload the CSV file containing methylation data. Every column is a sample, and every row is a CpG site (the first column must contain the CpG site names). The first row must contain the sample names. The first column must contain the CpG sites.
    3. **Validation**: If the uploaded file passes the validation checks, proceed to the next step.
    4. **Choose a model**: Select a model from the available options.
    5. **Run prediction**: Click the "🧠 Predict" button to start the prediction process.
    6. **View results**: The results will be displayed in a table, and you can visualize the data.
    7. **Upload metadata**: If a metadata file is available, upload it for evaluating and visualizing the results.
    8. **The metadata table format**: every column is a sample, and every row is a feature (the row must contain the 'age' column).
    """)

st.title("🔬 Apply built-in aging clocks on your methylation data")

require_authentication()

# Ensure the username is available in session state
username = st.session_state.get("username", "default_user")  # Use "default_user" if username is not set

# Create a user-specific directory in the temp path
user_temp_path = os.path.join(TEMP_PATH, username)
os.makedirs(user_temp_path, exist_ok=True)  # Create the directory if it doesn't exist

# Session state init
if "pred_df" not in st.session_state:
    st.session_state["pred_df"] = None

os.makedirs(TEMP_PATH, exist_ok=True)  # Create the directory if it doesn't exist

if "start_button_clicked" not in st.session_state:  
    st.session_state["start_button_clicked"] = False

# Add "Start New Training" button at the top
col1, col2 = st.columns([3, 1])  # Create two columns for the button and description

with col1:
    st.markdown(
        """
        **Click this button to initiate a new training session.**
        Use it after a completed training or when you wish to interrupt an ongoing one and begin a new process.
        """
    )
with col2:
    if st.button("🔄 Start New Predictions", key="start_new_predictions_top"):
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S") 
        st.session_state["beta_uploader_key"] = f"beta_uploader_key_{current_time}"
        st.session_state["meta_uploader_key"] = f"meta_uploader_key_{current_time}"
        # Clear other session state variables (optional)
        cleanup_temp_files_and_session_state_2nd_page()
        st.session_state["start_button_clicked"] = True
        # Rerun the script
        st.rerun()

# Add a separator line
st.markdown("<hr>", unsafe_allow_html=True)

if "uploaded_betas_name_2nd_page" not in st.session_state:
        st.session_state["uploaded_betas_name_2nd_page"] = None
if "beta_uploader_key" not in st.session_state:
        st.session_state["beta_uploader_key"] = "beta_uploader_key_0"
if "meta_uploader_key" not in st.session_state:
        st.session_state["meta_uploader_key"] = "meta_uploader_key_0"

uploaded_file= None

if st.session_state["start_button_clicked"]:
    # Upload methylation file
    uploaded_file = st.file_uploader("Upload your methylation CSV", type=["csv"], key=st.session_state["beta_uploader_key"])

if not uploaded_file and st.session_state["pred_df"] is not None:
    st.session_state["pred_df"] = None

if "betas_file_path_2nd_page" not in st.session_state:
        st.session_state["betas_file_path_2nd_page"] = None
if "df_betas_preview_2nd_page" not in st.session_state:
    st.session_state["df_betas_preview_2nd_page"] = None
if "feature_coverage" not in st.session_state:
    st.session_state["feature_coverage"] = None


if uploaded_file:
    if uploaded_file.name != st.session_state["uploaded_betas_name_2nd_page"]:     
        st.session_state["uploaded_betas_name_2nd_page"] = uploaded_file.name
        try:
            #new file has been uploaded
            st.session_state["feature_coverage"] = None  
            st.session_state["df_betas_preview_2nd_page"] = None
            st.session_state["pred_df"] = None
            # Save the uploaded file to the custom temp directory
            st.session_state["betas_file_path_2nd_page"] = os.path.join(user_temp_path, uploaded_file.name)
            with open(st.session_state["betas_file_path_2nd_page"], "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Schedule the file for removal
            temp_remove(st.session_state["betas_file_path_2nd_page"])
            
            df = pd.read_csv(st.session_state["betas_file_path_2nd_page"], index_col=0)
            if not all(df.dtypes == float):
                st.error("❌ Error reading uploaded file: All values in the DataFrame must be float.")
                st.stop()
            #save df preview to session state for later displaying
            st.session_state["df_betas_preview_2nd_page"]=df.iloc[:20, :20]

            index_list = df.index.tolist()
            # Calculate the feature coverage for each model 
            percents = requests.post(
                f"{API_URL}/predictions/calculate_percent/",
                json={"file_path": st.session_state["betas_file_path_2nd_page"]},  # Send data as JSON
                verify=False
            )

            if percents.status_code == 200:
                # Parse the response JSON
                percent_data = percents.json()
                st.session_state["feature_coverage"] = percent_data               
            else:
                st.error(f"❌ Error {percents.status_code}: {percents.text}")

        except Exception as e:
            st.error(f"❌ Error reading the uploaded file: {e}")
            
model_choice = None

if st.session_state["feature_coverage"] is not None and st.session_state["df_betas_preview_2nd_page"] is not None:
    # Display the preview of the DataFrame
    st.markdown("### 📊 Methylation Data Preview")
    st.dataframe(st.session_state["df_betas_preview_2nd_page"])

    # Display percentages of covered CpG sites in each model
    st.write("### Percentages of covered CpG sites in each model")
    st.write(f"**Blood inflammatory Clock 1**: {st.session_state['feature_coverage']['inflammation_Hannum_ELASTICNET']}%")
    st.write(f"**Multi-tissue inflammatory clock**: {st.session_state['feature_coverage']['inflammation_AltumAge450k_ELASTICNET']}%")
    st.write(f"**Blood inflammatory Clock 2**: {st.session_state['feature_coverage']['inflammation_computage_ELASTICNET']}%")
    st.write(f"**Blood inflammatory Clock XGBoost**: {st.session_state['feature_coverage']['inflammation_computage_XGBoost']}%")

    # Choose model
    model_choice = st.selectbox("Choose a model", ["Blood inflammatory Clock 1", "Multi-tissue inflammatory clock", "Blood inflammatory Clock 2", "Blood inflammatory Clock XGBoost"])

if "prev_model_choice" not in st.session_state:
    st.session_state["prev_model_choice"] = None

# Predict button
if uploaded_file and model_choice:
    if st.button("🧠 Predict"):
        st.session_state["prev_model_choice"] = model_choice  # Reset the prediction DataFrame

        data = {
            "model_name": model_choice,
            "file_path": st.session_state["betas_file_path_2nd_page"]  # Pass the file path to the backend
        }

        with st.spinner("Predicting..."):
            response = requests.post(
                f"{API_URL}/predictions/predict/",
                json=data,  # Send data as JSON
                verify=False
            )

        if response.status_code == 200:
            result = response.json()
            pred_df = pd.DataFrame(result["predictions"])
            pred_df["PredictedAge"] = pred_df["predictions"].apply(lambda x: x["PredictedAge"] if isinstance(x, dict) else json.loads(x)["PredictedAge"])
            pred_df.drop(columns=["predictions"], inplace=True)
            st.session_state["pred_df"] = pred_df
            st.success("✅ Prediction successful!")

        else:
            try:
                error_msg = response.json().get("detail", "Unknown error")
            except Exception:
                error_msg = response.text
            st.error(f"❌ Error {response.status_code}: {error_msg}")



# Always show predictions if they are available and no new model is selected
if st.session_state["pred_df"] is not None and st.session_state["prev_model_choice"] == model_choice:
    st.markdown("### 📊 Predictions")
    st.dataframe(st.session_state["pred_df"].T)       
else:
    st.session_state["pred_df"]=None
    st.session_state["prev_model_choice"] = None  # Reset the prediction model choice
    current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S") 
    st.session_state["meta_uploader_key"] = f"meta_uploader_key_{current_time}"

# Metadata upload for evaluation (if prediction exists)
if st.session_state["pred_df"] is not None and st.session_state["prev_model_choice"] == model_choice:
    st.markdown("---")
    st.markdown("### 📁 Upload metadata for evaluation")

    meta_file = st.file_uploader("Upload metadata CSV with 'age' row", type=["csv"], key=st.session_state["meta_uploader_key"])
    if meta_file:
        try:
            meta_df = pd.read_csv(meta_file, index_col=0)
            
            # Use the refactored function to extract the age row
            age_row = extract_age_row(meta_df)
            pred_df = st.session_state["pred_df"]
            
            # Align the age row with the prediction indices
            try:
                # Check if all prediction indices are present in the age_row
                missing_indices = [idx for idx in pred_df.index if idx not in age_row.index]
                if missing_indices:
                    raise ValueError("No age value for every sample in the beta dataframe. (The meta data columns do not contain the beta data columns.)")

                ages = age_row[pred_df.index]
                ages = ages.astype(float)
                predictions = pred_df["PredictedAge"]

                # Plot
                fig, ax = plt.subplots()
                ax.scatter(ages, predictions, label="Data Points", color="blue")

                # Add the best-fitting line
                m, b = np.polyfit(ages, predictions, 1)  # Linear regression
                ax.plot(ages, m * ages + b, 'g--', label="Best Fit Line")  # Green dotted line

                # Add diagonal line for reference
                ax.plot([ages.min(), ages.max()], [ages.min(), ages.max()], 'r--', label="Ideal Fit")  # Red dashed line

                # Add title and labels
                ax.set_title("Predicted vs. Chronological Age")
                ax.set_xlabel("Chronological Age")
                ax.set_ylabel("Predicted Age")

                # Calculate metrics
                mae = (abs(ages - predictions)).mean()
                r = ages.corr(predictions)

                # Add MAE and R to the plot in the bottom-right corner
                ax.text(
                    0.95, 0.05, f"MAE: {mae:.2f}\nR: {r:.2f}",
                    transform=ax.transAxes, fontsize=10, verticalalignment='bottom',
                    horizontalalignment='right', bbox=dict(boxstyle="round", facecolor="white", alpha=0.5)
                )

                # Add legend
                ax.legend()

                # Save the plot to a BytesIO object
                plot_buffer = io.BytesIO()
                fig.savefig(plot_buffer, format="png", bbox_inches="tight")
                plot_buffer.seek(0)  # Move to the beginning of the buffer

                # Display the plot
                st.pyplot(fig)

                # Add a download button for the plot
                st.download_button(
                    label="📥 Download Plot as PNG",
                    data=plot_buffer,
                    file_name="predicted_vs_chronological_age.png",
                    mime="image/png"
                )

            except ValueError as e:
                st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"❌ Error processing metadata: {e}")
        except Exception as e:
            st.error(f"❌ Error processing metadata: {e}")
else:
    st.info("🔎 Upload methylation data and run prediction to enable evaluation.")
