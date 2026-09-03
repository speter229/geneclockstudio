"""Validation of client-supplied file paths.

Several endpoints take a path to a file the frontend has already written into the
server's temp directory. Without validation a client can point those paths at any
file on the server - including the secret CpG-order CSVs of the built-in clocks,
whose contents can then be read back out through the endpoint's response
(e.g. /train/gene_cpgs_request/ echoes the row index of whatever it was given).

``resolve_user_data_path`` restricts such paths to the directories that legitimately
hold user data: the per-user temp folders and the bundled example datasets/genesets.
"""

import os

from fastapi import HTTPException

from backend.config import PROJECT_ROOT, TEMP_PATH

# Directories a client is allowed to reference in a request.
ALLOWED_DATA_ROOTS = [
    os.path.realpath(TEMP_PATH),
    os.path.realpath(os.path.join(PROJECT_ROOT, "backend", "data", "example_datasets")),
    os.path.realpath(os.path.join(PROJECT_ROOT, "backend", "data", "example_genesets")),
]


def is_allowed_data_path(path: str) -> bool:
    """True if ``path`` resolves inside one of the allowed data directories."""
    real_path = os.path.realpath(path)
    return any(
        os.path.commonpath([real_path, root]) == root
        for root in ALLOWED_DATA_ROOTS
    )


def resolve_user_data_path(client_path: str, must_exist: bool = True) -> str:
    """Resolves a client-supplied path and verifies it points at user data.

    Accepts both absolute paths and paths relative to PROJECT_ROOT (the frontend
    sends absolute temp paths, older callers sent relative ones). Symlinks and
    ``..`` segments are resolved before the check, so neither can escape the
    allowed directories.

    Args:
        client_path: The path as received from the client.
        must_exist: Raise 400 if the resolved file does not exist.

    Returns:
        The absolute, validated path.

    Raises:
        HTTPException: 400 if the path is malformed, outside the allowed
            directories, or (when required) missing.
    """
    if not client_path or not isinstance(client_path, str):
        raise HTTPException(status_code=400, detail="No file path provided.")

    candidate = client_path if os.path.isabs(client_path) else os.path.join(PROJECT_ROOT, client_path)
    real_path = os.path.realpath(candidate)

    if not is_allowed_data_path(real_path):
        # Deliberately vague: do not confirm to the caller whether the file exists.
        raise HTTPException(status_code=400, detail="Invalid file path.")

    if must_exist and not os.path.isfile(real_path):
        raise HTTPException(status_code=400, detail="File not found on the server.")

    return real_path
