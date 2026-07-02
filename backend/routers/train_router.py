import pandas as pd
import json
import os
import time
import logging
import scipy
from fastapi import APIRouter, Form, HTTPException, Depends
from typing import Optional
from backend.config import PROJECT_ROOT  # Import PROJECT_ROOT
from backend.services.train_service import process_training_job
from fastapi.responses import FileResponse, JSONResponse
import numpy as np
from backend.services.authenticator_service import get_current_user
from pydantic import BaseModel
from backend.services.train_preprocess import check_dataframes
from backend.schemas.train_schema import TrainModelRequest, CheckDFSRequest, GeneCpGRequest
from backend.services.train_preprocess import cg_selection
from backend.services.train_preprocess import prepocess_before_training
from backend.services.train_preprocess import validate_gene_dataframe
from scipy.stats import pearsonr

router = APIRouter()

model_registry_path = os.path.join(PROJECT_ROOT, "backend/saved_models/model_registry.json")  # Updated path


# Global cache with timestamps
dataframe_cache = {}
cache_expiry_time = 4*3600  # 1h in seconds

# Function to check if the users's data in cache is expired, and delete if so
def cleanup_cache_in_time():
    current_time = time.time()
    keys_to_remove = [
        user for user, data in dataframe_cache.items()
        if current_time - data["timestamp"] > cache_expiry_time
    ]
    for user in keys_to_remove:
        del dataframe_cache[user]

# Endpoint to validate the content of the uploaded meta and beta dataframes
@router.post("/check_dfs/")
def check_dfs(request: CheckDFSRequest, current_user: str = Depends(get_current_user)):
    try:
        # Perform validation and caching
        betas_path = os.path.join(PROJECT_ROOT, request.betas_path)
        metadata_path = os.path.join(PROJECT_ROOT, request.metadata_path)

        df_betas = pd.read_csv(betas_path, index_col=0)
        df_meta = pd.read_csv(metadata_path, index_col=0)

        # Store dataframes with a timestamp
        dataframe_cache[current_user] = {
            "df_betas": df_betas,
            "df_meta": df_meta,
            "timestamp": time.time()
        }

        # Cleanup old cache entries
        cleanup_cache_in_time()
        
        return( check_dataframes(df_betas, df_meta))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gene_cpgs_request/")
