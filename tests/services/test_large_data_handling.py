import pandas as pd
import time
import pytest
from backend.services.train_preprocess import prepocess_before_training

def test_large_beta_file_loading():
    """
    Test if the system can load and process a large beta.csv file.
    """
    # Load the large beta.csv file
    beta_file_path = "tests/data/altum_age/altumAge450k_beta_08gb.csv"
    try:
        df_betas = pd.read_csv(beta_file_path, index_col=0)
        assert not df_betas.empty, "The beta.csv file is empty."
        assert df_betas.shape[0] > 1000, "The beta.csv file should have more than 1000 rows."
        assert df_betas.shape[1] > 100, "The beta.csv file should have more than 100 columns."
    except Exception as e:
        pytest.fail(f"Failed to load the beta.csv file: {e}")

def test_large_beta_file_processing_speed():
    """
    Test the processing speed of a large beta.csv file.
    """
    # Load the large beta.csv file
    beta_file_path = "tests/data/altum_age/altumAge450k_beta_08gb.csv"
    meta_file_path = "tests/data/altum_age/altumAge450k_meta.csv"
    try:
        df_betas = pd.read_csv(beta_file_path, index_col=0)
        df_meta = pd.read_csv(meta_file_path, index_col=0)

        # Measure processing time
        start_time = time.time()
        processed_betas, processed_meta = prepocess_before_training(df_betas, df_meta)
        end_time = time.time()

        # Assert the processing was successful
        assert processed_betas.shape == df_betas.shape, "Processed beta DataFrame shape mismatch."
        assert processed_meta.shape == df_meta.shape, "Processed meta DataFrame shape mismatch."

        # Print the processing time
        processing_time = end_time - start_time
        print(f"Processing time for large beta.csv file: {processing_time:.2f} seconds")
    except Exception as e:
        pytest.fail(f"Failed to process the beta.csv file: {e}")