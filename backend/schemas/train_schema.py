from pydantic import BaseModel, Field
from typing import Optional

# Bounds for the user-selectable train/evaluation split. Outside this range one of
# the two sets gets too small to be meaningful for the metrics we report.
MIN_TEST_SIZE = 0.1
MAX_TEST_SIZE = 0.5
DEFAULT_TEST_SIZE = 0.2

class TrainModelRequest(BaseModel):
    model_name: str
    model_params: str
    # Fraction of the dataset held back for evaluation (0.2 = the classic 80/20 split).
    test_size: float = Field(
        default=DEFAULT_TEST_SIZE, ge=MIN_TEST_SIZE, le=MAX_TEST_SIZE
    )

class CheckDFSRequest(BaseModel):
    betas_path: str
    metadata_path: str

class GeneCpGRequest(BaseModel):
    genes_path: str
    is_promoter_only: bool = False