def gene_cpgs_request(request: GeneCpGRequest, current_user: str = Depends(get_current_user)):
    try:
        # Make path to file
        gene_filter_path = os.path.join(PROJECT_ROOT, request.genes_path)
        # Check if the file exists
        if not os.path.exists(gene_filter_path):
            raise HTTPException(status_code=400, detail="Gene filter saving to server failed.")
        
        # Read the gene file into a dataframe
        df_genes = pd.read_csv(gene_filter_path)
        
        # Validate the gene dataframe
        try:
            validate_gene_dataframe(df_genes)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Process the gene dataframe
        gene_cpg_pairs = cg_selection(UPLOADED_GENE=df_genes, promoter_only=request.is_promoter_only)
        cg_selection_list = [cpg for _, cpg in gene_cpg_pairs]
        dataframe_cache[current_user]["df_betas"] = dataframe_cache[current_user]["df_betas"][
            dataframe_cache[current_user]["df_betas"].index.isin(cg_selection_list)
        ]
        dataframe_cache[current_user]["df_betas"], dataframe_cache[current_user]["df_meta"] = prepocess_before_training(
            dataframe_cache[current_user]["df_betas"], dataframe_cache[current_user]["df_meta"]
        )

        cg_selection_list = dataframe_cache[current_user]["df_betas"].index.tolist()

        # Extract the 'age' row from the metadata table
        if 'age' in dataframe_cache[current_user]["df_meta"].index.str.lower():
            age_row_index = dataframe_cache[current_user]["df_meta"].index.str.lower().get_loc('age')
            ages = dataframe_cache[current_user]["df_meta"].iloc[age_row_index].astype(float).tolist()
        else:
            raise HTTPException(status_code=400, detail="'Age' row not found in metadata table.")
        
        # Calculate correlations for each CpG site
        correlations = [
            pearsonr(list(dataframe_cache[current_user]["df_betas"].iloc[i]), ages)[0]
            for i in range(len(dataframe_cache[current_user]["df_betas"]))
        ]

        # Add correlations to gene_cpg_pairs
        gene_cpg_pairs_with_corr = [
            (gene, cpg, correlations[dataframe_cache[current_user]["df_betas"].index.get_loc(cpg)])
            for gene, cpg in gene_cpg_pairs
            if cpg in cg_selection_list
        ]

        # Group by gene and calculate the average correlation
        gene_avg_correlations = {}
        for gene, cpg, corr in gene_cpg_pairs_with_corr:
            if gene not in gene_avg_correlations:
                gene_avg_correlations[gene] = []
            gene_avg_correlations[gene].append(corr)
        
        # Calculate the average correlation for each gene
        gene_avg_correlations = {
            gene: sum(corrs) / len(corrs) for gene, corrs in gene_avg_correlations.items()
        }

        # Map each CpG site to its gene's average correlation
        cpg_to_gene_avg_corr = {
            cpg: gene_avg_correlations[gene]
            for gene, cpg, _ in gene_cpg_pairs_with_corr
        }

        # Prepare the final result
        result_correlation = [
            {"cpg": cpg, "gene_avg_correlation": cpg_to_gene_avg_corr[cpg]}
            for cpg in cg_selection_list
        ]

        cg_list = [item["cpg"] for item in result_correlation]
        gene_avg_correlation_list = [item["gene_avg_correlation"] for item in result_correlation]

        return {
            "cg_selection_list": cg_list,
            "gene_avg_correlation_list": gene_avg_correlation_list
        }

    except HTTPException as e:
        # Re-raise HTTP exceptions to ensure proper status codes
        raise e
    except Exception as e:
        # Log unexpected errors and return a JSON response
        logging.error(f"Unexpected error in /gene_cpgs_request/: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while processing the request.")
    finally:
        # Cleanup the gene filter file
        if os.path.exists(gene_filter_path):
            try:
                os.remove(gene_filter_path)
                logging.info(f"Successfully removed gene filter file: {gene_filter_path}")
            except Exception as e:
                logging.error(f"Error removing gene filter file: {gene_filter_path}. Error: {e}")

# Endpoint to train the model with the given data and hyperparameters
@router.post("/train_model/")
def train_model(request: TrainModelRequest, current_user: str = Depends(get_current_user)):
    try:
        logging.info(f"Received request: {request}")
        logging.info(f"Current user: {current_user}")


        # Read the files into DataFrames
        df_betas = dataframe_cache[current_user]["df_betas"]
        df_meta = dataframe_cache[current_user]["df_meta"]

        
        # Parse the model parameters from JSON
        params = json.loads(request.model_params)

        # Call the process_training_job function with the username
        result = process_training_job(
            df_betas, df_meta, request.model_name, params, username=current_user
        )

        # Sanitize result to ensure JSON serializability (replace NaN/inf with None and convert numpy types)
        def sanitize(obj):
            # Primitive types
            if obj is None:
                return None
            if isinstance(obj, (str, bool)):
                return obj
            # Numbers: handle numpy scalars and floats
            if isinstance(obj, (int, float)):
                try:
                    if isinstance(obj, float) and not np.isfinite(obj):
                        return None
                except Exception:
                    return None
                # Ensure Python native types
                return obj
            # numpy scalar
            try:
                import numpy as _np
                if _np and isinstance(obj, _np.generic):
                    val = obj.item()
                    if isinstance(val, float) and not _np.isfinite(val):
                        return None
                    return val
            except Exception:
                pass
            # Lists/tuples
            if isinstance(obj, (list, tuple)):
                return [sanitize(x) for x in obj]
            # Dicts
            if isinstance(obj, dict):
                return {str(k): sanitize(v) for k, v in obj.items()}
            # Fallback: convert to string
            try:
                return str(obj)
            except Exception:
                return None

        safe_result = sanitize(result)
        return JSONResponse(content=safe_result)
    except ValueError as e:
        # Include the specific error message in the response
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logging.error(f"Error in /train/train_model/: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing the training job.")

