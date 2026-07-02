import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from backend.services.train_service import process_training_job
import pytest

class TestTrainService(unittest.TestCase):
    @patch("backend.services.train_service.cg_selection")
    @patch("backend.services.train_service.train_elasticnet_model")
    @patch("backend.services.train_service.train_xgboost_model")
    @patch("backend.services.train_service.train_random_forest_model")
    @patch("backend.services.train_service.save_model_for_user")
    @patch("backend.services.train_service.register_model_owner")
    def test_process_training_job(
        self,
        mock_register_model_owner,
        mock_save_model_for_user,
        mock_train_random_forest_model,
        mock_train_xgboost_model,
        mock_train_elasticnet_model,
        mock_cg_selection,
    ):
        # Mock inputs
        df_betas = pd.DataFrame(np.random.rand(20, 20), index=[f"cg{i}" for i in range(20)])
        df_meta = pd.DataFrame(
            np.random.rand(2, 20),
            index=["age", "other_meta"],
            columns=df_betas.columns,
        )
        model_name = "ElasticNet"
        params = {"alpha": 0.1, "l1_ratio": 0.5, "max_iter": 1000, "cv": 2}
        username = "test_user"

        # Mock return values
        mock_cg_selection.return_value = df_betas.index.tolist()

        # Mock the ElasticNet model and its predict method
        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.rand(4)  # Match the length of y_test
        mock_train_elasticnet_model.return_value = mock_model

        mock_save_model_for_user.return_value = {
            "model_id": "1234",
            "model_filename": "test_model.joblib",
            "download_path": "/train/download_model/1234",
        }

        # Call the function
        result = process_training_job(
            df_betas=df_betas,
            df_meta=df_meta,
            model_name=model_name,
            params=params,
            username=username,
        )

        # Assertions
        mock_train_elasticnet_model.assert_called_once_with(
            X_train=unittest.mock.ANY,
            y_train=unittest.mock.ANY,
            cv=params["cv"],
            alpha=params["alpha"],
            l1_ratio=params["l1_ratio"],
            max_iter=params["max_iter"],
        )
        mock_save_model_for_user.assert_called_once_with(
            mock_model, df_betas.index.tolist(), username, model_name
        )
        mock_register_model_owner.assert_called_once_with("1234", username, "test_model.joblib")

        # Check the result
        self.assertIn("model_id", result)
        self.assertIn("y_test", result)
        self.assertIn("y_pred", result)
        self.assertIn("mae", result)
        self.assertIn("r_value", result)
        self.assertEqual(result["model_id"], "1234")


def test_process_training_job_invalid_betas():
    """
    Test process_training_job with invalid df_betas (too few columns).
    """
    # Mock invalid df_betas (too few columns)
    df_betas = pd.DataFrame({"Sample1": [0.1, 0.2, 0.3]})
    df_meta = pd.DataFrame({"Sample1": [45]}, index=["age"])
    model_name = "ElasticNet"
    params = {"alpha": 0.1, "l1_ratio": 0.5}

    # Call the function and assert it raises a ValueError
    with pytest.raises(ValueError, match="Too few samples in the training data"):
        process_training_job(df_betas, df_meta, model_name, params)


if __name__ == "__main__":
    unittest.main()