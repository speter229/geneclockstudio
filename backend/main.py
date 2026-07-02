import sys
import os
import json
import uvicorn
from fastapi import FastAPI
from backend.routers import dataset_router 
from backend.routers import predictions_router
from backend.routers import train_router
from backend.routers import authenticator_router
from backend.config import PROJECT_ROOT, TEMP_PATH 
from backend.services.temp_service import cleanup_whole_temp_folder  

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

os.makedirs(TEMP_PATH, exist_ok=True) # Ensure the temp directory exists
cleanup_whole_temp_folder()  #Delete leftover files from previous runs

def ensure_saved_models_directory():
    """
    Ensures that the 'saved_models' directory and 'model_registry.json' file exist.
    If the directory or file does not exist, they will be created.
    """
    saved_models_path = os.path.join(PROJECT_ROOT, "backend/saved_models")
    model_registry_path = os.path.join(saved_models_path, "model_registry.json")

    # Ensure the 'saved_models' directory exists
    if not os.path.exists(saved_models_path):
        os.makedirs(saved_models_path)

    # Ensure the 'model_registry.json' file exists
    if not os.path.exists(model_registry_path):
        with open(model_registry_path, "w") as f:
            json.dump({}, f)  # Create an empty JSON file

ensure_saved_models_directory()

app = FastAPI()

#setup the routers
app.include_router(dataset_router.router, prefix="/datasets", tags=["Datasets"])
app.include_router(predictions_router.router, prefix="/predictions", tags=["Predictions"])
app.include_router(train_router.router, prefix="/train", tags=["Train"])
app.include_router(authenticator_router.router, prefix="/authenticate", tags=["Authentication"])

if __name__ == "__main__":
    # Construct SSL paths using PROJECT_ROOT
    ssl_certfile = os.path.join(PROJECT_ROOT, "backend/https_codes/server.crt")
    ssl_keyfile = os.path.join(PROJECT_ROOT, "backend/https_codes/server.key")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",   #FOR SERVER DEPLOYMENT
        port=8500,        #FOR BOTH SERVER DEPLOYMENT AND LOCAL TESTING
        #host="127.0.0.1",  # FOR LOCAL TESTING
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        reload=True,
        limit_concurrency=100,  # Maximum number of concurrent requests
        limit_max_requests=1000  # Maximum number of requests a worker can handle before restarting
    )
