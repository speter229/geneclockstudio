import streamlit as st
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import requests
import json
import os
from auth import require_authentication
from frontend.config import API_URL  
import base64
from frontend.config import PROJECT_ROOT  
from backend.services.temp_service import temp_remove  
from backend.config import TEMP_PATH
from frontend.ui_utils import inject_global_css, set_background
from frontend.utils import load_chromosome_data
from frontend.utils import plot_cpgs_on_chromosomes  
from frontend.utils import cleanup_temp_files_and_session_state_3rd_page 
from frontend.utils import new_beta_temp_and_session_state_clenaup_3rd_page  
from frontend.utils import new_meta_temp_and_session_state_clenaup_3rd_page  
from frontend.utils import new_gene_temp_and_session_state_clenaup_3rd_page
from backend.services.example_datasets_service import list_example_training_datasets
from backend.services.example_datasets_service import get_example_training_dataset_paths
from backend.services.example_genesets_service import list_example_genesets
from backend.services.example_genesets_service import get_example_geneset_path
import numpy as np
import io
import shutil

st.set_page_config(page_title="Train your own gene set-specific aging clock", layout="centered",page_icon="frontend/assets/dna_logo.jpg")

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


if "previous_page" not in st.session_state or st.session_state["previous_page"] != "Create Your Own Model":
    # Call the cleanup function if we came from another page
    cleanup_temp_files_and_session_state_3rd_page()

if "previous_page" not in st.session_state:
    st.session_state["previous_page"] = "Create Your Own Model"
# Update the current page in session state
st.session_state["previous_page"] = "Create Your Own Model"

# Initialize session state for the Help visibility
if "show_help_3" not in st.session_state:
    st.session_state["show_help_3"] = False

# Add the Help button to the sidebar
if st.sidebar.button("Help"):
    # Toggle the visibility of the help section
    st.session_state["show_help_3"] = not st.session_state["show_help_3"]

# Display or hide the help section based on session state
if st.session_state["show_help_3"]:
    st.sidebar.markdown("### ℹ️ How to Use This Page")
    st.sidebar.markdown("""
    1. **Start New Training**: If you want to start a new training session, click the "🔄 Start New Training" button at the top of the page. You will be able to upload a new dataset and configure the model parameters according to your preferences.
    2. **Upload methylation and metadata files**: Upload the required methylation and metadata CSV files.
    3. **The beta values table format**: Every row is a CpG site, and every column is a sample (row and column names should be unique). Apart from that, only float values are allowed.
    4. **The metadata** table format is as follows: every column is a sample, and every row is a feature (the row must contain the 'age' column where only float values are accepted).
    5. **Optional**: If needed, filter CpG sites to a gene set, either by uploading your own gene list (CSV format, one column named `Gene_ID` with HGNC gene symbols) or by picking a bundled built-in gene set (e.g. the GenAge human ageing-related genes).
    6. **Promoter selection**: Choose whether to filter CpG sites to certain genes and whether to include only promoter regions. The promoter region is defined to encompass the TSS1500, TSS200, 5'UTR, and 1stExon genomic regions.
    7. **Filtered CpG sites**: If you filtered the sites with a gene set, the number of remaining CpG sites will be displayed, and on a plot showing their positions on chromosomes.
    8. **Choose a model**: Select a model (ElasticNet, XGBoost, RandomForest) and configure its parameters.
    9. **Train the model**: Click the "🚀 Train Model" button to start the training process.
    10. **View results**: After training is complete, the results will be displayed, and you will have the option to download the trained model.
                        """)

st.title("🧬 Train Your Own Gene Set-Specific Aging Clock")

require_authentication()

os.makedirs(TEMP_PATH, exist_ok=True)  # Create the directory if it doesn't exist

# Ensure the username is available in session state
username = st.session_state.get("username", "default_user")  # Use "default_user" if username is not set

# Create a user-specific directory in the temp path
user_temp_path = os.path.join(TEMP_PATH, username)
os.makedirs(user_temp_path, exist_ok=True)  # Create the directory if it doesn't exist

headers = {
    "Authorization": f"Bearer {st.session_state['token']}"  # Ensure the token is stored in session state
}

if "beta_uploader_key" not in st.session_state:
        st.session_state["beta_uploader_key"] = "beta_uploader_key_0"
