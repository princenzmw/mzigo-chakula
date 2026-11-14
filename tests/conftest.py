"""Shared pytest fixtures for Mzigo Chakula data loading and profiling tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from mzigo_chakula.data import DEFAULT_RAW_CSV, load_data, profile_dataset


@pytest.fixture(scope="session")
def raw_csv_path() -> Path:
    """Return the path to the raw World Bank RTFP Kenya CSV."""
    return DEFAULT_RAW_CSV


@pytest.fixture(scope="session")
def physical_market_rows(raw_csv_path: Path) -> list[dict[str, str]]:
    """Load all physical market rows excluding Market Average."""
    return load_data(csv_path=raw_csv_path, include_market_average=False)


@pytest.fixture(scope="session")
def all_rows(raw_csv_path: Path) -> list[dict[str, str]]:
    """Load all rows including Market Average."""
    return load_data(csv_path=raw_csv_path, include_market_average=True)


@pytest.fixture(scope="session")
def dataset_profile(raw_csv_path: Path) -> dict:
    """Compute the full dataset profile once per test session."""
    return profile_dataset(csv_path=raw_csv_path)
