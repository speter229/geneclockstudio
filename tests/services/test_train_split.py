"""The train/evaluation split is user-selectable, so its bounds must hold end to end."""

import pytest
from pydantic import ValidationError

from backend.schemas.train_schema import (
    DEFAULT_TEST_SIZE,
    MAX_TEST_SIZE,
    MIN_TEST_SIZE,
    TrainModelRequest,
)


def _request(**kwargs):
    return TrainModelRequest(model_name="ElasticNet", model_params="{}", **kwargs)


def test_default_is_the_classic_80_20_split():
    assert _request().test_size == DEFAULT_TEST_SIZE == 0.2


@pytest.mark.parametrize("test_size", [MIN_TEST_SIZE, 0.2, 0.35, MAX_TEST_SIZE])
def test_accepts_splits_inside_the_allowed_range(test_size):
    assert _request(test_size=test_size).test_size == test_size


@pytest.mark.parametrize("test_size", [0.0, 0.05, 0.51, 0.9, 1.0, -0.1])
def test_rejects_splits_outside_the_allowed_range(test_size):
    """Outside 10-50% one of the two sets is too small for the reported metrics."""
    with pytest.raises(ValidationError):
        _request(test_size=test_size)


def test_slider_range_on_the_train_page_maps_into_the_allowed_range():
    """The page offers 50-90% training in 5% steps; every value must be accepted."""
    for train_percent in range(50, 95, 5):
        test_size = round((100 - train_percent) / 100, 2)
        assert MIN_TEST_SIZE <= test_size <= MAX_TEST_SIZE
        assert _request(test_size=test_size).test_size == test_size
