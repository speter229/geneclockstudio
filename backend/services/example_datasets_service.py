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
    "compute_age_training_subset_1": {
        "label": "Compute Age Training Subset 1 (528 samples, 225,112 CpGs)",
        "description": (
            "Fixed benchmark methylation subset with 528 samples and 225,112 CpG sites, "
            "including Age and other metadata rows (~830 MB beta table)."
        ),
        "beta_path": os.path.join(PROJECT_ROOT, "backend/data/example_datasets/compute_age_training_subset_1_beta.csv"),
        "meta_path": os.path.join(PROJECT_ROOT, "backend/data/example_datasets/compute_age_training_subset_1_meta.csv"),
    },
    "compute_age_training_subset_2": {
        "label": "Compute Age Training Subset 2 (132 samples, 900,449 CpGs)",
        "description": (
            "Fixed benchmark methylation subset with 132 samples and 900,449 CpG sites, "
            "including Age and other metadata rows (~840 MB beta table)."
        ),
        "beta_path": os.path.join(PROJECT_ROOT, "backend/data/example_datasets/compute_age_training_subset_2_beta.csv"),
        "meta_path": os.path.join(PROJECT_ROOT, "backend/data/example_datasets/compute_age_training_subset_2_meta.csv"),
    },
    "compute_age_training_subset_3": {
        "label": "Compute Age Training Subset 3 (1320 samples, 225,112 CpGs)",
        "description": (
            "Fixed benchmark methylation subset with 1320 samples and 225,112 CpG sites, "
            "including Age and other metadata rows (~2 GB beta table). Loading and training "
            "on this dataset will take noticeably longer than the smaller subsets."
        ),
        "beta_path": os.path.join(PROJECT_ROOT, "backend/data/example_datasets/compute_age_training_subset_3_beta.csv"),
        "meta_path": os.path.join(PROJECT_ROOT, "backend/data/example_datasets/compute_age_training_subset_3_meta.csv"),
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
