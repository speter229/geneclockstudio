from fastapi import APIRouter, HTTPException
from backend.services.dataset_service import get_dataset_info
from backend.schemas.dataset_schema import DatasetInfoWithAge

router = APIRouter()

# Endpoint to get dataset information by name
@router.get("/{dataset_name}", response_model=DatasetInfoWithAge)
def get_dataset(dataset_name: str):
    try:
        dataset_info = get_dataset_info(dataset_name)  # calls service
        return dataset_info  # returns validated schema
    except ValueError as e:
        # Raise 404 if the dataset is not found
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Raise 500 for other errors (e.g., schema validation issues)
        raise HTTPException(status_code=500, detail=str(e))
