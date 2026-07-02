import warnings
import pandas as pd
import time
import pytest
from backend.services.train_service import process_training_job  # Correct import

def test_large_beta_file_training():
    """
    Test the training function with a large beta.csv file.
    """
    # Suppress warnings (e.g., InconsistentVersionWarning)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)

        # Load the large beta.csv and meta.csv files
        beta_file_path = "tests/data/altum_age/altumAge450k_beta_08gb.csv"
        meta_file_path = "tests/data/altum_age/altumAge450k_meta.csv"
        try:
            df_betas = pd.read_csv(beta_file_path, index_col=0)
            df_meta = pd.read_csv(meta_file_path, index_col=0)

            # Ensure the beta and meta files are not empty
            assert not df_betas.empty, "The beta.csv file is empty."
            assert not df_meta.empty, "The meta.csv file is empty."
            assert df_betas.shape[0] > 1000, "The beta.csv file should have more than 1000 rows."
            assert df_betas.shape[1] > 100, "The beta.csv file should have more than 100 columns."

            # Prepare training parameters
            model_name = "ElasticNet"
            params = {"alpha": 0.1, "l1_ratio": 0.5, "max_iter": 1000, "cv": 2}
            username = "test_user"

            # Measure training time
            start_time = time.time()
            result = process_training_job(df_betas, df_meta, model_name, params, username=username)
            end_time = time.time()

            # Assert the training was successful
            assert "model_id" in result, "Training result does not contain 'model_id'."
            assert "model_filename" in result, "Training result does not contain 'model_filename'."
            assert "download_path" in result, "Training result does not contain 'download_path'."

            # Print the training time
            training_time = end_time - start_time
            print(f"Training time for large beta.csv file: {training_time:.2f} seconds")

        except Exception as e:
            pytest.fail(f"Failed to train using the beta.csv file: {e}")