# Endpoint to download the users trained model
@router.get("/download_model/{model_id}")
def download_model(model_id: str, current_user: str = Depends(get_current_user)):
    try:
        # Log the model ID and user
        logging.info(f"Download request for model_id: {model_id} by user: {current_user}")
        # Check if the model registry exists
        if not os.path.exists(model_registry_path):
            raise HTTPException(status_code=404, detail="Model registry not found.")

        # Load the model registry
        with open(model_registry_path, "r") as f:
            registry = json.load(f)

        # Check if the model_id exists in the registry
        if model_id not in registry:
            raise HTTPException(status_code=404, detail="Model not found in the registry.")

        # Check if the current user owns the model
        model_data = registry[model_id]
        if model_data.get("username") != current_user:
            raise HTTPException(status_code=403, detail="You do not have access to this model.")

        # Get the filename from the registry
        model_filename = model_data.get("model_filename")
        model_path = os.path.join(PROJECT_ROOT, "backend/saved_models", current_user, model_filename)

        if not os.path.exists(model_path):
            raise HTTPException(status_code=404, detail="Model file not found on the server.")

        # Log the file path
        logging.info(f"Serving model file: {model_path}")

        # Return the file as a response
        return FileResponse(model_path, filename=model_filename, media_type="application/octet-stream")

    except Exception as e:
        logging.error(f"Error in download_model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint to list all models for the authenticated user
@router.get("/list/")
def list_user_models(current_user: str = Depends(get_current_user)):
    try:
        # Check if the model registry exists
        if not os.path.exists(model_registry_path):
            return {"models": []}  # Return an empty list if no models are registered

        # Load the model registry
        with open(model_registry_path, "r") as f:
            registry = json.load(f)

        # Filter models belonging to the current user
        user_models = [
            {
                "model_id": model_id,
                "model_filename": data.get("model_filename"),  # Include the actual filename
                "download_link": f"/train/download_model/{data.get('model_filename')}"  # Use the filename for the download link
            }
            for model_id, data in registry.items()
            if data.get("username") == current_user
        ]

        return {"models": user_models}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Endpoint to delete a model for the authenticated user
@router.delete("/delete_model/{model_id}")
def delete_model(model_id: str, current_user: str = Depends(get_current_user)):
    """
    Deletes a model for the authenticated user.
    """
    try:
        # Log the model ID and user
        logging.info(f"Delete request for model_id: {model_id} by user: {current_user}")

        # Check if the model registry exists
        if not os.path.exists(model_registry_path):
            raise HTTPException(status_code=404, detail="Model registry not found.")
        
        # Load the model registry
        with open(model_registry_path, "r") as f:
            registry = json.load(f)

        # Check if the model_id exists in the registry
        if model_id not in registry:
            raise HTTPException(status_code=404, detail="Model not found in the registry.")

        # Check if the current user owns the model
        model_data = registry[model_id]
        if model_data.get("username") != current_user:
            raise HTTPException(status_code=403, detail="You do not have access to this model.")

        # Delete the model file
        model_file_path = os.path.join(PROJECT_ROOT, "backend/saved_models", current_user ,model_data["model_filename"])
        if os.path.exists(model_file_path):
            os.remove(model_file_path)

        # Remove the model from the registry
        del registry[model_id]
        with open(model_registry_path, "w") as f:
            json.dump(registry, f)

        logging.info(f"Model {model_id} deleted successfully.")
        return {"message": "Model deleted successfully."}

    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Unexpected error while deleting model: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while deleting the model.")