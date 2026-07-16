import datetime
import json
import pandas as pd
import numpy as np
from typing import Optional
from backend.services.train_preprocess import cg_selection, train_random_forest_model
from backend.services.train_preprocess import MethylationDataset
from backend.services.train_preprocess import prepocess_before_training
from sklearn.model_selection import train_test_split
from backend.services.train_preprocess import train_elasticnet_model
from backend.services.train_preprocess import train_xgboost_model
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.stats import pearsonr
import joblib
import uuid
import os
import torch
import logging
from backend.config import PROJECT_ROOT

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

model_registry_path = os.path.join(PROJECT_ROOT, "backend/saved_models/model_registry.json")

# Ensure the directory and file exist
if not os.path.exists(os.path.dirname(model_registry_path)):
    os.makedirs(os.path.dirname(model_registry_path))  # Create the directory if it doesn't exist

if not os.path.exists(model_registry_path):
    with open(model_registry_path, "w") as f:
        json.dump({}, f)  # Create an empty JSON file

def save_model_for_user(model,features_order,  username, model_name):
    """
    Saves the trained model for a specific user with a descriptive filename.

    Args:
        model: The trained model object.
        username (str): The username of the model owner.
        model_name (str): The name of the model (e.g., ElasticNet, XGBoost, RandomForest).

    Returns:
        dict: A dictionary containing the model ID , filename and download path.
    """
    model_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    model_filename = f"model_and_features_{timestamp}_{model_name}_{model_id}.joblib"
    user_dir = os.path.join(PROJECT_ROOT, "backend", "saved_models", username)
    os.makedirs(user_dir, exist_ok=True)  # Ensure the directory exists
    save_path = os.path.join(user_dir, model_filename)
    joblib.dump((model,features_order), save_path)
    return {
        "model_id": model_id,
        "model_filename": model_filename,
        "download_path": f"/train/download_model/{model_id}"
    }

def register_model_owner(model_id: str, username: str, model_name: str):
    """
    Registers a model's ownership to a specific user.

    Args:
        model_id (str): The unique ID of the model.
        username (str): The username of the model owner.
    """
    # Load the existing registry or initialize an empty one
    if os.path.exists(model_registry_path):
        with open(model_registry_path, "r") as f:
            try:
                registry = json.load(f)
            except json.JSONDecodeError:
                registry = {}
    else:
        registry = {}

    # Add the model ownership
    registry[model_id] = {"username": username, "model_filename": model_name}
    # Save the updated registry
    with open(model_registry_path, "w") as f:
        json.dump(registry, f, indent=4)

def validate_model_ownership(model_id: str, username: str) -> bool:
    """
    Validates if a user owns a specific model.

    Args:
        model_id (str): The unique ID of the model.
        username (str): The username of the user.

    Returns:
        bool: True if the user owns the model, False otherwise.
    """
    if os.path.exists(model_registry_path):
        with open(model_registry_path, "r") as f:
            try:
                registry = json.load(f)
            except json.JSONDecodeError:
                return False

        # Check if the model exists and is owned by the user
        return registry.get(model_id, {}).get("username") == username

    return False


