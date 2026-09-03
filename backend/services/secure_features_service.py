"""Encryption-at-rest for the secret CpG feature lists of the built-in clocks.

The CpG sites used by "Blood inflammatory Clock 1" and "Blood inflammatory Clock 2"
(and the shared per-CpG mean table needed to impute missing sites) are proprietary:
they must not be readable by anyone who gets hold of the repository, a backup or the
server filesystem, and they must never leave the backend over the API.

Files listed in PROTECTED_DATA_FILES are stored on disk only in encrypted form
(``<name>.enc``, Fernet / AES-128-CBC + HMAC) and are decrypted in memory on demand.
The symmetric key is never stored in the repository; it is resolved, in order, from:

    1. the ``CLOCK_FEATURES_KEY`` environment variable (the key itself),
    2. the ``CLOCK_FEATURES_KEY_FILE`` environment variable (path to a key file),
    3. ``<PROJECT_ROOT>/.secrets/clock_features.key`` (gitignored, default for
       single-server deployments).

Use ``scripts/protect_clock_features.py`` to generate the key and to encrypt or
decrypt the files during maintenance.
"""

import io
import logging
import os
from typing import Dict

import pandas as pd
from cryptography.fernet import Fernet, InvalidToken

from backend.config import PROJECT_ROOT

DATA_DIR = os.path.join(PROJECT_ROOT, "backend", "data")
DEFAULT_KEY_PATH = os.path.join(PROJECT_ROOT, ".secrets", "clock_features.key")
ENCRYPTED_SUFFIX = ".enc"

# By default a leftover plaintext copy of a protected file is refused rather than
# read: silently falling back to it would defeat the encryption on any server where
# a maintenance --decrypt run was not cleaned up. Set CLOCK_FEATURES_ALLOW_PLAINTEXT=1
# for local development while the files have not been encrypted yet.
ALLOW_PLAINTEXT_ENV = "CLOCK_FEATURES_ALLOW_PLAINTEXT"


def plaintext_fallback_allowed() -> bool:
    """True if reading an unencrypted protected file is explicitly permitted."""
    return os.environ.get(ALLOW_PLAINTEXT_ENV, "").strip().lower() in {"1", "true", "yes"}

# Data files whose contents are secret. Paths are relative to backend/data/.
PROTECTED_DATA_FILES = [
    # Blood inflammatory Clock 1: model input order + nonzero-coefficient CpGs
    "hannum_elnet_cg_order.csv",
    "Hannum_Inflammation_elnet_nonzero_cpg_order.csv",
    # Blood inflammatory Clock 2 (and the XGBoost variant): input order + nonzero CpGs
    "inflamm_hugging_models_cg_order.csv",
    "computage_elnet_nonzero_cpg_order.csv",
    # Union of all clock CpGs with their means - knowing this set leaks the clocks
    "inflammation_cg_means.csv",
    # Demo dataset built to cover the clocks 100%, so its row index is that same union
    os.path.join("example_datasets", "apply_demo_inflammatory_clocks_beta.csv"),
]

# Decrypted file contents, cached in memory so we decrypt once per process
# instead of on every request.
_plaintext_cache: Dict[str, bytes] = {}


class ProtectedDataError(RuntimeError):
    """Raised when a protected data file cannot be read (missing key or file)."""


def get_key() -> bytes:
    """Returns the Fernet key for the protected data files.

    Raises:
        ProtectedDataError: if no key can be found.
    """
    env_key = os.environ.get("CLOCK_FEATURES_KEY")
    if env_key:
        return env_key.strip().encode()

    key_path = os.environ.get("CLOCK_FEATURES_KEY_FILE") or DEFAULT_KEY_PATH
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return f.read().strip()

    raise ProtectedDataError(
        "No encryption key found for the protected clock feature files. Set "
        "CLOCK_FEATURES_KEY, or CLOCK_FEATURES_KEY_FILE, or place the key in "
        f"{DEFAULT_KEY_PATH} (generate one with scripts/protect_clock_features.py --init)."
    )


def _resolve(relative_name: str) -> str:
    """Turns a name relative to backend/data into an absolute path."""
    return os.path.join(DATA_DIR, relative_name)


def read_protected_bytes(relative_name: str) -> bytes:
    """Returns the decrypted content of a protected data file.

    Prefers the encrypted ``<name>.enc`` file. A plaintext file of the same name is
    read only when CLOCK_FEATURES_ALLOW_PLAINTEXT is set (development convenience);
    otherwise it is refused, so a forgotten decrypted copy on a server cannot
    quietly bypass the encryption.
    """
    if relative_name in _plaintext_cache:
        return _plaintext_cache[relative_name]

    path = _resolve(relative_name)
    encrypted_path = path + ENCRYPTED_SUFFIX

    if os.path.exists(encrypted_path):
        with open(encrypted_path, "rb") as f:
            token = f.read()
        try:
            content = Fernet(get_key()).decrypt(token)
        except InvalidToken as exc:
            raise ProtectedDataError(
                f"Could not decrypt {os.path.basename(encrypted_path)} - the "
                "configured key does not match the one used for encryption."
            ) from exc
    elif os.path.exists(path):
        if not plaintext_fallback_allowed():
            logging.error(
                "Protected data file %s exists UNENCRYPTED and there is no %s file. "
                "Refusing to read it.",
                relative_name, ENCRYPTED_SUFFIX,
            )
            raise ProtectedDataError(
                f"Protected data file {relative_name} is present only in plaintext. "
                "Encrypt it with scripts/protect_clock_features.py --encrypt "
                "--remove-plaintext, or set "
                f"{ALLOW_PLAINTEXT_ENV}=1 to allow this in development."
            )
        logging.warning(
            "Protected data file %s is stored UNENCRYPTED and is being read because "
            "%s is set. Run scripts/protect_clock_features.py to encrypt it.",
            relative_name, ALLOW_PLAINTEXT_ENV,
        )
        with open(path, "rb") as f:
            content = f.read()
    else:
        raise ProtectedDataError(f"Protected data file not found: {relative_name}")

    _plaintext_cache[relative_name] = content
    return content


def read_protected_csv(relative_name: str, **read_csv_kwargs) -> pd.DataFrame:
    """Reads a protected CSV (encrypted at rest) into a DataFrame."""
    return pd.read_csv(io.BytesIO(read_protected_bytes(relative_name)), **read_csv_kwargs)


def materialize_protected_file(relative_name: str, destination_path: str) -> str:
    """Writes the decrypted content of a protected file to ``destination_path``.

    Used for bundled example datasets that have to exist as a real file in the
    user's temp directory for the rest of the pipeline to read.
    """
    content = read_protected_bytes(relative_name)
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    with open(destination_path, "wb") as f:
        f.write(content)
    return destination_path


def encrypt_file(path: str, key: bytes) -> str:
    """Encrypts ``path`` to ``path + '.enc'`` and returns the encrypted path."""
    with open(path, "rb") as f:
        plaintext = f.read()
    encrypted_path = path + ENCRYPTED_SUFFIX
    with open(encrypted_path, "wb") as f:
        f.write(Fernet(key).encrypt(plaintext))
    return encrypted_path


def decrypt_file(encrypted_path: str, key: bytes) -> str:
    """Decrypts ``<name>.enc`` back to ``<name>`` and returns the plaintext path."""
    with open(encrypted_path, "rb") as f:
        token = f.read()
    plaintext_path = encrypted_path[: -len(ENCRYPTED_SUFFIX)]
    with open(plaintext_path, "wb") as f:
        f.write(Fernet(key).decrypt(token))
    return plaintext_path
