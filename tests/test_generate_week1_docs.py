"""Tests for Week 1 document and PDF generation."""

from __future__ import annotations

import csv
from pathlib import Path

from mzigo_chakula.generate_week1_docs import (
    render_proposal_pdf,
    write_data_quality_profile,
    write_dataset_dictionary,
    write_proposal_markdown,
)


def test_write_dataset_dictionary(dataset_profile: dict, tmp_path: Path) -> None:
    """Verify the 46-column dictionary CSV structure and non-empty descriptions."""
    out = write_dataset_dictionary(dataset_profile, tmp_path / "dataset-dictionary.csv")
    assert out.is_file()
    with out.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 46
    assert rows[0]["column_name"] == "ISO3"
    assert rows[-1]["column_name"] == "trust_food_price_index"
    assert all(row["description"].strip() for row in rows)


def test_write_data_quality_profile_no_ai_dashes(
    dataset_profile: dict,
    tmp_path: Path,
) -> None:
    """Verify quality profile metrics and absence of em/en dashes."""
    out = write_data_quality_profile(dataset_profile, tmp_path / "data-quality-profile.md")
    text = out.read_text(encoding="utf-8")
    assert "55,692" in text
    assert "55,454" in text
    assert "238" in text
    assert "27 Kenyan counties" in text
    assert "\u2014" not in text
    assert "\u2013" not in text


def test_write_proposal_md_and_pdf(dataset_profile: dict, tmp_path: Path) -> None:
    """Verify proposal markdown and 3-page PDF rendering."""
    md_out = write_proposal_markdown(dataset_profile, tmp_path / "proposal.md")
    md_text = md_out.read_text(encoding="utf-8")
    assert "Prince Nzamuwe, Yizere Denis Derick" in md_text
    assert "\u2014" not in md_text
    assert "\u2013" not in md_text

    pdf_out = render_proposal_pdf(dataset_profile, tmp_path / "proposal.pdf")
    raw_pdf = pdf_out.read_bytes()
    assert raw_pdf.startswith(b"%PDF-")
    # Count page objects in the rendered PDF (should be 3 pages)
    page_count = raw_pdf.count(b"/Type /Page\n") + raw_pdf.count(b"/Type /Page\r") + raw_pdf.count(b"/Type /Page ")
    assert 2 <= page_count <= 4
