import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from auth import require_authentication
from frontend.config import API_URL
import base64
from frontend.config import PROJECT_ROOT 
import os
from frontend.ui_utils import inject_global_css, set_background

# Set page configuration
st.set_page_config(
    page_title="Inspect clock datasets and aging clocks",
    layout="centered",
    menu_items={},  # Hides the Streamlit menu
    page_icon="frontend/assets/dna_logo.jpg"
)

inject_global_css()

background_image_path = os.path.join(PROJECT_ROOT, "frontend/assets/img2_dark.jpg")
set_background(background_image_path)

if "previous_page" not in st.session_state:
    st.session_state["previous_page"] = "Inspect Training Datasets"
st.session_state["previous_page"] = "Inspect Training Datasets"

st.title("Inspect Training Datasets")
require_authentication()

# Initialize session state for the Help visibility
if "show_help_1" not in st.session_state:
    st.session_state["show_help_1"] = False

# Add the Help button to the sidebar
if st.sidebar.button("Help"):
    # Toggle the visibility of the help section
    st.session_state["show_help_1"] = not st.session_state["show_help_1"]

# Display or hide the help section based on session state
if st.session_state["show_help_1"]:
    st.sidebar.markdown("### ℹ️ How to Use This Page")
    st.sidebar.markdown("""
    1. **Choose a dataset**: Select a dataset from the available options.
    2. **View dataset details**: Once selected, you can view metadata, age distribution, and the clocks listed which were trained on the displayed dataset.
    Also, the research results are listed with the given aging clocks.
    3. **Navigate back**: Use the "Back" button to return to the dataset selection screen.
""")

# Function to load dataset from the backend
@st.cache_data(show_spinner="Loading dataset...")
def load_dataset(name):
    response = requests.get(f"{API_URL}/datasets/{name}", verify=False)
    response.raise_for_status()
    data = response.json()
    return data

# Initialize session state for dataset selection
if "selected_dataset" not in st.session_state:
    st.session_state["selected_dataset"] = None

# Main screen with dataset selection buttons
if st.session_state["selected_dataset"] is None:
    st.write("### Choose a dataset you would like to see:")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("GSE40279", key="gse40279_button"):
            st.session_state["selected_dataset"] = "GSE40279"
            st.rerun()  # Force rerun to immediately reflect the state change

    with col2:
        if st.button("Computage bench", key="computage_button"):
            st.session_state["selected_dataset"] = "Computage"
            st.rerun()  # Force rerun to immediately reflect the state change

    with col3:
        if st.button("AltumAge", key="altumage_button"):
            st.session_state["selected_dataset"] = "AltumAge"
            st.rerun()  # Force rerun to immediately reflect the state change

# Dataset display screen
else:
    try:
        # Back button to return to the main screen
        if st.button("Back", key="back_button"):
            st.session_state["selected_dataset"] = None
            st.rerun()  # Force rerun to immediately reflect the state change

        dataset_data = load_dataset(st.session_state["selected_dataset"])

        # Display dataset description
        st.write("### Dataset Description")
        st.write(dataset_data["description"])

        # Display metadata
        metadata = pd.DataFrame(dataset_data["metadata"])
        st.write("### Metadata Preview")
        st.write("Each column represents a sample, and each row represents an attribute.")
        st.dataframe(metadata)

        # Display age distribution
        age_values = dataset_data["ages"]
        fig, ax = plt.subplots(figsize=(6, 4))  # Set a fixed size for the plot
        ax.hist(age_values, bins=20, edgecolor="black")
        ax.set_title("Distribution of Ages")
        ax.set_xlabel("Age")
        ax.set_ylabel("Frequency")
        ax.set_xlim(0, 100)  # Set x-axis limit for better visibility
        st.pyplot(fig)

        trained_clocks = dataset_data.get("trained_clocks", "No clocks available for this dataset.")
        st.write("### Clocks trained on this dataset:")
        st.write(trained_clocks)
        #for the GSE40279 study there are research results for the clocks trained on this dataset.
        if st.session_state["selected_dataset"] == "GSE40279":
            if "study_description_1" in dataset_data:
                st.write("### Evaluation of rejuvenation")
                st.write(dataset_data["study_description_1"])
            if "study_scatterplot_1" in dataset_data:
                hannum_rejuv_plot = os.path.join(PROJECT_ROOT, dataset_data["study_scatterplot_1"])
                st.image(hannum_rejuv_plot, use_container_width=True)
            if "study_description_2" in dataset_data:
                st.write("### Cancer predictions")
                st.write(dataset_data["study_description_2"])
            if "study_scatterplot_2" in dataset_data:
                computage_disease_plot = os.path.join(PROJECT_ROOT, dataset_data["study_scatterplot_2"])
                st.image(computage_disease_plot, use_container_width=True)
            if "study_description_3" in dataset_data:
                st.write(dataset_data["study_description_3"])
            if "study_boxplot_1" in dataset_data:
                computage_disease_boxplot = os.path.join(PROJECT_ROOT, dataset_data["study_boxplot_1"])
                st.image(computage_disease_boxplot, use_container_width=True)
        #for the Computage study there are research results for the clocks trained on this dataset.
        if st.session_state["selected_dataset"] == "Computage":
            if "study_description_1" in dataset_data:
                st.write("### Disease predictions")
                st.write(dataset_data["study_description_1"])
            if "study_scatterplot_1" in dataset_data:
                computage_disease_plot = os.path.join(PROJECT_ROOT, dataset_data["study_scatterplot_1"])
                st.image(computage_disease_plot, use_container_width=True)
            if "study_description_2" in dataset_data:
                st.write(dataset_data["study_description_2"])
            if "study_boxplot_1" in dataset_data:
                computage_disease_boxplot = os.path.join(PROJECT_ROOT, dataset_data["study_boxplot_1"])
                st.image(computage_disease_boxplot, use_container_width=True)
        if st.button("Back", key="back_button2"):
            st.session_state["selected_dataset"] = None
            st.rerun()  # Force rerun to immediately reflect the state change

    except requests.HTTPError as e:
        st.error(f"❌ Error retrieving dataset: {e}")
    except Exception as e:
        st.error(f"❌ An unexpected error occurred: {e}")


