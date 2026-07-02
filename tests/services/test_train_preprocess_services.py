import pytest
import pandas as pd
import numpy as np
from backend.services.train_preprocess import (
    cg_selection,
    prepocess_before_training,
    train_elasticnet_model,
    train_xgboost_model,
    train_random_forest_model,
)

def test_prepocess_before_training():
    # Mock data
    df_betas = pd.DataFrame({
        "Sample1": [0.1, 0.2, np.nan],
        "Sample2": [0.3, np.nan, 0.5],
        "Sample3": [np.nan, 0.6, 0.7]
    })
    df_meta = pd.DataFrame({
        "Sample1": [45],
        "Sample2": [50],
        "Sample3": [55]
    }, index=["age"])

    # Call the function
    processed_betas, processed_meta = prepocess_before_training(df_betas, df_meta)

    # Assert the results
    assert processed_betas.isnull().sum().sum() == 0  # No missing values
    assert processed_betas.shape[1] == processed_meta.shape[1]  # Same shape

def test_prepocess_before_training_no_missing_values():
    """
    Test prepocess_before_training with DataFrames that have no missing values.
    """
    # Mock data with no missing values
    df_betas = pd.DataFrame({
        "Sample1": [0.1, 0.2, 0.3],
        "Sample2": [0.4, 0.5, 0.6],
        "Sample3": [0.7, 0.8, 0.9]
    })
    df_meta = pd.DataFrame({
        "Sample1": [45],
        "Sample2": [50],
        "Sample3": [55]
    }, index=["age"])

    # Call the function
    processed_betas, processed_meta = prepocess_before_training(df_betas, df_meta)

    # Assert the results
    pd.testing.assert_frame_equal(processed_betas, df_betas)  # No changes to df_betas
    pd.testing.assert_frame_equal(processed_meta, df_meta)    # No changes to df_meta

def test_cg_selection():
    # Mock data
    uploaded_gene = pd.DataFrame({"Gene_ID": ["Gene1", "Gene2"]})
    promoter_only = True

    # Mock probe table
    probe_table = pd.DataFrame({
        "UCSC_RefGene_Name": ["Gene1;Gene3", "Gene2", "Gene4"],
        "UCSC_RefGene_Group": ["TSS1500", "Body", "TSS200"]
    })
    probe_table.index = ["cg1", "cg2", "cg3"]
    
    # Call the function
    result = cg_selection(uploaded_gene, promoter_only)

    # Assert the result
    assert result == []


def test_train_elasticnet_model():
    # Mock data
    X_train = np.random.rand(100, 10)
    y_train = np.random.rand(100)

    # Call the function
    model = train_elasticnet_model(X_train, y_train, alpha=0.1, l1_ratio=0.5, max_iter=1000)

    # Assert the model is trained
    assert model is not None
    assert hasattr(model, "coef_")


def test_train_xgboost_model():
    # Mock data
    X_train = np.random.rand(100, 10)
    y_train = np.random.rand(100)

    # Call the function
    model = train_xgboost_model(X_train, y_train, learning_rate=0.1, max_depth=3, n_estimators=100)

    # Assert the model is trained
    assert model is not None
    assert hasattr(model, "feature_importances_")

def test_train_random_forest_model():
    # Mock data
    X_train = np.random.rand(100, 10)
    y_train = np.random.rand(100)

    # Call the function
    model = train_random_forest_model(X_train, y_train, n_estimators=100, max_depth=10)

    # Assert the model is trained
    assert model is not None
    assert hasattr(model, "feature_importances_")