if "meta_uploader_key" not in st.session_state:
        st.session_state["meta_uploader_key"] = "meta_uploader_key_0"
if "gene_uploader_key" not in st.session_state:
        st.session_state["gene_uploader_key"] = "gene_uploader_key_0"

if "start_button_clicked" not in st.session_state:  
    st.session_state["start_button_clicked"] = False

col1, col2 = st.columns([3, 1])  # Create two columns for the button and description

with col1:
    st.markdown(
        """
        **Click this button to initiate a new training session.**
        Use it after a completed training or when you wish to interrupt an ongoing one and begin a new process.
        """
    )

with col2:
    if st.button("🔄 Start New Training", key="start_new_training_top"):
        # Increment the keys to reset the file uploaders
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S") 
        # Reset the keys to ensure uploaded files are cleared
        st.session_state["beta_uploader_key"] = f"beta_uploader_key_{current_time}"
        st.session_state["meta_uploader_key"] = f"meta_uploader_key_{current_time}"
        st.session_state["gene_uploader_key"] = f"gene_uploader_key_{current_time}"
        # Clear other session state variables
        cleanup_temp_files_and_session_state_3rd_page()
        st.session_state["start_button_clicked"] = True
        # Rerun the page
        st.rerun()

# Add a separator line
st.markdown("<hr>", unsafe_allow_html=True)

uploaded_betas = None
uploaded_meta = None

if "uploaded_gene_name" not in st.session_state:
            st.session_state["uploaded_gene_name"] = None
if "builtin_genes_file_path" not in st.session_state:
            st.session_state["builtin_genes_file_path"] = None

if st.session_state["start_button_clicked"]:
    st.session_state["data_source_choice"] = st.radio(
        "Data source",
        ["Upload my own data", "Use an example dataset"],
        key="data_source_radio",
        horizontal=True,
    )

# Create two columns for file upload
col1, col2 = st.columns(2)

if st.session_state["start_button_clicked"] and st.session_state["data_source_choice"] == "Upload my own data":
# File upload for betas and metadata
    with col1:
        if "uploaded_betas_name" not in st.session_state:
            st.session_state["uploaded_betas_name"] = None
        uploaded_betas = st.file_uploader("Upload your methylation CSV", type=["csv"], key=st.session_state["beta_uploader_key"])
    with col2:
        if "uploaded_meta_name" not in st.session_state:
            st.session_state["uploaded_meta_name"] = None
        uploaded_meta = st.file_uploader("Upload metadata CSV with 'age' row", type=["csv"],  key=st.session_state["meta_uploader_key"])

if st.session_state["start_button_clicked"] and st.session_state["data_source_choice"] == "Use an example dataset":
    if "uploaded_betas_name" not in st.session_state:
        st.session_state["uploaded_betas_name"] = None
    if "uploaded_meta_name" not in st.session_state:
        st.session_state["uploaded_meta_name"] = None

    example_datasets = list_example_training_datasets()
    example_ids = list(example_datasets.keys())
    example_labels = [example_datasets[dataset_id]["label"] for dataset_id in example_ids]
    selected_label = st.selectbox("Choose a bundled example dataset", example_labels)
    selected_id = example_ids[example_labels.index(selected_label)]
    st.caption(example_datasets[selected_id]["description"])

    if st.button("📂 Load Example Dataset"):
        # Loading a new example dataset invalidates any previously loaded gene filter
        new_beta_temp_and_session_state_clenaup_3rd_page()
        new_meta_temp_and_session_state_clenaup_3rd_page()
        try:
            src_beta_path, src_meta_path = get_example_training_dataset_paths(selected_id)

            # Copy the bundled files into the user's own temp folder, so they are
            # treated exactly like an uploaded file by the rest of the page (preview,
            # validation, auto-cleanup) and the bundled originals are never touched.
            st.session_state["uploaded_betas_name"] = f"{selected_id}_beta.csv"
            st.session_state["betas_file_path"] = os.path.join(user_temp_path, st.session_state["uploaded_betas_name"])
            shutil.copyfile(src_beta_path, st.session_state["betas_file_path"])
            temp_remove(st.session_state["betas_file_path"])
            df_betas_preview = pd.read_csv(st.session_state["betas_file_path"], index_col=0, nrows=20)
            st.session_state["df_betas_preview"] = df_betas_preview.iloc[:20, :20]
            st.session_state["beta_read_success"] = True

            st.session_state["uploaded_meta_name"] = f"{selected_id}_meta.csv"
            st.session_state["meta_file_path"] = os.path.join(user_temp_path, st.session_state["uploaded_meta_name"])
            shutil.copyfile(src_meta_path, st.session_state["meta_file_path"])
            temp_remove(st.session_state["meta_file_path"])
            df_meta_preview = pd.read_csv(st.session_state["meta_file_path"], index_col=0, nrows=20)
            st.session_state["df_meta_preview"] = df_meta_preview.iloc[:20, :20]
            st.session_state["meta_read_success"] = True
        except Exception as e:
            st.session_state["beta_read_success"] = False
            st.session_state["meta_read_success"] = False
            st.error(f"❌ Error loading example dataset: {e}")
        st.rerun()

