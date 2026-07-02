import warnings
import pandas as pd
import time
import pytest
from backend.services.predictive_model_service import predict_biological_age

def test_large_beta_file_prediction():
    """
    Test the prediction function with a large beta.csv file.
    """
    # Elnyomjuk az InconsistentVersionWarning figyelmeztetéseket
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)

        # Load the large beta.csv file
        beta_file_path = "tests/data/altum_age/altumAge450k_beta_08gb.csv"
        try:
            df_betas = pd.read_csv(beta_file_path, index_col=0)

            # Ensure the beta file is not empty
            assert not df_betas.empty, "The beta.csv file is empty."
            assert df_betas.shape[0] > 1000, "The beta.csv file should have more than 1000 rows."
            assert df_betas.shape[1] > 100, "The beta.csv file should have more than 100 columns."

            # Measure prediction time
            start_time = time.time()
            result = predict_biological_age("Blood inflammatory Clock 1", df_betas)
            end_time = time.time()

            # Assert the prediction was successful
            assert "predictions" in result, "Prediction result does not contain 'predictions'."
            predictions = result["predictions"]
            assert len(predictions) == df_betas.shape[1], "Number of predictions does not match the number of samples."

            # Print the prediction time
            prediction_time = end_time - start_time
            print(f"Prediction time for large beta.csv file: {prediction_time:.2f} seconds")

        except Exception as e:
            pytest.fail(f"Failed to predict using the beta.csv file: {e}")