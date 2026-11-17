"""Unit tests for Week 4 dashboard screenshots, report layout, and usability insights."""

from __future__ import annotations

import json
from pathlib import Path

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


def test_report_json_defines_four_pages() -> None:
    """Confirm pbip/mzigo-chakula.Report/report.json defines all 4 required pages."""
    report_path = PROJECT_ROOT / "pbip" / "mzigo-chakula.Report" / "report.json"
    assert report_path.is_file()
    data = json.loads(report_path.read_text(encoding="utf-8"))
    sections = data["sections"]
    assert len(sections) == 4
    names = [section["displayName"] for section in sections]
    assert names == [
        "Executive Pulse",
        "County and Commodity",
        "Trends and Diagnostics",
        "Decisions and Action",
    ]
    for section in sections:
        assert section["width"] == 1280.0
        assert section["height"] == 720.0


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