if "betas_file_path" not in st.session_state:
        st.session_state["betas_file_path"] = None
if "meta_file_path" not in st.session_state:
        st.session_state["meta_file_path"] = None
if "beta_read_success" not in st.session_state:
        st.session_state["beta_read_success"] = None
if "meta_read_success" not in st.session_state:
        st.session_state["meta_read_success"] = None
if "df_betas_preview" not in st.session_state:
    st.session_state["df_betas_preview"] = None
if "df_meta_preview" not in st.session_state:
    st.session_state["df_meta_preview"] = None

if uploaded_betas:
    if uploaded_betas.name != st.session_state["uploaded_betas_name"]:
        st.session_state["uploaded_betas_name"] = uploaded_betas.name
        #new beta value table uploaded
        new_beta_temp_and_session_state_clenaup_3rd_page()
        try:
            # Save the betas file to the temp directory
            st.session_state["betas_file_path"] = os.path.join(user_temp_path, uploaded_betas.name)
            #betas_file_path = os.path.join(TEMP_PATH, uploaded_betas.name)
            with open(st.session_state["betas_file_path"], "wb") as f:
                f.write(uploaded_betas.getbuffer())

            # Schedule the file for removal after 30 minutes
            temp_remove(st.session_state["betas_file_path"])

            df_betas_preview = pd.read_csv(st.session_state["betas_file_path"], index_col=0, nrows=20)
            st.session_state["df_betas_preview"]  = df_betas_preview.iloc[:20, :20]
            st.session_state["beta_read_success"] = True
        except Exception as e:
            st.session_state["beta_read_success"] = False
            st.error(f"❌ Error reading the betas file: {e}")
        st.rerun()

if st.session_state["beta_read_success"] != None:
    st.write("### ✅ Uploaded Betas File Preview")
    st.dataframe(st.session_state["df_betas_preview"])

if uploaded_meta:
    if uploaded_meta.name != st.session_state["uploaded_meta_name"]:
        st.session_state["uploaded_meta_name"] = uploaded_meta.name
        #new beta value table uploaded
        new_meta_temp_and_session_state_clenaup_3rd_page()
        try:
            # Save the metadata file to the temp directory
            st.session_state["meta_file_path"] = os.path.join(user_temp_path, uploaded_meta.name)
            with open(st.session_state["meta_file_path"] , "wb") as f:
                f.write(uploaded_meta.getbuffer())

            # Schedule the file for removal after 30 minutes
            temp_remove(st.session_state["meta_file_path"])

            df_meta_preview = pd.read_csv(st.session_state["meta_file_path"] , index_col=0, nrows=20)
            st.session_state["df_meta_preview"]= df_meta_preview.iloc[:20, :20]
            st.session_state["meta_read_success"] = True
        except Exception as e:
            st.session_state["meta_read_success"]  = False
            st.error(f"❌ Error reading the metadata file: {e}")
        st.rerun()
        
try:
    if st.session_state["meta_read_success"] == True:
        st.write("### ✅ Uploaded Metadata File Preview")
        st.dataframe(st.session_state["df_meta_preview"])
except Exception as e:
    st.error(f"❌ Error displaying the metadata DataFrame: {e}")
    # Reset session state variables related to the metadata DataFrame
    st.session_state["df_meta_preview"] = None
    st.session_state["meta_read_success"] = None
    st.rerun()  # Force a page rerun

