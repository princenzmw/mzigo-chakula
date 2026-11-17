"""Unit tests for Week 3 DAX validator, semantic model export, and deliverables."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from mzigo_chakula.data import PROJECT_ROOT
from mzigo_chakula.dax_validator import DAX_MEASURES, compute_dax_validation_summary
from mzigo_chakula.etl import COMMODITY_SPECS, ETLResult, run_etl
from mzigo_chakula.generate_week3_deliverables import generate_week3_outputs


@pytest.fixture(scope="module")
def etl_result(raw_csv_path: Path) -> ETLResult:
    """Compute Week 2 ETL once for Week 3 validation tests."""
    return run_etl(csv_path=raw_csv_path)


def test_dax_measure_specs_complete() -> None:
    """Verify all 15 DAX measures are numbered sequentially and non-empty."""
    assert len(DAX_MEASURES) == 15
    assert [spec.measure_number for spec in DAX_MEASURES] == list(range(1, 16))
    for spec in DAX_MEASURES:
        assert spec.table_name == "fact_prices"
        assert len(spec.dax_expression.strip()) > 0
        assert len(spec.description.strip()) > 0


def test_dax_validation_summary_invariants(etl_result: ETLResult) -> None:
    """Confirm DAX reference KPIs, grain safety, and zero-sum affordability gap."""
    summary = compute_dax_validation_summary(etl_result)
    overall = summary["overall"]

    assert overall["data_completeness_pct"] == pytest.approx(1.0)
    assert 0.03 < overall["survey_coverage_rate_pct"] < 0.06
    assert overall["national_food_index_full"] == pytest.approx(1.2005, abs=0.001)
    assert len(summary["counties"]) == 27

    for spec in COMMODITY_SPECS:
        cid = spec.commodity_id
        assert abs(summary["gap_weighted_sums"][cid]) < 1e-9
        months = summary["seasonal_by_month"][cid]
        assert len(months) == 12
        mean_idx = sum(m["seasonal_index"] for m in months) / 12
        assert mean_idx == pytest.approx(1.0, abs=0.02)


def test_pbip_and_tmdl_files_exist() -> None:
    """Verify Power BI Project manifests, BIM, and all 7 TMDL files exist."""
    pbip_root = PROJECT_ROOT / "pbip"
    assert (pbip_root / "mzigo-chakula.pbip").is_file()
    assert (pbip_root / "mzigo-chakula.Report" / "definition.pbir").is_file()
    assert (pbip_root / "mzigo-chakula.Report" / "report.json").is_file()

    model_root = pbip_root / "mzigo-chakula.SemanticModel"
    assert (model_root / "definition.pbism").is_file()
    assert (model_root / "model.bim").is_file()

    def_dir = model_root / "definition"
    expected_tmdl = [
        def_dir / "database.tmdl",
        def_dir / "model.tmdl",
        def_dir / "relationships.tmdl",
        def_dir / "tables" / "dim_markets.tmdl",
        def_dir / "tables" / "dim_date.tmdl",
        def_dir / "tables" / "dim_commodity.tmdl",
        def_dir / "tables" / "fact_prices.tmdl",
    ]
    for path in expected_tmdl:
        assert path.is_file(), f"Missing exported TMDL file: {path}"


def test_generate_week3_outputs(raw_csv_path: Path, tmp_path: Path) -> None:
    """Confirm model diagram (300 DPI) and DAX catalogue generate cleanly without dashes."""
    outputs = generate_week3_outputs(csv_path=raw_csv_path, docs_dir=tmp_path)

    with Image.open(outputs["model_diagram"]) as img:
        assert img.size == (2400, 1650)
        dpi = img.info.get("dpi", (0, 0))
        assert dpi[0] == pytest.approx(300, abs=1)
        assert dpi[1] == pytest.approx(300, abs=1)

    catalogue_text = outputs["dax_catalogue"].read_text(encoding="utf-8")
    assert "\u2014" not in catalogue_text
    assert "\u2013" not in catalogue_text
    assert "National Food Price Index" in catalogue_text
    assert "166,362" in catalogue_text