def process_training_job(
    df_betas: pd.DataFrame,
    df_meta: pd.DataFrame,
    model_name: str,
    params: dict,
    username: str = None
) -> dict:
    """
    Processes the training job with the given features. Returns model features, predictions and evaluation metrics.
    Args:
        df_betas (pd.DataFrame): DataFrame containing the beta values for CpG sites.
        df_meta (pd.DataFrame): DataFrame containing the metadata for the samples.
        model_name (str): The name of the model to be trained (e.g., "ElasticNet", "XGBoost", "RandomForest").
        params (dict): Dictionary containing hyperparameters for the model.
        username (str, optional): The username of the model owner. Defaults to None.
    Returns:
        dict: A dictionary containing the features order, predictions, and evaluation metrics.
    """
    try:
        logging.info("Starting process_training_job.")
        logging.info(f"df_betas shape: {df_betas.shape}")
        logging.info(f"df_meta shape: {df_meta.shape}")
        
        if df_betas.shape[1] < 20 :
            raise ValueError("Too few samples in the training data after filtering out low quality samples. At least 20 samples are required.")
        # Check if the training data has too few rows
        if df_betas.shape[0] < 20:
            raise ValueError("Too few cg sites after filtering out low quality CpG sites. At least 20 cg sites are required.")
        
        features_order = df_betas.index.tolist()
        
        # Create dataset
        logging.info("Creating MethylationDataset.")
        transcriptomic_dataset = MethylationDataset(df_meta, df_betas)

        # Train-test split
        logging.info("Splitting data into train and test sets.")
        train_data, test_data = train_test_split(transcriptomic_dataset, test_size=0.2, random_state=42)
        logging.info(f"Train data size: {len(train_data)}")
        logging.info(f"Test data size: {len(test_data)}")

        # Prepare training and testing data
        X_train, y_train = [], []
        for features, target in train_data:
            X_train.append(features)
            y_train.append(target)

        X_test, y_test = [], []
        for features, target in test_data:
            X_test.append(features)
            y_test.append(target)

        # Log the sizes and sample data
        logging.info(f"X_train size: {len(X_train)}, y_train size: {len(y_train)}")
        logging.info(f"X_test size: {len(X_test)}, y_test size: {len(y_test)}")
        logging.info(f"First 3 X_train samples: {X_train[:3]}, First 3 y_train samples: {y_train[:3]}")

        # Train the model
        elasticnet_selected_cpgs = None
        chosen_alpha = None
        chosen_l1_ratio = None
        if model_name == "ElasticNet":
            logging.info("Training ElasticNet model.")
            alpha = params.get("alpha", 0.1)
            l1_ratio = params.get("l1_ratio", 0.5)
            max_iter = params.get("max_iter", 1000)
            cv = params.get("cv", 5)
            auto_optimize = params.get("auto_optimize", False)

            # Convert lists to numpy arrays to ensure consistent dtypes
            X_train_arr = np.array(X_train, dtype=float)
            y_train_arr = np.array(y_train, dtype=float)
            logging.info(f"X_train_arr shape: {X_train_arr.shape}, y_train_arr shape: {y_train_arr.shape}")

            model = train_elasticnet_model(
                X_train=X_train_arr,
                y_train=y_train_arr,
                cv=cv,
                alpha=alpha,
                l1_ratio=l1_ratio,
                max_iter=max_iter,
                auto_optimize=auto_optimize,
            )
            logging.info("ElasticNet model trained successfully.")

            # Surface the (auto-optimized or fixed) hyperparameters and the
            # nonzero-coefficient CpG sites so the user can inspect/download them.
            elasticnet_step = model.named_steps["elasticnet"]
            chosen_alpha = float(getattr(elasticnet_step, "alpha_", alpha))
            chosen_l1_ratio = float(getattr(elasticnet_step, "l1_ratio_", l1_ratio))
            coefs = np.asarray(elasticnet_step.coef_, dtype=float)
            nonzero_mask = coefs != 0
            elasticnet_selected_cpgs = [
                {"cpg": features_order[i], "coefficient": float(coefs[i])}
                for i in np.where(nonzero_mask)[0]
            ]
            logging.info(f"ElasticNet selected {len(elasticnet_selected_cpgs)} nonzero-coefficient CpG sites out of {len(features_order)}.")

        elif model_name == "XGBoost":
            logging.info("Training XGBoost model.")
            learning_rate = params.get("learning_rate", 0.1)
            max_depth = params.get("max_depth", 3)
            n_estimators = params.get("n_estimators", 100)
            subsample = params.get("subsample", 1.0)

            X_train_arr = np.array(X_train, dtype=float)
            y_train_arr = np.array(y_train, dtype=float)

            model = train_xgboost_model(
                X_train=X_train_arr,
                y_train=y_train_arr,
                learning_rate=learning_rate,
                max_depth=max_depth,
                n_estimators=n_estimators,
                subsample=subsample
            )
            logging.info("XGBoost model trained successfully.")

        elif model_name == "RandomForest":
            logging.info("Training RandomForest model.")
            n_estimators = params.get("n_estimators", 100)
            max_depth = params.get("max_depth", 10)
            min_samples_split = params.get("min_samples_split", 2)
            min_samples_leaf = params.get("min_samples_leaf", 2)
            max_features = params.get("max_features", "sqrt")
            bootstrap = params.get("bootstrap", True)

            X_train_arr = np.array(X_train, dtype=float)
            y_train_arr = np.array(y_train, dtype=float)

            model = train_random_forest_model(
                X_train=X_train_arr,
                y_train=y_train_arr,
                n_estimators=n_estimators,
                max_depth=max_depth,
                min_samples_split=min_samples_split,
                min_samples_leaf=min_samples_leaf,
                max_features=max_features,
                bootstrap=bootstrap,
                random_state=42
            )
            logging.info("RandomForest model trained successfully.")

        # Evaluate the model
        logging.info("Evaluating the model.")
        # Ensure X_test and y_test are numpy arrays of float
        X_test_arr = np.array(X_test, dtype=float)
        y_test_arr = np.array(y_test, dtype=float)

        y_pred = model.predict(X_test_arr)
        y_pred = np.array(y_pred, dtype=float)

        # Identify finite predictions and targets
        finite_mask = np.isfinite(y_pred) & np.isfinite(y_test_arr)
        nonfinite_count = np.sum(~finite_mask)
        if nonfinite_count > 0:
            logging.warning(f"Found {nonfinite_count} non-finite predictions or targets; they will be excluded from metric calculations and set to null in the response.")

        # Compute metrics on finite pairs only
        if np.sum(finite_mask) > 0:
            try:
                mae = mean_absolute_error(y_test_arr[finite_mask], y_pred[finite_mask])
            except Exception as _:
                mae = None

            try:
                if np.sum(finite_mask) > 1:
                    r_value, _ = pearsonr(y_test_arr[finite_mask], y_pred[finite_mask])
                else:
                    r_value = None
            except Exception:
                r_value = None
        else:
            mae = None
            r_value = None

        logging.info(f"MAE on test set: {mae}")
        logging.info(f"R value on test set: {r_value}")

        # Save the model
        logging.info("Saving the model.")
        model_data_json = save_model_for_user(model, features_order, username, model_name)
        register_model_owner(model_data_json["model_id"], username, model_data_json["model_filename"])

        # Return the results
        # Convert predictions and tests to JSON-safe lists (replace non-finite with None)
        y_test_list = [float(x) if np.isfinite(x) else None for x in np.array(y_test, dtype=float).tolist()]
        y_pred_list = [float(x) if np.isfinite(x) else None for x in np.array(y_pred, dtype=float).tolist()]

        # For frontend compatibility, return numeric fallbacks when metrics are missing
        mae_value = float(mae) if mae is not None and np.isfinite(mae) else -1.0
        r_value_value = float(r_value) if r_value is not None and np.isfinite(r_value) else -1.0

        result = model_data_json | {
            "features_order": features_order,
            "y_test": y_test_list,
            "y_pred": y_pred_list,
            "mae": mae_value,
            "r_value": r_value_value,
            "selected_cpgs": elasticnet_selected_cpgs,
            "chosen_alpha": chosen_alpha,
            "chosen_l1_ratio": chosen_l1_ratio,
            "message": "Training job processed successfully."
        }
        logging.info("Training job completed successfully.")
        return result

    except Exception as e:
        logging.error(f"An error occurred in process_training_job: {str(e)}", exc_info=True)
        raise