uploaded_genes = None
genes_file_path = None
is_promoter_only = False

if "dfs_valid" not in st.session_state:
    st.session_state["dfs_valid"] = None
# Check if both files are uploaded
if st.session_state["beta_read_success"] and st.session_state["meta_read_success"] and st.session_state["dfs_valid"] == None:
    ## Check if the uploaded files are valid
    check_dfs_response = requests.post(
        f"{API_URL}/train/check_dfs/",
        json={
            "betas_path": st.session_state["betas_file_path"],
            "metadata_path": st.session_state["meta_file_path"],
        },
        headers=headers,
        verify=False
    )
    if check_dfs_response.status_code != 200:
        st.session_state["dfs_valid"] = False
        try:
            error_detail = check_dfs_response.json().get("detail", "Unknown error")
            st.error(f"❌ Error processing dataframes: {error_detail}")
            st.stop()
        except Exception as e:
            st.error(f"❌ Error processing dataframes: Unable to parse error response. {e}")
            st.stop()
    else:
        st.session_state["dfs_valid"] = True
        st.success("✅ Dataframes are valid!")

if(st.session_state["dfs_valid"] != True and st.session_state["start_button_clicked"] == True):
    st.warning("Please upload the methylation CSV and metadata CSV files in correct form to proceed.")

if "df_genes" not in st.session_state:
    st.session_state["df_genes"] = None
if "gene_cpgs_result" not in st.session_state:
    st.session_state["gene_cpgs_result"] = None
if "gene_selection_option" not in st.session_state:  
    st.session_state["gene_selection_option"] = None

if st.session_state["dfs_valid"] == True and st.session_state["gene_cpgs_result"] == None:    
    st.markdown("## **Gene Selection**")
    # Gene selection with promoter options
    st.session_state["gene_selection_option"] = st.radio(
        "Do you want to filter CpG sites to certain genes?",
        ("No", "Yes (all CpG sites in gene region)", "Yes (only CpG sites within promoter regions)")
    )

    if st.session_state["gene_selection_option"] != "No":
        # Determine promoter selection based on the chosen option
        is_promoter_only = st.session_state["gene_selection_option"] == "Yes (only CpG sites within promoter regions)"

        gene_source = st.radio(
            "Gene set source",
            ["Upload my own gene list", "Use a built-in gene set"],
            key="gene_source_radio",
            horizontal=True,
        )

        genes_file_path = None

        if gene_source == "Upload my own gene list":
            st.write("**Criteria for gene upload:**")
            st.write("- File format: CSV")
            st.write("- Must contain one column named `Gene_ID`")
            st.write("- Gene names should be listed in the `Gene_ID` column")
            st.write("-  The gene names must be HGNC gene symbols ")

            uploaded_genes = st.file_uploader("Upload a CSV file with HGNC gene symbols for filtering", type=["csv"], key=st.session_state["gene_uploader_key"])
            if uploaded_genes:
                if uploaded_genes.name != st.session_state["uploaded_gene_name"]:
                    st.session_state["uploaded_gene_name"] = uploaded_genes.name
                    #new beta value table uploaded
                    new_gene_temp_and_session_state_clenaup_3rd_page()
                    try:
                        # Save the gene filter file to the temp directory
                        genes_file_path = os.path.join(user_temp_path, uploaded_genes.name)
                        with open(genes_file_path, "wb") as f:
                            f.write(uploaded_genes.getbuffer())
                        temp_remove(genes_file_path)
                        st.session_state["df_genes"] = pd.read_csv(genes_file_path)
                    except Exception as e:
                        st.error(f"❌ Error reading the gene filter file: {e}")
                        st.stop()
                else:
                    genes_file_path = None
            else:
                st.info("Please upload a gene filter CSV file to proceed.")
                st.stop()
        else:
            example_genesets = list_example_genesets()
            geneset_ids = list(example_genesets.keys())
            geneset_labels = [example_genesets[gid]["label"] for gid in geneset_ids]
            selected_geneset_label = st.selectbox("Choose a bundled example gene set", geneset_labels)
            selected_geneset_id = geneset_ids[geneset_labels.index(selected_geneset_label)]
            st.caption(example_genesets[selected_geneset_id]["description"])

            if st.button("📂 Load Example Gene Set"):
                new_gene_temp_and_session_state_clenaup_3rd_page()
                try:
                    src_genes_path = get_example_geneset_path(selected_geneset_id)
                    dest_name = f"{selected_geneset_id}.csv"
                    dest_path = os.path.join(user_temp_path, dest_name)
                    # Copy the bundled gene set into the user's own temp folder, so the
                    # bundled original is never deleted by the backend's cleanup step.
                    shutil.copyfile(src_genes_path, dest_path)
                    temp_remove(dest_path)
                    st.session_state["uploaded_gene_name"] = dest_name
                    st.session_state["df_genes"] = pd.read_csv(dest_path)
                    genes_file_path = dest_path
                    st.session_state["builtin_genes_file_path"] = dest_path
                except Exception as e:
                    st.error(f"❌ Error loading example gene set: {e}")
                    st.stop()
            elif st.session_state.get("builtin_genes_file_path") and os.path.exists(st.session_state["builtin_genes_file_path"]):
                genes_file_path = st.session_state["builtin_genes_file_path"]
            else:
                st.info("Click \"Load Example Gene Set\" to proceed.")
                st.stop()

        if genes_file_path:
            # Send API request to filter CpG sites
            try:
                gene_cpgs_response = requests.post(
                    f"{API_URL}/train/gene_cpgs_request/",
                    json={
                        "genes_path": genes_file_path,
                        "is_promoter_only": is_promoter_only,
                    },
                    headers=headers,
                    verify=False
                )
                if gene_cpgs_response.status_code == 200:
                    st.session_state["gene_cpgs_result"] = gene_cpgs_response.json()
                    st.session_state["builtin_genes_file_path"] = None
                    st.rerun()
                else:
                    # Parse the error message from the backend
                    try:
                        error_detail = gene_cpgs_response.json().get("detail", "Unknown error")
                        st.error(f"❌ Error processing gene filter: {error_detail}")
                    except Exception:
                        st.error(f"❌ Error processing gene filter: Unable to parse error response. {gene_cpgs_response.text}")
                    st.stop()

            except Exception as e:
                st.error(f"❌ Exception occurred while calling gene_cpgs_request: {e}")
                st.stop()
