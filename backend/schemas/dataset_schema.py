from pydantic import BaseModel
from typing import Dict, List, Optional

class DatasetInfoWithAge(BaseModel):
    description: str
    metadata: Dict
    ages: List[float]
    trained_clocks: str
    study_description_1: Optional[str] = None
    study_description_2: Optional[str] = None
    study_description_3: Optional[str] = None
    study_scatterplot_1: Optional[str] = None
    study_scatterplot_2: Optional[str] = None
    study_boxplot_1: Optional[str] = None