import pandas as pd
import os
import threading
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from frontend.config import PROJECT_ROOT 
import shutil
from backend.config import TEMP_PATH
import datetime

def extract_age_row(meta_df: pd.DataFrame) -> pd.Series:
    """
    Extracts the 'age' row from the metadata DataFrame.

    Args:
        meta_df (pd.DataFrame): The metadata DataFrame.

    Returns:
        pd.Series: The 'age' row as a float series.

    Raises:
        ValueError: If the 'age' row is not found or contains invalid values.
    """
    if 'age' in meta_df.index.str.lower():
        age_row_index = meta_df.index.str.lower().get_loc('age')
        age_row = meta_df.iloc[age_row_index].astype(float)  # Ensure the row is float type
        if age_row.isnull().any():
            raise ValueError("The 'Age' row contains missing values or NaNs.")
        return age_row
    else:
        raise ValueError("'Age' row not found.")


# Perform cleanup of temporary files and session states
def cleanup_temp_files_and_session_state_3rd_page():
    """
    Cleans up temporary files and resets session state variables for the third page,
    including resetting file uploaders to their default state.
    """
    # Get the username from session state
    username = st.session_state.get("username", "default_user")
    user_temp_path = os.path.join(TEMP_PATH, username)

    # List of session state variables that store file paths
    file_variables = [
        "betas_file_path",
        "meta_file_path",
        "genes_file_path"
    ]
    
    # Remove files if they exist
    for var in file_variables:
        if var in st.session_state and st.session_state[var]:
            file_path = st.session_state[var]
            if os.path.exists(file_path):
                os.remove(file_path)
            st.session_state[var] = None  # Clear the session state variable

    # Remove the user-specific directory and all its contents
    if os.path.exists(user_temp_path):
        shutil.rmtree(user_temp_path)

    # Clear other session state variables
    other_variables = [
        "uploaded_betas_name",
        "uploaded_meta_name",
        "uploaded_gene_name",
        "beta_read_success",
        "meta_read_success",
        "df_betas_preview",
        "df_meta_preview",
        "df_genes",
        "dfs_valid",
        "gene_cpgs_result",
        "elasticnet_params",
        "xgboost_params",
        "random_forest_params",
        "download_path",
        "scatterplot_fig",
        "gene_selection_option",
        "show_help_3",
        "data_source_choice",
    ]
    for var in other_variables:
        if var in st.session_state:
            st.session_state[var] = None

    # Remove widget-tied session state variables for file uploaders
    widget_tied_variables = [
        "betas_file",
        "meta_file",
        "genes_file",
        "model_choice",
        "data_source_radio",
    ]
    for var in widget_tied_variables:
        if var in st.session_state:
            del st.session_state[var]  # Remove the variable to reset the file uploader

def new_beta_temp_and_session_state_clenaup_3rd_page():
    """
    Cleans up session states after a new betadata file is uploaded.
    """
    # Get the username from session state
    username = st.session_state.get("username", "default_user")
    user_temp_path = os.path.join(TEMP_PATH, username)

    current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S") 
    st.session_state["gene_uploader_key"] = f"gene_uploader_key_{current_time}"

    # List of session state variables that store file paths
    file_variables = [
        "genes_file_path"
    ]
    
    # Remove files if they exist
    for var in file_variables:
        if var in st.session_state and st.session_state[var]:
            file_path = st.session_state[var]
            if os.path.exists(file_path):
                os.remove(file_path)
            st.session_state[var] = None  # Clear the session state variable

    # Clear other session state variables
    other_variables = [
        "uploaded_gene_name",
        "beta_read_success",
        "df_betas_preview",
        "df_genes",
        "dfs_valid",
        "gene_cpgs_result",
        "elasticnet_params",
        "xgboost_params",
        "random_forest_params",
        "download_path",
        "scatterplot_fig",
        "gene_selection_option",
        "show_help_3",
    ]
    for var in other_variables:
        if var in st.session_state:
            st.session_state[var] = None

    # Remove widget-tied session state variables for file uploaders
    widget_tied_variables = [
        "betas_file",
        "genes_file",
        "model_choice",
    ]
    for var in widget_tied_variables:
        if var in st.session_state:
            del st.session_state[var]  # Remove the variable to reset the file uploader

def new_meta_temp_and_session_state_clenaup_3rd_page():
    """
    Cleans up session states after a new metadata file is uploaded.
    """
    # Get the username from session state
    username = st.session_state.get("username", "default_user")
    user_temp_path = os.path.join(TEMP_PATH, username)

    current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S") 
    st.session_state["gene_uploader_key"] = f"gene_uploader_key_{current_time}"

    # List of session state variables that store file paths
    file_variables = [
        "genes_file_path"
    ]
    
    # Remove files if they exist
    for var in file_variables:
        if var in st.session_state and st.session_state[var]:
            file_path = st.session_state[var]
            if os.path.exists(file_path):
                os.remove(file_path)
            st.session_state[var] = None  # Clear the session state variable

    # Clear other session state variables
    other_variables = [
        "uploaded_gene_name",
        "meta_read_success",
        "df_meta_preview",
        "df_genes",
        "dfs_valid",
        "gene_cpgs_result",
        "elasticnet_params",
        "xgboost_params",
        "random_forest_params",
        "download_path",
        "scatterplot_fig",
        "gene_selection_option",
        "show_help_3",
    ]
    for var in other_variables:
        if var in st.session_state:
            st.session_state[var] = None

    # Remove widget-tied session state variables for file uploaders
    widget_tied_variables = [
        "meta_file",
        "genes_file",
        "model_choice",
    ]
    for var in widget_tied_variables:
        if var in st.session_state:
            del st.session_state[var]  # Remove the variable to reset the file uploader