model_choice = None

if(st.session_state["gene_cpgs_result"] != None):
    dfMarkPos, dfChrSize = load_chromosome_data()
    st.write("### Uploaded Gene Filter File Preview")
    st.dataframe(st.session_state["df_genes"].T)
    st.success("✅ CpG sites filtered successfully!")
    st.write("Number of CpG sites left after filtering: ", len(st.session_state["gene_cpgs_result"]["cg_selection_list"]))
    st.write("Plot of filtered genes position on chromosomes, and their average correlation with age:")
    fig = plot_cpgs_on_chromosomes(
        st.session_state["gene_cpgs_result"]["cg_selection_list"],
        st.session_state["gene_cpgs_result"]["gene_avg_correlation_list"],
        dfMarkPos,
        dfChrSize
    )
    # Save the plot to a BytesIO object
    plot_buffer = io.BytesIO()
    fig.savefig(plot_buffer, format="png", bbox_inches="tight")
    plot_buffer.seek(0)  # Move to the beginning of the buffer

    # Store the plot buffer in session state
    st.session_state["cpg_plot_buffer"] = plot_buffer
    # Render the plot
    st.pyplot(fig)
    # Add a download button for the plot
    st.download_button(
        label="📥 Download CpG Sites Plot as PNG",
        data=st.session_state["cpg_plot_buffer"],
        file_name="cpg_sites_plot.png",
        mime="image/png"
    )


if "scatterplot_fig" not in st.session_state:
    st.session_state["scatterplot_fig"] = None
if "previous_model_choice" not in st.session_state:
    st.session_state["previous_model_choice"] = None

if st.session_state["dfs_valid"] == True and (st.session_state["gene_cpgs_result"] != None or st.session_state["gene_selection_option"] == "No"):    
    model_choice = st.selectbox("## Choose a model", ["Select a model", "ElasticNet", "XGBoost", "RandomForest"], key="model_choice")

