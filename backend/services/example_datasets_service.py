import os
import shutil
from backend.config import PROJECT_ROOT
from backend.services.secure_features_service import materialize_protected_file

# Registry of bundled example beta-value/metadata pairs that users can load
# instead of uploading their own data on the "Train your own gene set-specific aging clock" page.
# Add new entries here to expose more built-in datasets in the UI.
EXAMPLE_TRAINING_DATASETS = {
    "demo_blood_sample": {
        "label": "Demo blood methylation sample (656 samples, 21 CpGs)",
        "description": (
            "A small blood methylation dataset with a matching 'age' metadata row, "
            "bundled so you can try out the training pipeline without uploading your own data. "
            "Only 21 CpG sites are included, so this is best for a quick smoke test rather than "
            "gene set-filtered training (use the Compute Age Training subsets or a custom upload "
            "for that)."
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


# Registry of bundled example beta-value/metadata pairs that users can load
# instead of uploading their own data on the "Apply Built-in Aging Clocks" page.
EXAMPLE_PREDICTION_DATASETS = {
    "inflammatory_clocks_demo": {
        "label": "Blood inflammatory clocks demo (36 healthy control samples, 1308 CpGs)",
        "description": (
            "36 healthy-control blood samples covering 100% of the CpG sites used by all "
            "four built-in inflammatory clocks, so you can try out predictions on data "
            "known to work well without uploading your own file."
        ),
        "beta_path": os.path.join(PROJECT_ROOT, "backend/data/example_datasets/apply_demo_inflammatory_clocks_beta.csv"),
        "meta_path": os.path.join(PROJECT_ROOT, "backend/data/example_datasets/apply_demo_inflammatory_clocks_meta.csv"),
        # This beta table was assembled to cover the clocks 100%, so its row index is
        # exactly the union of their secret CpG sites: it is stored encrypted at rest
        # (see secure_features_service) and only decrypted into the user's temp folder.
        "protected_beta_name": os.path.join("example_datasets", "apply_demo_inflammatory_clocks_beta.csv"),
    },
}


def list_example_prediction_datasets():
    """Returns the id -> {label, description} mapping for UI display."""
    return {
        dataset_id: {"label": info["label"], "description": info["description"]}
        for dataset_id, info in EXAMPLE_PREDICTION_DATASETS.items()
    }


def is_protected_prediction_dataset(dataset_id: str) -> bool:
    """True if the dataset's beta table is encrypted at rest.

    Such a table was assembled to cover a built-in clock completely, so its row
    index is that clock's proprietary CpG list and must not be displayed.
    """
    info = EXAMPLE_PREDICTION_DATASETS.get(dataset_id, {})
    return bool(info.get("protected_beta_name"))


def get_example_prediction_dataset_paths(dataset_id: str):
    """Returns (beta_path, meta_path) for a bundled example prediction dataset id."""
    if dataset_id not in EXAMPLE_PREDICTION_DATASETS:
        raise ValueError(f"Unknown example dataset: {dataset_id}")
    info = EXAMPLE_PREDICTION_DATASETS[dataset_id]
    return info["beta_path"], info["meta_path"]


def materialize_example_prediction_dataset(dataset_id: str, dest_beta_path: str, dest_meta_path: str):
    """Places a bundled example prediction dataset into the user's temp folder.

    Handles both plain and encrypted-at-rest beta tables, so the caller does not
    need to know which of the two a given dataset uses.

    Returns:
        tuple: (dest_beta_path, dest_meta_path)
    """
    if dataset_id not in EXAMPLE_PREDICTION_DATASETS:
        raise ValueError(f"Unknown example dataset: {dataset_id}")
    info = EXAMPLE_PREDICTION_DATASETS[dataset_id]

    protected_name = info.get("protected_beta_name")
    if protected_name:
        materialize_protected_file(protected_name, dest_beta_path)
    else:
        shutil.copyfile(info["beta_path"], dest_beta_path)

    shutil.copyfile(info["meta_path"], dest_meta_path)
    return dest_beta_path, dest_meta_path
