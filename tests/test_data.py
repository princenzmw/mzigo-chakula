"""Unit tests for dataset loading, schema validation, geographic normalization, and profiling."""

from __future__ import annotations

from pathlib import Path

import pytest

from mzigo_chakula.data import (
    COUNTY_MAPPING,
    EXPECTED_COLUMNS,
    load_data,
    resolve_geography,
)


def test_load_data_row_counts(
    physical_market_rows: list[dict[str, str]],
    all_rows: list[dict[str, str]],
) -> None:
    """Confirm exact row counts with and without Market Average aggregate series."""
    assert len(all_rows) == 55692
    assert len(physical_market_rows) == 55454
    assert len(all_rows) - len(physical_market_rows) == 238
    assert all(row["mkt_name"] != "Market Average" for row in physical_market_rows)


def test_load_data_missing_file(tmp_path: Path) -> None:
    """Raise FileNotFoundError when the CSV path does not exist."""
    missing = tmp_path / "does_not_exist.csv"
    with pytest.raises(FileNotFoundError):
        load_data(csv_path=missing)


def test_load_data_schema_mismatch(tmp_path: Path) -> None:
    """Raise ValueError when columns do not match the 46 expected fields."""
    bad_csv = tmp_path / "bad_schema.csv"
    bad_csv.write_text("ISO3,country,mkt_name\nKEN,Kenya,Wakulima\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Schema mismatch"):
        load_data(csv_path=bad_csv)


@pytest.mark.parametrize(
    ("adm1", "adm2", "mkt", "expected_region", "expected_county"),
    [
        ("Coast", "Tana River", "Adele Center", "Coast", "Tana River"),
        ("Hola (Tana River)", "Hola (Tana River)", "Hola (Tana River)", "Coast", "Tana River"),
        ("Coast", "Kwale", "Vanga (Kwale)", "Coast", "Kwale"),
        ("Kwale", "Matuga", "Kwale", "Coast", "Kwale"),
        ("Rift Valley", "Kajiado", "Kajiado", "Rift Valley", "Kajiado"),
        ("Kajiado", "Ongata Rongai", "Ongata Rongai", "Rift Valley", "Kajiado"),
        ("Nairobi", "Nairobi", "Kitengela (Kajiado)", "Rift Valley", "Kajiado"),
        ("Nairobi", "Nairobi", "Wakulima (Nairobi)", "Nairobi", "Nairobi"),
        ("Eastern", "Moyale", "Moyale town", "Eastern", "Marsabit"),
        ("North Eastern", "Ijara", "Hara (Garissa)", "North Eastern", "Garissa"),
        ("Eastern", "Meru South", "Kaanwa (Tharaka Nithi)", "Eastern", "Tharaka Nithi"),
        ("Tharaka Nithi", "Chuka/Igambang'Ombe", "Tharaka Nithi", "Eastern", "Tharaka Nithi"),
        ("Coast", "Taita Taveta", "Mtito Andei", "Coast", "Taita Taveta"),
        ("Taita Taveta", "Voi", "Taita Taveta", "Coast", "Taita Taveta"),
    ],
)
def test_resolve_geography_edge_cases(
    adm1: str,
    adm2: str,
    mkt: str,
    expected_region: str,
    expected_county: str,
) -> None:
    """Ensure split counties and market-level overrides map deterministically."""
    region, county, _ = resolve_geography(adm1, adm2, mkt)
    assert region == expected_region
    assert county == expected_county


def test_resolve_geography_rejects_unknown_pair() -> None:
    """Raise ValueError on unmapped admin pairs."""
    with pytest.raises(ValueError, match="Unmapped administrative pair"):
        resolve_geography("UnknownRegion", "UnknownCounty", "Test Market")


def test_county_mapping_covers_all_raw_pairs(
    physical_market_rows: list[dict[str, str]],
) -> None:
    """Verify every (adm1_name, adm2_name) pair in the dataset is mapped."""
    observed_pairs = {(r["adm1_name"], r["adm2_name"]) for r in physical_market_rows}
    assert len(observed_pairs) == 35
    assert observed_pairs.issubset(COUNTY_MAPPING.keys())


def test_profile_dataset_invariants(dataset_profile: dict) -> None:
    """Confirm deterministic profiling metrics match the raw CSV."""
    assert dataset_profile["total_rows"] == 55692
    assert dataset_profile["total_columns"] == 46
    assert dataset_profile["physical_market_rows"] == 55454
    assert dataset_profile["market_average_rows"] == 238
    assert dataset_profile["physical_markets_count"] == 233
    assert dataset_profile["total_series_count"] == 234
    assert dataset_profile["clean_counties_count"] == 27
    assert dataset_profile["clean_regions_count"] == 7
    assert dataset_profile["date_min"] == "2007-01-01"
    assert dataset_profile["date_max"] == "2026-10-01"
    assert dataset_profile["distinct_months"] == 238
    assert len(dataset_profile["column_profiles"]) == 46
    col_names = tuple(c["column_name"] for c in dataset_profile["column_profiles"])
    assert col_names == EXPECTED_COLUMNS