#check if the model choice has changed
if st.session_state["previous_model_choice"] != model_choice:
    st.session_state["scatterplot_fig"] = None  # Reset the scatterplot figure if the model choice changes
    st.session_state["previous_model_choice"] = model_choice  # Update the previous model choice

# Model parameters  
if model_choice == "ElasticNet":

    st.markdown("### ElasticNet Parameters")

    auto_optimize = st.checkbox(
        "Automatically optimize regularization strength (recommended)",
        value=True,
        help=(
            "Uses ElasticNetCV to search a grid of alpha/L1-ratio values with internal "
            "cross-validation (similar to glmnet's built-in tuning) and picks the best "
            "one automatically, instead of the fixed values below."
        ),
    )

    col1, col2 = st.columns(2)
    with col1:
        alpha = st.slider("Alpha (Regularization Strength)", 0.0, 1.0, 0.01, 0.001, disabled=auto_optimize)
    with col2:
        l1_ratio = st.slider("L1 Ratio (Mixing Parameter)", 0.0, 1.0, 0.5, 0.001, disabled=auto_optimize)

    col3, col4 = st.columns(2)
    with col3:
        max_iter = st.number_input("Max Iterations", min_value=1, value=10000, max_value=100000, step=100)
    with col4:
        cv = st.number_input("Cross-Validation (CV)", min_value=2, max_value=10, value=3)

    if auto_optimize:
        st.caption(
            "Auto-optimize searches alpha/L1-ratio combinations with internal CV, "
            "which takes longer than a single fixed-parameter fit — expect it to take "
            "from under a minute up to several minutes depending on dataset size."
        )

    st.session_state["elasticnet_params"] = {
        "alpha": alpha,
        "l1_ratio": l1_ratio,
        "max_iter": max_iter,
        "cv": cv,
        "auto_optimize": auto_optimize,
    }

elif model_choice == "XGBoost":
    st.markdown("### XGBoost Parameters")
    col1, col2 = st.columns(2)
    with col1:
        learning_rate = st.slider("Learning Rate", 0.01, 0.5, 0.1, 0.01)
    with col2:
        max_depth = st.slider("Max Depth", min_value=3, max_value=10, value=6, step=1)

    col3, col4 = st.columns(2)
    with col3:
        n_estimators = st.number_input("Number of Estimators", min_value=10, max_value=300, value=50, step=10)
    with col4:
        subsample = st.slider("Subsample Ratio", 0.1, 1.0, 1.0, 0.1)

    st.session_state["xgboost_params"] = {
        "learning_rate": learning_rate,
        "max_depth": max_depth,
        "n_estimators": n_estimators,
        "subsample": subsample,
    }
elif model_choice == "RandomForest":
    st.markdown("### Random Forest Parameters")
    
    col1, col2 = st.columns(2)
    with col1:
        n_estimators = st.number_input("Number of Estimators", min_value=50, max_value=200, value=100, step=10)
    with col2:
        max_depth = st.slider("Max Depth", min_value=5, max_value=20, value=10, step=1)

    col3, col4 = st.columns(2)
    with col3:
        min_samples_split = st.slider("Min Samples Split", 2, 10, 2, 1)
    with col4:
        min_samples_leaf = st.slider("Min Samples Leaf", 1, 10, 2, 1)

    col5, col6 = st.columns(2)
    with col5:
        max_features = st.selectbox("Max Features", ["sqrt", "log2", None])
    with col6:
        bootstrap = st.selectbox("Bootstrap", [True, False])

    st.session_state["random_forest_params"] = {
        "n_estimators": n_estimators,
        "max_depth": max_depth,
        "min_samples_split": min_samples_split,
        "min_samples_leaf": min_samples_leaf,
        "max_features": max_features,
        "bootstrap": bootstrap,
    }

