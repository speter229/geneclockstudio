import os
from backend.config import PROJECT_ROOT

# Registry of bundled example beta-value/metadata pairs that users can load
# instead of uploading their own data on the "Train Your Own Aging Clock" page.
# Add new entries here to expose more built-in datasets in the UI.
EXAMPLE_TRAINING_DATASETS = {
    "demo_blood_sample": {
        "label": "Demo blood methylation sample (656 samples, 1281 CpGs)",
        "description": (
            "A small blood methylation dataset with a matching 'age' metadata row, "
            "bundled so you can try out the training pipeline without uploading your own data."
        ),
        "beta_path": os.path.join(PROJECT_ROOT, "backend/data/example_datasets/demo_blood_beta.csv"),
        "meta_path": os.path.join(PROJECT_ROOT, "backend/data/example_datasets/demo_blood_meta.csv"),
    },
}


def list_example_training_datasets():
    """Returns the id -> {label, description} mapping for UI display."""
    return {
        dataset_id: {"label": info["label"], "description": info["description"]}
        for dataset_id, info in EXAMPLE_TRAINING_DATASETS.items()
    }


def get_example_training_dataset_paths(dataset_id: str):
    """Returns (beta_path, meta_path) for a bundled example dataset id."""
    if dataset_id not in EXAMPLE_TRAINING_DATASETS:
        raise ValueError(f"Unknown example dataset: {dataset_id}")
    info = EXAMPLE_TRAINING_DATASETS[dataset_id]
    return info["beta_path"], info["meta_path"]
