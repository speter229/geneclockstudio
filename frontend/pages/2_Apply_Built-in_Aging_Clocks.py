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
from backend.services.example_datasets_service import list_example_prediction_datasets
from backend.services.example_datasets_service import materialize_example_prediction_dataset
from backend.services.example_datasets_service import is_protected_prediction_dataset
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
    2. **Upload methylation data**: Upload the CSV file containing methylation data, or pick "Use an example dataset" to try the tool with a bundled dataset. Every column is a sample, and every row is a CpG site (the first column must contain the CpG site names). The first row must contain the sample names. The first column must contain the CpG sites.
    3. **Validation**: If the uploaded file passes the validation checks, proceed to the next step.
    4. **Choose a model**: Select a model from the available options.
    5. **Run prediction**: Click the "🧠 Predict" button to start the prediction process.
    6. **View results**: The results will be displayed in a table, and you can visualize the data.
    7. **Upload metadata**: If a metadata file is available, upload it for evaluating and visualizing the results.
    8. **The metadata table format**: every column is a sample, and every row is a feature (the row must contain the 'age' column).
    """)

st.title("🔬 Apply built-in aging clocks on your methylation data")

require_authentication()

# The prediction endpoints require a logged-in user, so every call needs the token.
headers = {
    "Authorization": f"Bearer {st.session_state['token']}"
}

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
if "builtin_prediction_meta_path" not in st.session_state:
        st.session_state["builtin_prediction_meta_path"] = None

uploaded_file= None


def process_new_betas_file(betas_path: str, display_name: str, mask_cpg_ids: bool = False):
    """Loads a beta-values CSV (uploaded or bundled) into session state:
    validates it, stores a preview, and computes per-clock CpG coverage.

    Args:
        mask_cpg_ids: Hide the CpG row labels in the preview. Set for bundled demo
            datasets whose row index is the protected CpG list of a built-in clock -
            printing 20 of those identifiers would hand out 20 confirmed clock sites.
    """
    st.session_state["uploaded_betas_name_2nd_page"] = display_name
    st.session_state["feature_coverage"] = None
    st.session_state["df_betas_preview_2nd_page"] = None
    st.session_state["pred_df"] = None
    st.session_state["betas_file_path_2nd_page"] = betas_path
    st.session_state["preview_cpg_ids_masked"] = mask_cpg_ids

    df = pd.read_csv(betas_path, index_col=0)
    if not all(df.dtypes == float):
        st.error("❌ Error reading file: All values in the DataFrame must be float.")
        st.stop()
    preview = df.iloc[:20, :20]
    if mask_cpg_ids:
        preview = preview.copy()
        preview.index = [f"CpG site {i + 1}" for i in range(len(preview))]
    st.session_state["df_betas_preview_2nd_page"] = preview

    percents = requests.post(
        f"{API_URL}/predictions/calculate_percent/",
        json={"file_path": betas_path},
        headers=headers,
        verify=False
    )
    if percents.status_code == 200:
        st.session_state["feature_coverage"] = percents.json()
    else:
        st.error(f"❌ Error {percents.status_code}: {percents.text}")


if st.session_state["start_button_clicked"]:
    data_source_choice_2nd_page = st.radio(
        "Data source",
        ["Upload my own data", "Use an example dataset"],
        key="data_source_radio_2nd_page",
        horizontal=True,
    )

    if data_source_choice_2nd_page == "Upload my own data":
        uploaded_file = st.file_uploader("Upload your methylation CSV", type=["csv"], key=st.session_state["beta_uploader_key"])
    else:
        example_pred_datasets = list_example_prediction_datasets()
        example_pred_ids = list(example_pred_datasets.keys())
        example_pred_labels = [example_pred_datasets[did]["label"] for did in example_pred_ids]
        selected_pred_label = st.selectbox("Choose a bundled example dataset", example_pred_labels)
        selected_pred_id = example_pred_ids[example_pred_labels.index(selected_pred_label)]
        st.caption(example_pred_datasets[selected_pred_id]["description"])

        if st.button("📂 Load Example Dataset"):
            try:
                dest_name = f"{selected_pred_id}_beta.csv"
                dest_beta_path = os.path.join(user_temp_path, dest_name)
                dest_meta_path = os.path.join(user_temp_path, f"{selected_pred_id}_meta.csv")

                materialize_example_prediction_dataset(
                    selected_pred_id, dest_beta_path, dest_meta_path
                )
                temp_remove(dest_beta_path)
                temp_remove(dest_meta_path)
                st.session_state["builtin_prediction_meta_path"] = dest_meta_path

                # Bundled demo tables that are encrypted at rest are indexed by the
                # clocks' secret CpG sites, so their row labels stay hidden.
                is_protected_demo = is_protected_prediction_dataset(selected_pred_id)
                process_new_betas_file(
                    dest_beta_path, dest_name, mask_cpg_ids=is_protected_demo
                )
            except Exception as e:
                st.error(f"❌ Error loading example dataset: {e}")

if not uploaded_file and st.session_state["pred_df"] is not None and st.session_state.get("uploaded_betas_name_2nd_page") is None:
    st.session_state["pred_df"] = None

if "betas_file_path_2nd_page" not in st.session_state:
        st.session_state["betas_file_path_2nd_page"] = None
if "df_betas_preview_2nd_page" not in st.session_state:
    st.session_state["df_betas_preview_2nd_page"] = None
if "feature_coverage" not in st.session_state:
    st.session_state["feature_coverage"] = None


if uploaded_file:
    if uploaded_file.name != st.session_state["uploaded_betas_name_2nd_page"]:
        try:
            st.session_state["builtin_prediction_meta_path"] = None
            # Save the uploaded file to the custom temp directory
            betas_file_path = os.path.join(user_temp_path, uploaded_file.name)
            with open(betas_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Schedule the file for removal
            temp_remove(betas_file_path)

            process_new_betas_file(betas_file_path, uploaded_file.name)
        except Exception as e:
            st.error(f"❌ Error reading the uploaded file: {e}")

model_choice = None

if st.session_state["feature_coverage"] is not None and st.session_state["df_betas_preview_2nd_page"] is not None:
    # Display the preview of the DataFrame
    st.markdown("### 📊 Methylation Data Preview")
    st.dataframe(st.session_state["df_betas_preview_2nd_page"])
    if st.session_state.get("preview_cpg_ids_masked"):
        st.caption(
            "The CpG identifiers of this bundled demo dataset are part of the "
            "proprietary clock feature lists, so they are not shown."
        )

    # Display percentages of covered CpG sites in each model. The CpG lists of the
    # clocks are proprietary, so the backend reports coverage in 5% steps only.
    st.write("### Percentages of covered CpG sites in each model")
    st.write(f"**Blood inflammatory Clock 1**: at least {st.session_state['feature_coverage']['inflammation_Hannum_ELASTICNET']}%")
    st.write(f"**Multi-tissue inflammatory clock**: at least {st.session_state['feature_coverage']['inflammation_AltumAge450k_ELASTICNET']}%")
    st.write(f"**Blood inflammatory Clock 2**: at least {st.session_state['feature_coverage']['inflammation_computage_ELASTICNET']}%")
    st.write(f"**Blood inflammatory Clock XGBoost**: at least {st.session_state['feature_coverage']['inflammation_computage_XGBoost']}%")

    # Choose model
    model_choice = st.selectbox("Choose a model", ["Blood inflammatory Clock 1", "Multi-tissue inflammatory clock", "Blood inflammatory Clock 2", "Blood inflammatory Clock XGBoost"])

if "prev_model_choice" not in st.session_state:
    st.session_state["prev_model_choice"] = None

# Predict button
if st.session_state.get("betas_file_path_2nd_page") and model_choice:
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
                headers=headers,
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

    meta_df = None
    if st.session_state.get("builtin_prediction_meta_path"):
        st.caption("Using the bundled 'age' metadata for the loaded example dataset. Upload your own file below to override it.")
        meta_df = pd.read_csv(st.session_state["builtin_prediction_meta_path"], index_col=0)

    meta_file = st.file_uploader("Upload metadata CSV with 'age' row", type=["csv"], key=st.session_state["meta_uploader_key"])
    if meta_file:
        meta_df = pd.read_csv(meta_file, index_col=0)

    if meta_df is not None:
        try:

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
