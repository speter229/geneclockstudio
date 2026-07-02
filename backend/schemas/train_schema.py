from pydantic import BaseModel
from typing import Optional

class TrainModelRequest(BaseModel):
    model_name: str
    model_params: str

class CheckDFSRequest(BaseModel):
    betas_path: str
    metadata_path: str

class GeneCpGRequest(BaseModel):
    genes_path: str
    is_promoter_only: bool = False