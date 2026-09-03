import logging

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from backend.services.authenticator_service import get_current_user
from backend.services.path_guard import resolve_user_data_path
from backend.services.rate_limit import RateLimiter
from backend.services.predictive_model_service import predict_biological_age
from backend.services.predictive_model_service import calculate_feature_coverage
from backend.schemas.predictions_schema import PredictRequest, IndexListRequest

router = APIRouter()

# Both endpoints below are weak oracles about the clocks' secret CpG lists, so both
# are rate limited per user. Legitimate use is a handful of calls per loaded dataset;
# mapping out a clock by probing would need orders of magnitude more.
# See backend/services/rate_limit.py.
COVERAGE_MAX_CALLS = 60
COVERAGE_WINDOW_SECONDS = 3600
coverage_limiter = RateLimiter("coverage", COVERAGE_MAX_CALLS, COVERAGE_WINDOW_SECONDS)

# A prediction only changes when a submitted CpG is one the clock actually uses, so
# repeated calls over hand-crafted files leak membership one site at a time.
PREDICT_MAX_CALLS = 120
PREDICT_WINDOW_SECONDS = 3600
predict_limiter = RateLimiter("predict", PREDICT_MAX_CALLS, PREDICT_WINDOW_SECONDS)


def enforce_coverage_rate_limit(username: str):
    """Raises 429 if the user exceeded COVERAGE_MAX_CALLS within the time window."""
    coverage_limiter.check(username)


def enforce_predict_rate_limit(username: str):
    """Raises 429 if the user exceeded PREDICT_MAX_CALLS within the time window."""
    predict_limiter.check(username)


# Endpoint to predict biological age
@router.post("/predict/")
def predict(request: PredictRequest, current_user: str = Depends(get_current_user)):
    try:
        enforce_predict_rate_limit(current_user)

        file_path = resolve_user_data_path(request.file_path)

        df = pd.read_csv(file_path, index_col=0)

        result = predict_biological_age(request.model_name, df)

        return {"predictions": result}
    except HTTPException:
        raise
    except Exception as e:
        # Do not echo internal exception text to the client: messages from pandas or
        # the model pipeline can contain CpG identifiers from the clock's feature list.
        logging.exception("Error in /predictions/predict/ for user %s", current_user)
        raise HTTPException(status_code=500, detail="Prediction failed.")

# Endpoint to calculate feature coverage
@router.post("/calculate_percent/")
def calculate_percent(request: IndexListRequest, current_user: str = Depends(get_current_user)):
    try:
        enforce_coverage_rate_limit(current_user)

        # Extract the file path from the request
        file_path = resolve_user_data_path(request.file_path)

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
    except HTTPException:
        raise
    except Exception as e:
        # As above: the error text can name protected CpG sites, so keep it server-side.
        logging.exception("Error in /predictions/calculate_percent/ for user %s", current_user)
        raise HTTPException(status_code=500, detail="Coverage calculation failed.")
