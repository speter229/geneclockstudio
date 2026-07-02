from pydantic import BaseModel

class PredictRequest(BaseModel):
    model_name: str
    file_path: str

class IndexListRequest(BaseModel):
    file_path: str
