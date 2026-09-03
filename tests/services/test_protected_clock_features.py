"""Tests for the secrecy of the built-in clocks' CpG feature lists."""

import os

import pytest
from fastapi import HTTPException

from backend.config import PROJECT_ROOT, TEMP_PATH
from backend.services.path_guard import resolve_user_data_path
from backend.services.predictive_model_service import bucket_percent, calculate_feature_coverage
from backend.services.secure_features_service import (
    ENCRYPTED_SUFFIX,
    PROTECTED_DATA_FILES,
    _resolve,
    read_protected_csv,
)


def test_protected_files_are_not_stored_in_plaintext():
    """Every secret data file must exist only in its encrypted form on disk."""
    for name in PROTECTED_DATA_FILES:
        path = _resolve(name)
        assert os.path.exists(path + ENCRYPTED_SUFFIX), f"missing encrypted file for {name}"
        assert not os.path.exists(path), (
            f"{name} is present in plaintext - run "
            "scripts/protect_clock_features.py --encrypt --remove-plaintext"
        )


def test_protected_files_can_be_decrypted():
    """The clock feature lists must still be readable through the service."""
    clock1 = read_protected_csv("hannum_elnet_cg_order.csv", index_col=0)
    clock2 = read_protected_csv("inflamm_hugging_models_cg_order.csv", index_col=0)
    assert len(clock1) > 1000
    assert len(clock2) > 1000


@pytest.mark.parametrize(
    "raw, expected",
    [(0, 0), (4.9, 0), (5, 5), (7.7, 5), (99.9, 95), (100, 100)],
)
def test_bucket_percent_never_overstates_coverage(raw, expected):
    assert bucket_percent(raw) == expected


def test_single_cpg_probe_reveals_nothing():
    """Asking about one CpG site must not disclose whether a clock uses it."""
    clock2_cpgs = read_protected_csv("inflamm_hugging_models_cg_order.csv")["ID"].tolist()
    member = calculate_feature_coverage([clock2_cpgs[0]])
    non_member = calculate_feature_coverage(["cg99999999"])
    assert member == non_member == [0, 0, 0, 0]


def test_path_guard_allows_user_temp_files(tmp_path):
    user_dir = os.path.join(TEMP_PATH, "pytest_path_guard_user")
    os.makedirs(user_dir, exist_ok=True)
    path = os.path.join(user_dir, "betas.csv")
    with open(path, "w") as f:
        f.write("cpg,S1\ncg00000001,0.5\n")
    try:
        assert resolve_user_data_path(path) == os.path.realpath(path)
    finally:
        os.remove(path)


@pytest.mark.parametrize(
    "client_path",
    [
        "backend/data/inflammation_cg_means.csv.enc",
        "backend/data/hannum_elnet_cg_order.csv.enc",
        "backend/temp/../data/inflamm_hugging_models_cg_order.csv.enc",
        "backend/data/users.json",
        ".secrets/clock_features.key",
        os.path.join(PROJECT_ROOT, "backend", "models", "aging_clocks"),
    ],
)
def test_path_guard_blocks_everything_outside_user_data(client_path):
    with pytest.raises(HTTPException) as exc:
        resolve_user_data_path(client_path, must_exist=False)
    assert exc.value.status_code == 400


def test_plaintext_only_file_is_refused_by_default(tmp_path, monkeypatch):
    """A forgotten decrypted copy on the server must not silently bypass encryption."""
    from backend.services import secure_features_service as sfs

    monkeypatch.delenv(sfs.ALLOW_PLAINTEXT_ENV, raising=False)
    monkeypatch.setattr(sfs, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(sfs, "_plaintext_cache", {})
    (tmp_path / "leaked.csv").write_text("cpg\ncg00000029\n")

    with pytest.raises(sfs.ProtectedDataError):
        sfs.read_protected_bytes("leaked.csv")


def test_plaintext_only_file_is_read_when_explicitly_allowed(tmp_path, monkeypatch):
    """The development escape hatch still works when opted into."""
    from backend.services import secure_features_service as sfs

    monkeypatch.setenv(sfs.ALLOW_PLAINTEXT_ENV, "1")
    monkeypatch.setattr(sfs, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(sfs, "_plaintext_cache", {})
    (tmp_path / "dev.csv").write_text("cpg\ncg00000029\n")

    assert b"cg00000029" in sfs.read_protected_bytes("dev.csv")
