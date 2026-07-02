import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from backend.services.dataset_service import get_dataset_info

class TestDatasetService(unittest.TestCase):
    @patch("backend.services.dataset_service.pd.read_csv")
    def test_get_dataset_info_gse40279(self, mock_read_csv):
        # Mock data
        mock_df = pd.DataFrame(
            {
                "Sample1": [45, "Blood", "GEO1"],
                "Sample2": [50, "Blood", "GEO2"],
            },
            index=["age", "tissue", "geo_accession"],
        )
        mock_read_csv.return_value = mock_df

        # Call the function
        result = get_dataset_info("GSE40279")

        # Assert the result
        self.assertEqual(result["description"], (
            "The GSE40279 accession data is a widely used methylation data for model training.\n"
            "It contains 656 blood samples, measured with illumina450k (so each sample has about 480k features.)."
            "It is accessible from the GEO database, with this link: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE40279\n"
        ))
        self.assertEqual(result["metadata"], mock_df.iloc[:3, :20].to_dict())
        self.assertEqual(result["ages"], [45.0, 50.0])

    @patch("backend.services.dataset_service.pd.read_csv")
    def test_get_dataset_info_computage(self, mock_read_csv):
        # Mock data
        mock_df = pd.DataFrame(
            {
                "Sample1": [30, "Healthy"],
                "Sample2": [40, "Healthy"],
            },
            index=["Age", "HealthStatus"],
        )
        mock_read_csv.return_value = mock_df

        # Call the function
        result = get_dataset_info("Computage")

        # Assert the result
        self.assertEqual(result["description"], (
            "This is a public dataset from Hugging Face.\n"
            "Dataset detailed description and tutorial for usage: https://huggingface.co/datasets/computage/computage_bench \n"
            "The interesting part is that it contains disease information, so we could measure if certain diseases affect the biological age prediction.\n"
            "The data used for training (healthy samples) contains about 7,000 blood samples\n"
            "The data used for testing contains about 10,000 samples."
        ))
        self.assertEqual(result["metadata"], mock_df.iloc[:8, :20].to_dict())
        self.assertEqual(result["ages"], [30.0, 40.0])
    
    def test_get_dataset_info_invalid_dataset(self):
        # Call the function with an invalid dataset name
        with self.assertRaises(ValueError) as context:
            get_dataset_info("InvalidDataset")

        # Assert the exception message
        self.assertEqual(str(context.exception), "❌ Error processing dataset InvalidDataset: Dataset not found.")

    @patch("backend.services.dataset_service.pd.read_csv")
    def test_get_dataset_info_file_not_found(self, mock_read_csv):
        # Mock the file not found error
        mock_read_csv.side_effect = FileNotFoundError("File not found")

        # Call the function and assert the exception
        with self.assertRaises(ValueError) as context:
            get_dataset_info("GSE40279")

        self.assertIn("❌ Error processing dataset GSE40279", str(context.exception))

if __name__ == "__main__":
    unittest.main()