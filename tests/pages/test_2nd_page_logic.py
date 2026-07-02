import pytest
import pandas as pd
from frontend.utils import extract_age_row

def test_extract_age_row_success():
    """
    Test extracting the 'age' row successfully.
    """
    meta_df = pd.DataFrame(
        {
            "Sample1": [30, 0.5],
            "Sample2": [40, 0.8],
        },
        index=["Age", "Other"]
    )
    age_row = extract_age_row(meta_df)
    assert age_row.equals(pd.Series([30.0, 40.0], index=["Sample1", "Sample2"]))


def test_extract_age_row_missing():
    """
    Test extracting the 'age' row when it is missing.
    """
    meta_df = pd.DataFrame(
        {
            "Sample1": [0.5],
            "Sample2": [0.8],
        },
        index=["Other"]
    )
    with pytest.raises(ValueError, match="'Age' row not found."):
        extract_age_row(meta_df)


def test_extract_age_row_with_nan():
    """
    Test extracting the 'age' row when it contains NaN values.
    """
    meta_df = pd.DataFrame(
        {
            "Sample1": [30, 0.5],
            "Sample2": [None, 0.8],
        },
        index=["Age", "Other"]
    )
    with pytest.raises(ValueError, match="The 'Age' row contains missing values or NaNs."):
        extract_age_row(meta_df)