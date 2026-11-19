"""Unit tests for Week 5 final report, presentation deck, contribution matrix, and README."""

from __future__ import annotations

import re
from pathlib import Path

from pptx import Presentation

from mzigo_chakula.data import PROJECT_ROOT
from mzigo_chakula.generate_week5_deliverables import generate_week5_outputs


def _count_pdf_pages(pdf_path: Path) -> int:
    """Count PDF pages using exact /Type /Page dictionary markers."""
    raw = pdf_path.read_bytes()
    return len(re.findall(rb"/Type\s*/Page(?![sA-Za-z])", raw))


def test_generate_week5_outputs(raw_csv_path: Path, tmp_path: Path) -> None:
    """Verify isolated Week 5 output generation (11-page PDF, 12-slide PPTX, matrix)."""
    outputs = generate_week5_outputs(
        csv_path=raw_csv_path,
        docs_dir=tmp_path / "docs",
        slides_dir=tmp_path / "slides",
        contribution_dir=tmp_path / "contribution",
        update_readme=False,
    )

    page_count = _count_pdf_pages(outputs["report_pdf"])
    assert 10 <= page_count <= 15

    prs = Presentation(str(outputs["presentation_pptx"]))
    assert len(prs.slides) == 12
    for slide in prs.slides:
        assert slide.has_notes_slide
        notes_text = slide.notes_slide.notes_text_frame.text
        assert len(notes_text.strip()) > 20
        assert "\u2014" not in notes_text
        assert "\u2013" not in notes_text
        for shape in slide.shapes:
            if shape.has_text_frame:
                assert "\u2014" not in shape.text_frame.text
                assert "\u2013" not in shape.text_frame.text

    for md_key in ("report_md", "contribution_matrix"):
        text = outputs[md_key].read_text(encoding="utf-8")
        assert "\u2014" not in text
        assert "\u2013" not in text
        assert "[TBD]" not in text


def test_tracked_week5_artifacts_and_readme_clean() -> None:
    """Verify tracked Week 5 deliverables and updated README have zero TBD or AI dashes."""
    report_pdf = PROJECT_ROOT / "docs" / "report.pdf"
    pptx_path = PROJECT_ROOT / "slides" / "presentation.pptx"
    contrib_md = PROJECT_ROOT / "contribution" / "contribution-matrix.md"
    report_md = PROJECT_ROOT / "docs" / "report.md"
    readme_md = PROJECT_ROOT / "README.md"

    assert 10 <= _count_pdf_pages(report_pdf) <= 15
    prs = Presentation(str(pptx_path))
    assert len(prs.slides) == 12

    for md_path in (contrib_md, report_md, readme_md):
        text = md_path.read_text(encoding="utf-8")
        assert "\u2014" not in text
        assert "\u2013" not in text
        assert "[TBD]" not in text

    readme_text = readme_md.read_text(encoding="utf-8")
    assert "Tharaka Nithi" in readme_text
    assert "Prince Nzamuwe" in readme_text
    assert "Yizere Denis Derick" in readme_text

    expected_visuals = (
        PROJECT_ROOT / "screenshots" / "week1-initial-import.png",
        PROJECT_ROOT / "screenshots" / "week2-powerquery-cleaning.png",
        PROJECT_ROOT / "screenshots" / "week3-powerbi-model-view.png",
        PROJECT_ROOT / "screenshots" / "week3-dax-validation.png",
        PROJECT_ROOT / "docs" / "model-diagram.png",
        PROJECT_ROOT / "screenshots" / "page1-executive-pulse.png",
        PROJECT_ROOT / "screenshots" / "page2-county-commodity.png",
        PROJECT_ROOT / "screenshots" / "page3-trends-diagnostics.png",
        PROJECT_ROOT / "screenshots" / "page4-decisions-action.png",
    )
    for vis_path in expected_visuals:
        assert vis_path.is_file(), f"Missing embedded workflow visual: {vis_path}"
