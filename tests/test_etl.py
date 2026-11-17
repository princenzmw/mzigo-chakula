"""Unit tests for Week 2 ETL transformations, star-schema integrity, and deliverables."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from mzigo_chakula.etl import (
    ETLResult,
    classify_county_group,
    classify_kenya_season,
    run_etl,
)
from mzigo_chakula.generate_week2_deliverables import generate_week2_outputs


@pytest.fixture(scope="module")
def etl_result(raw_csv_path: Path) -> ETLResult:
    """Execute the Week 2 ETL pipeline once for this test module."""
    return run_etl(csv_path=raw_csv_path)


def test_star_schema_row_counts(etl_result: ETLResult) -> None:
    """Verify exact row counts across all four cleaned star-schema tables."""
    assert len(etl_result.dim_markets) == 233
    assert len(etl_result.dim_date) == 238
    assert len(etl_result.dim_commodity) == 3
    assert len(etl_result.fact_prices) == 166_362


def test_primary_and_foreign_key_integrity(etl_result: ETLResult) -> None:
    """Confirm zero duplicate primary keys and zero orphan foreign keys."""
    qa = etl_result.qa_metrics
    assert qa["duplicate_pk_counts"] == {
        "dim_markets": 0,
        "dim_date": 0,
        "dim_commodity": 0,
        "fact_prices": 0,
    }
    assert qa["orphan_fk_counts"] == {
        "mkt_id": 0,
        "date_key": 0,
        "commodity_id": 0,
    }


def test_dim_date_recency_and_seasons(etl_result: ETLResult) -> None:
    """Confirm recency windows, contiguous date span, and all Kenya seasons."""
    dates = etl_result.dim_date
    assert dates[0]["full_date"] == "2007-01-01"
    assert dates[-1]["full_date"] == "2026-10-01"

    recent_rows = [d for d in dates if d["is_recent"]]
    last_36m_rows = [d for d in dates if d["is_last_36m"]]
    assert len(recent_rows) == 12
    assert recent_rows[0]["full_date"] == "2025-11-01"
    assert recent_rows[-1]["full_date"] == "2026-10-01"

    assert len(last_36m_rows) == 36
    assert last_36m_rows[0]["full_date"] == "2023-11-01"
    assert last_36m_rows[-1]["full_date"] == "2026-10-01"

    seasons = {classify_kenya_season(month) for month in range(1, 13)}
    assert seasons == {
        "Hot Dry / Lean (Jan-Feb)",
        "Long Rains (Mar-May)",
        "Cool Dry / Harvest (Jun-Sep)",
        "Short Rains (Oct-Dec)",
    }
    with pytest.raises(ValueError, match="Invalid calendar month"):
        classify_kenya_season(13)


def test_dim_markets_geography_and_groups(etl_result: ETLResult) -> None:
    """Confirm market geography normalization and ASAL vs. Urban/Agri classification."""
    markets_by_name = {row["mkt_name"]: row for row in etl_result.dim_markets}
    assert "Market Average" not in markets_by_name

    kitengela = markets_by_name["Kitengela (Kajiado)"]
    assert kitengela["adm1_name"] == "Rift Valley"
    assert kitengela["adm2_name"] == "Kajiado"
    assert kitengela["county_group"] == "Arid & Semi-Arid (ASAL)"

    assert classify_county_group("Turkana") == "Arid & Semi-Arid (ASAL)"
    assert classify_county_group("Nairobi") == "Agricultural & Urban"

    qa = etl_result.qa_metrics
    assert qa["null_lat_lon_after"] == 0
    assert qa["asal_counties_count"] + qa["agri_urban_counties_count"] == 27


def test_fact_prices_mom_and_outliers(etl_result: ETLResult) -> None:
    """Confirm baseline MoM nulls, positive prices, and flagged outliers."""
    qa = etl_result.qa_metrics
    assert qa["null_price_value_after"] == 0
    assert qa["non_positive_price_count"] == 0
    assert qa["null_mom_rows"] == 699
    assert qa["valid_mom_rows"] == 165_663
    assert qa["outlier_rows"] > 0

    first_month_nulls = [
        r for r in etl_result.fact_prices if r["price_change_mom"] is None
    ]
    assert len(first_month_nulls) == 699
    assert {r["date_key"] for r in first_month_nulls} == {20070101}


def test_generate_week2_outputs(raw_csv_path: Path, tmp_path: Path) -> None:
    """Confirm Week 2 CSVs, .pq scripts, and transformation-log.md generate cleanly."""
    outputs = generate_week2_outputs(
        csv_path=raw_csv_path,
        processed_dir=tmp_path / "processed",
        powerquery_dir=tmp_path / "powerquery",
        docs_dir=tmp_path / "docs",
    )

    with outputs["dim_markets_csv"].open("r", encoding="utf-8", newline="") as handle:
        markets_rows = list(csv.DictReader(handle))
    assert len(markets_rows) == 233

    with outputs["dim_date_csv"].open("r", encoding="utf-8", newline="") as handle:
        date_rows = list(csv.DictReader(handle))
    assert len(date_rows) == 238

    with outputs["dim_commodity_csv"].open("r", encoding="utf-8", newline="") as handle:
        commodity_rows = list(csv.DictReader(handle))
    assert len(commodity_rows) == 3

    for pq_key in ("dim_markets_pq", "dim_date_pq", "dim_commodity_pq", "fact_prices_pq"):
        pq_text = outputs[pq_key].read_text(encoding="utf-8")
        assert len(pq_text) > 100
        if pq_key != "dim_commodity_pq":
            assert "QuoteStyle.Csv" in pq_text
            assert '"en-US"' in pq_text

    log_text = outputs["transformation_log"].read_text(encoding="utf-8")
    assert "\u2014" not in log_text
    assert "\u2013" not in log_text
    assert "166,362" in log_text
    assert "T10" in log_text
