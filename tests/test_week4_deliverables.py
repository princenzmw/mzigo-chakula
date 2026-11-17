"""Unit tests for Week 4 dashboard screenshots, report layout, and usability insights."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from mzigo_chakula.data import PROJECT_ROOT
from mzigo_chakula.generate_week4_deliverables import generate_week4_outputs

EXPECTED_PAGES = (
    "page1-executive-pulse.png",
    "page2-county-commodity.png",
    "page3-trends-diagnostics.png",
    "page4-decisions-action.png",
)


def _load_tmdl_symbols() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Parse table column and measure names from exported SemanticModel TMDL files."""
    tables_dir = PROJECT_ROOT / "pbip" / "mzigo-chakula.SemanticModel" / "definition" / "tables"
    columns_by_table: dict[str, set[str]] = {}
    measures_by_table: dict[str, set[str]] = {}
    for tmdl_path in tables_dir.glob("*.tmdl"):
        table_name = tmdl_path.stem
        cols: set[str] = set()
        meas: set[str] = set()
        for line in tmdl_path.read_text(encoding="utf-8").splitlines():
            col_match = re.match(r"^\tcolumn\s+(?:'([^']+)'|(\S+))\s*$", line)
            if col_match:
                cols.add(col_match.group(1) or col_match.group(2))
            meas_match = re.match(r"^\tmeasure\s+(?:'([^']+)'|([^\s=]+))\s*=", line)
            if meas_match:
                meas.add(meas_match.group(1) or meas_match.group(2))
        columns_by_table[table_name] = cols
        measures_by_table[table_name] = meas
    return columns_by_table, measures_by_table


def _iter_field_refs(obj: Any) -> list[tuple[str, str, str]]:
    """Collect (kind, entity, prop) tuples from PBIR Column and Measure expressions."""
    refs: list[tuple[str, str, str]] = []
    if isinstance(obj, dict):
        for kind in ("Column", "Measure"):
            if kind in obj and isinstance(obj[kind], dict):
                node = obj[kind]
                entity = node.get("Expression", {}).get("SourceRef", {}).get("Entity")
                prop = node.get("Property")
                if isinstance(entity, str) and isinstance(prop, str):
                    refs.append((kind, entity, prop))
        for val in obj.values():
            refs.extend(_iter_field_refs(val))
    elif isinstance(obj, list):
        for item in obj:
            refs.extend(_iter_field_refs(item))
    return refs


def test_report_json_defines_four_pages() -> None:
    """Confirm PBIR pages, 40 visual.json files, and all bound TMDL symbols are valid."""
    pages_root = PROJECT_ROOT / "pbip" / "mzigo-chakula.Report" / "definition" / "pages"
    pages_meta_path = pages_root / "pages.json"
    assert pages_meta_path.is_file()
    pages_meta = json.loads(pages_meta_path.read_text(encoding="utf-8"))
    page_order = pages_meta["pageOrder"]
    assert len(page_order) == 4

    expected_titles = [
        "Executive Pulse",
        "County and Commodity",
        "Trends and Diagnostics",
        "Decisions and Action",
    ]
    columns_by_table, measures_by_table = _load_tmdl_symbols()

    observed_titles: list[str] = []
    total_visuals = 0
    for page_id in page_order:
        page_dir = pages_root / page_id
        page_json_path = page_dir / "page.json"
        assert page_json_path.is_file(), f"Missing page.json: {page_json_path}"
        page_data = json.loads(page_json_path.read_text(encoding="utf-8"))
        observed_titles.append(page_data["displayName"])
        assert page_data["width"] == 1280
        assert page_data["height"] == 720

        visual_files = list((page_dir / "visuals").glob("*/visual.json"))
        assert len(visual_files) >= 8, f"Expected >=8 visuals on {page_id}, found {len(visual_files)}"
        total_visuals += len(visual_files)

        for vf in visual_files:
            payload = json.loads(vf.read_text(encoding="utf-8"))
            refs = _iter_field_refs(payload["visual"]["query"])
            assert refs, f"Visual {vf} has no field projections"
            for kind, entity, prop in refs:
                if kind == "Column":
                    assert prop in columns_by_table.get(entity, set()), (
                        f"{vf}: unknown column {entity}[{prop}]"
                    )
                else:
                    assert prop in measures_by_table.get(entity, set()), (
                        f"{vf}: unknown measure {entity}[{prop}]"
                    )

    assert observed_titles == expected_titles
    assert total_visuals == 40


def test_week4_screenshots_dimensions_and_dpi() -> None:
    """Verify all 4 dashboard PNGs exist in screenshots/ and output/ at 2400x1350, 300 DPI."""
    for filename in EXPECTED_PAGES:
        shot_path = PROJECT_ROOT / "screenshots" / filename
        out_path = PROJECT_ROOT / "output" / filename
        assert shot_path.is_file(), f"Missing screenshot: {shot_path}"
        assert out_path.is_file(), f"Missing 300 DPI output copy: {out_path}"

        for path in (shot_path, out_path):
            with Image.open(path) as img:
                assert img.size == (2400, 1350)
                dpi = img.info.get("dpi", (0, 0))
                assert dpi[0] == pytest.approx(300, abs=1)
                assert dpi[1] == pytest.approx(300, abs=1)


def test_generate_week4_outputs_and_no_ai_dashes(raw_csv_path: Path, tmp_path: Path) -> None:
    """Confirm generator succeeds cleanly and usability-and-insights.md has zero AI dashes."""
    outputs = generate_week4_outputs(csv_path=raw_csv_path, docs_dir=tmp_path)
    doc_text = outputs["usability_and_insights"].read_text(encoding="utf-8")
    assert len(doc_text) > 500
    assert "\u2014" not in doc_text
    assert "\u2013" not in doc_text
    assert "Tharaka Nithi" in doc_text
    assert "99.99%" in doc_text

    tracked_doc = PROJECT_ROOT / "docs" / "usability-and-insights.md"
    assert tracked_doc.is_file()
    tracked_text = tracked_doc.read_text(encoding="utf-8")
    assert "\u2014" not in tracked_text
    assert "\u2013" not in tracked_text
