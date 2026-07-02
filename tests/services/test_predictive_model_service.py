import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
import pytest
from backend.services.predictive_model_service import (
    calculate_percent,
    reorder_df_for_model,
    predict_biological_age,
    calculate_percent,
)

class TestPredictiveModelService(unittest.TestCase):
    @patch("backend.services.predictive_model_service.pd.read_csv")
    def test_calculate_percent(self, mock_read_csv):
        # Mock data
        clock_cpgs = ["cg1", "cg2", "cg3", "cg4"]
        table_cpgs = ["cg1", "cg2", "cg5"]

        # Call the function
        percent = calculate_percent(clock_cpgs, table_cpgs)

        # Assert the result
        self.assertEqual(percent, 50.0)  # 2 out of 4 CpGs are present (50%)

    @patch("backend.services.predictive_model_service.pd.read_csv")
    def test_reorder_df_for_model(self, mock_read_csv):
        # Mock data
        cg_order_df = pd.DataFrame(index=["cg1", "cg2", "cg3", "cg4"])
        df_betas = pd.DataFrame(
            {
                "Sample1": [0.1, 0.2, 0.3],
                "Sample2": [0.4, 0.5, 0.6],
            },
            index=["cg1", "cg2", "cg5"],
        )
        mock_read_csv.return_value = pd.DataFrame({"mean": [0.7, 0.8]}, index=["cg3", "cg4"])

        # Call the function
        reordered_df = reorder_df_for_model(cg_order_df, df_betas)

        # Assert the result
        self.assertEqual(reordered_df.shape, (4, 2))  # 4 CpGs, 2 samples
        self.assertTrue("cg3" in reordered_df.index)  # Missing CpG filled
        self.assertTrue("cg4" in reordered_df.index)  # Missing CpG filled

    @patch("backend.services.predictive_model_service.joblib.load")
    @patch("backend.services.predictive_model_service.pd.read_csv")
    def test_predict_biological_age(self, mock_read_csv, mock_joblib_load):
        # Mock data
        mock_model = MagicMock()
        mock_model.predict.return_value = [30.5, 40.2]
        mock_joblib_load.return_value = mock_model

        mock_read_csv.side_effect = [
            pd.DataFrame(index=["cg1", "cg2", "cg3"]),  # Mock cg_order
            pd.DataFrame({"mean": [0.7, 0.8, 0.9]}, index=["cg1", "cg2", "cg3"]),  # Mock cg means
        ]

        csv_df = pd.DataFrame(
            {
                "Sample1": [0.1, 0.2, 0.3],
                "Sample2": [0.4, 0.5, 0.6],
            },
            index=["cg1", "cg2", "cg3"],
        )

        # Call the function
        result = predict_biological_age("Blood inflammatory Clock 1", csv_df)

        # Assert the result
        self.assertIn("predictions", result)
        predictions = result["predictions"]

        # Adjust assertions based on the actual structure of predictions
        self.assertIn("Sample1", predictions)
        self.assertIn("Sample2", predictions)
        self.assertEqual(predictions["Sample1"]["PredictedAge"], 30.5)  # First prediction
        self.assertEqual(predictions["Sample2"]["PredictedAge"], 40.2)  # Second prediction

def test_calculate_percent_empty_inputs():
    """
    Test calculate_percent with empty inputs.
    """
    # Empty inputs
    clock_cpgs = []
    table_cpgs = []

    # Call the function
    result = calculate_percent(clock_cpgs, table_cpgs)

    # Assert the result is 0%
    assert result == 0

def test_calculate_percent_no_overlap():
    """
    Test calculate_percent with non-overlapping inputs.
    """
    # Non-overlapping inputs
    clock_cpgs = ["cg1", "cg2", "cg3"]
    table_cpgs = ["cg4", "cg5", "cg6"]

    # Call the function
    result = calculate_percent(clock_cpgs, table_cpgs)

    # Assert the result is 0%
    assert result == 0

def test_matching_cpgs():
    # Test case where some CpGs match
    clock_cpgs = ["cg000001", "cg000002", "cg000003"]
    table_cpgs = ["cg000001", "cg000002", "cg000004"]
    result = calculate_percent(clock_cpgs, table_cpgs)
    assert result == 66.66666666666666  # 2 out of 3 match

def test_no_matching_cpgs():
    # Test case where no CpGs match
    clock_cpgs = ["cg000001", "cg000002", "cg000003"]
    table_cpgs = ["cg000004", "cg000005", "cg000006"]
    result = calculate_percent(clock_cpgs, table_cpgs)
    assert result == 0.0  # No matches

def test_empty_clock_cpgs():
    # Test case where clock CpGs list is empty
    clock_cpgs = []
    table_cpgs = ["cg000001", "cg000002", "cg000003"]
    result = calculate_percent(clock_cpgs, table_cpgs)
    assert result == 0.0  # No CpGs in the clock

def test_empty_table_cpgs():
    # Test case where table CpGs list is empty
    clock_cpgs = ["cg000001", "cg000002", "cg000003"]
    table_cpgs = []
    result = calculate_percent(clock_cpgs, table_cpgs)
    assert result == 0.0  # No CpGs in the table

def test_case_sensitivity():
    # Test case where CpGs match but have different cases
    clock_cpgs = ["cg000001", "cg000002", "cg000003"]
    table_cpgs = ["CG000001", "CG000002", "CG000004"]
    result = calculate_percent(clock_cpgs, table_cpgs)
    assert result == 0.0 # 0 out of 3 match exactly

def test_duplicates_in_clock_cpgs():
    # Test case where clock CpGs list has duplicates
    clock_cpgs = ["cg000001", "cg000001", "cg000002", "cg000003"]
    table_cpgs = ["cg000001", "cg000002", "cg000004"]
    result = calculate_percent(clock_cpgs, table_cpgs)
    assert result == 66.66666666666666  # 2 unique CpGs out of 3 match

def test_duplicates_in_table_cpgs():
    # Test case where table CpGs list has duplicates
    clock_cpgs = ["cg000001", "cg000002", "cg000003"]
    table_cpgs = ["cg000001", "cg000001", "cg000002", "cg000004"]
    result = calculate_percent(clock_cpgs, table_cpgs)
    assert result == 66.66666666666666  # 2 out of 3 match