# Train API call
if model_choice and model_choice != "Select a model":
    if st.button("🚀 Train Model"):
        try:
            # Show a spinner while the training process is happening
            with st.spinner("🚀 Training the model... Please wait."):
                # Prepare data for API call
                data = {
                    "model_name": model_choice,
                    "model_params": json.dumps(st.session_state.get(f"{model_choice.lower()}_params", {})),
                    "promoter_only": is_promoter_only
                }

                files = {
                    "betas_path": st.session_state["betas_file_path"],
                    "metadata_path": st.session_state["meta_file_path"],
                }

                if st.session_state["gene_selection_option"] != "No" and genes_file_path:
                    files["gene_filter_path"] = genes_file_path

                response = requests.post(
                    f"{API_URL}/train/train_model/",
                    json={
                        "model_name": model_choice,
                        "model_params": json.dumps(st.session_state.get(f"{model_choice.lower()}_params", {})),
                        "gene_filter_path": genes_file_path if st.session_state["gene_selection_option"] != "No" else None,
                        "is_promoter_only": is_promoter_only,
                    },
                    headers=headers,
                    verify=False  # Added verify=False for HTTPS
                )
                # If the training was successful
                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Model training finished!")

                    # Extract response data
                    y_test = result["y_test"]
                    y_pred = result["y_pred"]
                    mae = result["mae"]
                    r_value = result["r_value"]
                    download_path = result["download_path"]
                    st.session_state["download_path"] = download_path
                    st.session_state["selected_cpgs"] = result.get("selected_cpgs")
                    st.session_state["chosen_alpha"] = result.get("chosen_alpha")
                    st.session_state["chosen_l1_ratio"] = result.get("chosen_l1_ratio")

                    # Create scatterplot
                    fig, ax = plt.subplots(figsize=(5, 4))

                    # Scatterplot of predictions vs true values
                    ax.scatter(y_test, y_pred, label="Predictions", color="blue")

                    # Add the red x=y line (dotted)
                    ax.plot([min(y_test), max(y_test)], [min(y_test), max(y_test)], 'r--', label="Ideal Fit (x=y)")

                    # Add the green best-fitting line
                    m, b = np.polyfit(y_test, y_pred, 1)  # Linear regression to find slope and intercept
                    ax.plot(y_test, m * np.array(y_test) + b, 'g-', label="Best Fit Line")

                    # Add labels, title, and legend
                    ax.set_xlabel("True Values (y_test)")
                    ax.set_ylabel("Predicted Values (y_pred)")
                    #ax.set_title("Scatterplot of Predictions vs True Values")
                    ax.legend()

                    # Add text for MAE and R-value
                    ax.text(0.05, 0.95, f"MAE: {mae:.2f}\nR: {r_value:.2f}",
                            transform=ax.transAxes, fontsize=10, verticalalignment='top',
                            bbox=dict(boxstyle="round", facecolor="white", alpha=0.5))

                    # Store the figure in session state
                    st.session_state["scatterplot_fig"] = fig
                else:
                    st.error(f"❌ Error {response.status_code}: {response.text}")

        except Exception as e:
            st.error(f"❌ Exception occurred: {e}")

# Re-render the plot if it exists in session state
if st.session_state["scatterplot_fig"] != None and "scatterplot_fig" in st.session_state:
    #st.dataframe(st.session_state["model_features_order_df"])
    plot_buffer = io.BytesIO()
    st.session_state["scatterplot_fig"].savefig(plot_buffer, format="png", bbox_inches="tight")
    plot_buffer.seek(0)  # Move to the beginning of the buffer
    st.markdown("### 📊 Predicted vs Chronological Ages")
    st.pyplot(st.session_state["scatterplot_fig"])
    st.download_button(
        label="📥 Download Plot as PNG",
        data=plot_buffer,
        file_name="scatterplot.png",
        mime="image/png"
    )

    if st.session_state.get("chosen_alpha") is not None:
        st.write(
            f"**Optimized ElasticNet hyperparameters:** alpha = {st.session_state['chosen_alpha']:.5f}, "
            f"l1_ratio = {st.session_state['chosen_l1_ratio']:.3f}"
        )

    selected_cpgs = st.session_state.get("selected_cpgs")
    if selected_cpgs:
        cpg_csv_df = pd.DataFrame(selected_cpgs)
        st.write(f"### {len(cpg_csv_df)} CpG sites have a nonzero coefficient in the trained ElasticNet model.")
        st.download_button(
            label="📥 Download Selected CpG Sites (CSV)",
            data=cpg_csv_df.to_csv(index=False).encode("utf-8"),
            file_name="selected_cpg_sites.csv",
            mime="text/csv",
        )

    st.write("### The trained model with the features order is stored. You can download it from the Home page later.")