def new_gene_temp_and_session_state_clenaup_3rd_page():
    """
    Cleans up session states after a new gene file is uploaded.
    """
    # Get the username from session state
    username = st.session_state.get("username", "default_user")
    user_temp_path = os.path.join(TEMP_PATH, username)

    # List of session state variables that store file paths
    file_variables = [
        "genes_file_path"
    ]
    
    # Remove files if they exist
    for var in file_variables:
        if var in st.session_state and st.session_state[var]:
            file_path = st.session_state[var]
            if os.path.exists(file_path):
                os.remove(file_path)
            st.session_state[var] = None  # Clear the session state variable

    # Clear other session state variables
    other_variables = [
        "gene_cpgs_result",
        "elasticnet_params",
        "xgboost_params",
        "random_forest_params",
        "download_path",
        "scatterplot_fig",
        "show_help_3",
    ]
    for var in other_variables:
        if var in st.session_state:
            st.session_state[var] = None

    # Remove widget-tied session state variables for file uploaders
    widget_tied_variables = [
        "model_choice",
    ]
    for var in widget_tied_variables:
        if var in st.session_state:
            del st.session_state[var]  # Remove the variable to reset the file uploader

def cleanup_temp_files_and_session_state_2nd_page():
    """
    Cleans up temporary files and resets session state variables for the second page.
    """
    # Get the username from session state
    username = st.session_state.get("username", "default_user")
    user_temp_path = os.path.join(TEMP_PATH, username)

    # List of session state variables that store file paths
    file_variables = [
        "betas_file_path_2nd_page"
    ]

    # Remove files if they exist
    for var in file_variables:
        if var in st.session_state and st.session_state[var]:
            file_path = st.session_state[var]
            if os.path.exists(file_path):
                os.remove(file_path)
            st.session_state[var] = None  # Clear the session state variable

    # Remove the user-specific directory and all its contents
    if os.path.exists(user_temp_path):
        shutil.rmtree(user_temp_path)

    # Clear other session state variables
    other_variables = [
        "uploaded_betas_name_2nd_page",
        "df_betas_preview_2nd_page",
        "feature_coverage",
        "pred_df",
        "model_choice_2nd_page"
    ]
    for var in other_variables:
        if var in st.session_state:
            st.session_state[var] = None

def load_chromosome_data():
    """
    Load the data files.
    """
    # Construct the file paths using PROJECT_ROOT
    dfMarkPos_path = os.path.join(PROJECT_ROOT, "backend/data/dfMarkPos.csv")
    dfChrSize_path = os.path.join(PROJECT_ROOT, "backend/data/dfChrSize.csv")

    # Load the data files
    dfMarkPos = pd.read_csv(dfMarkPos_path)  # CpG positions
    dfChrSize = pd.read_csv(dfChrSize_path)  # Chromosome lengths

    # Ensure chromosome names are strings and clean
    dfMarkPos['chrName'] = dfMarkPos['chrName'].astype(str).str.strip()
    dfChrSize['chrName'] = dfChrSize['chrName'].astype(str).str.strip()

    return dfMarkPos, dfChrSize

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

def plot_cpgs_on_chromosomes(cpgs_to_plot, cpgs_to_plot_type, dfMarkPos, dfChrSize, mark_height=2*1e6):
    assert len(cpgs_to_plot) == len(cpgs_to_plot_type), "CpG names and types must have the same length."

    # Define the colormap and normalization
    colormap = colormap = plt.cm.RdBu   # transition from cool (blue) to warm (red)
    norm = mcolors.Normalize(vmin=-0.2, vmax=0.2)  # Normalize values to the range -0.2 to 0.2

    # Map the float values to colors using the colormap
    cpgs_to_plot_colors = [colormap(norm(value)) for value in cpgs_to_plot_type]

    # Create a DataFrame for plotting
    dfTypes = pd.DataFrame({
        'markName': cpgs_to_plot,
        'markColor': cpgs_to_plot_colors
    })

    # Normalize formatting
    dfMarkPos['markName'] = dfMarkPos['markName'].astype(str).str.strip()
    dfTypes['markName'] = dfTypes['markName'].astype(str).str.strip()
    dfFiltered = dfMarkPos[dfMarkPos['markName'].isin(cpgs_to_plot)].copy()
    dfFiltered = dfFiltered.merge(dfTypes, on='markName', how='left')

    # Plot setup
    fig, ax = plt.subplots(figsize=(12, 8))
    x_positions = range(len(dfChrSize))

    # Draw chromosomes
    for i, row in dfChrSize.iterrows():
        ax.bar(
            x=i, height=row['chrSize'], width=0.7, bottom=0,
            color='#A9A9A9', edgecolor='black'
        )

    # Draw CpG marks
    for _, row in dfFiltered.iterrows():
        chr_name = str(row['chrName']).strip().split('.')[0]
        mark_name = str(row['markName'])
        mark_pos = row['markPos']
        mark_color = row['markColor']

        if chr_name in dfChrSize['chrName'].values:
            chr_index = dfChrSize[dfChrSize['chrName'] == chr_name].index[0]
            ax.bar(x=chr_index, height=mark_height, width=0.7, bottom=mark_pos, color=mark_color)
        
    # Customize plot
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(dfChrSize['chrName'], rotation=90)
    ax.set_ylabel("Position (bp)")
    ax.set_xlabel("Chromosome")
    ax.set_title("CpG Site Positions on Human Chromosomes")
    ax.set_ylim(0, dfChrSize['chrSize'].max() * 1.05)
    plt.tight_layout()

    # Add a colorbar to show the mapping of values to colors
    sm = plt.cm.ScalarMappable(cmap=colormap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax)
    cbar.set_label("Correlation Value")

    return fig