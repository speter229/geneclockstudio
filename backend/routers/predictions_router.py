from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
import os
from backend.config import PROJECT_ROOT 
from backend.services.predictive_model_service import predict_biological_age
from backend.services.predictive_model_service import calculate_feature_coverage
from backend.schemas.predictions_schema import PredictRequest, IndexListRequest

router = APIRouter()
# Endpoint to predict biological age
@router.post("/predict/")
def predict(request: PredictRequest):
    try:
        file_path = os.path.join(PROJECT_ROOT, request.file_path)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=400, detail="File not found on the server.")

        df = pd.read_csv(file_path, index_col=0)

        result = predict_biological_age(request.model_name, df)

        return {"predictions": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint to calculate feature coverage
@router.post("/calculate_percent/")
def calculate_percent(request: IndexListRequest):
    try:
        # Extract the file path from the request
        file_path = os.path.join(PROJECT_ROOT, request.file_path)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=400, detail="File not found on the server.")

        # Read only the index (first column) of the CSV file
        df = pd.read_csv(file_path, usecols=[0], index_col=0)

        # Convert the index to a list
        index_list = df.index.tolist()

        # Call the processing function with the index list
        result = calculate_feature_coverage(index_list)

        # Return the result as a dictionary
        return {
            "inflammation_Hannum_ELASTICNET": result[0],
            "inflammation_AltumAge450k_ELASTICNET": result[1],
            "inflammation_computage_ELASTICNET": result[2],
            "inflammation_computage_XGBoost": result[3],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
