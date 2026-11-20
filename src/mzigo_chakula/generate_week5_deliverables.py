"""Generate Week 5 final report (MD/PDF), 12-slide presentation (.pptx), and contribution matrix."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from fpdf import FPDF
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

from mzigo_chakula.data import DEFAULT_RAW_CSV, PROJECT_ROOT
from mzigo_chakula.dax_validator import DAX_MEASURES, compute_dax_validation_summary
from mzigo_chakula.etl import COMMODITY_SPECS, ETLResult, run_etl
from mzigo_chakula.generate_week4_deliverables import (
    BG_CANVAS,
    CANVAS_H,
    CANVAS_W,
    COLOR_AGRI,
    COLOR_AMBER,
    COLOR_ASAL,
    COLOR_BLUE,
    COLOR_SLATE,
    NAVY,
    _draw_hbar_chart,
    _draw_kpi_card,
    _draw_panel,
    _draw_table,
    _fonts_bundle,
)

DOCS_DIR = PROJECT_ROOT / "docs"
SLIDES_DIR = PROJECT_ROOT / "slides"
CONTRIBUTION_DIR = PROJECT_ROOT / "contribution"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Slide palette
PPTX_NAVY = RGBColor(0x0F, 0x29, 0x42)
PPTX_BLUE = RGBColor(0x1D, 0x4E, 0xD8)
PPTX_TEAL = RGBColor(0x0F, 0x76, 0x6E)
PPTX_ORANGE = RGBColor(0xEA, 0x58, 0x0C)
PPTX_DARK = RGBColor(0x0F, 0x17, 0x2A)
PPTX_MUTED = RGBColor(0x47, 0x55, 0x69)
PPTX_LIGHT = RGBColor(0xF1, 0xF5, 0xF9)
PPTX_WHITE = RGBColor(0xFF, 0xFF, 0xFF)


class ReportPDF(FPDF):
    """A4 technical project report with running header and page counter."""

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(100, 116, 139)
        self.cell(
            0,
            6,
            "Mzigo Chakula: Kenya Food Price Inflation & Household Affordability (DSA 3050A)",
            align="L",
        )
        self.ln(8)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(100, 116, 139)
        self.cell(0, 8, f"DSA 3050A Group Project B | Page {self.page_no()}/{{nb}}", align="C")


def _pdf_heading(pdf: ReportPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 12.5)
    pdf.set_text_color(15, 41, 66)
    pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(203, 213, 225)
    y = pdf.get_y()
    pdf.line(15, y, 195, y)
    pdf.ln(3)


def _pdf_subheading(pdf: ReportPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _pdf_body(pdf: ReportPDF, text: str, size: float = 9.5) -> None:
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(15, 23, 42)
    pdf.multi_cell(0, 4.7, text, align="L")
    pdf.ln(2.2)


def _pdf_table(
    pdf: ReportPDF,
    headers: list[str],
    rows: list[list[str]],
    widths: list[float],
    font_size: float = 8.0,
) -> None:
    """Render wrapped table inside ReportPDF matching column inner widths."""
    pdf.set_font("Helvetica", "B", font_size)
    pdf.set_fill_color(15, 41, 66)
    pdf.set_text_color(255, 255, 255)
    line_h = 4.2
    for hdr, w in zip(headers, widths, strict=True):
        pdf.cell(w, 6.2, hdr, border=1, align="L", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", font_size)
    pdf.set_text_color(15, 23, 42)
    for r_idx, row in enumerate(rows):
        if r_idx % 2 == 1:
            pdf.set_fill_color(248, 250, 252)
        else:
            pdf.set_fill_color(255, 255, 255)

        line_counts = [
            max(1, len(pdf.multi_cell(w - 2.4, line_h, cell, dry_run=True, output="LINES")))
            for cell, w in zip(row, widths, strict=True)
        ]
        row_h = max(line_counts) * line_h + 2.2
        y_start = pdf.get_y()
        x_curr = pdf.l_margin
        for cell, w in zip(row, widths, strict=True):
            pdf.rect(x_curr, y_start, w, row_h, style="DF")
            pdf.set_xy(x_curr + 1.2, y_start + 1.1)
            pdf.multi_cell(w - 2.4, line_h, cell, align="L")
            x_curr += w
        pdf.set_xy(pdf.l_margin, y_start + row_h)
    pdf.ln(3)


def _findings_and_recommendations(
    etl_result: ETLResult,
    summary: dict[str, Any],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Build verified 5 Findings and 5 Recommendations shared across report and README."""
    overall = summary["overall"]
    comms = summary["commodities"]
    counties = summary["counties"]
    groups = summary["group_comparison"]
    sw = summary["seasonal_by_window"]

    top3_12m = sorted(counties, key=lambda c: c["rank_12m"])[:3]
    top2_gap = sorted(counties, key=lambda c: c["gap_maize_kes"], reverse=True)[:2]
    cheapest_gap = min(counties, key=lambda c: c["gap_maize_kes"])
    asal_maize_diff = (
        groups["Arid & Semi-Arid (ASAL)"]["commodities"]["maize_fao"]["avg_price"]
        - groups["Agricultural & Urban"]["commodities"]["maize_fao"]["avg_price"]
    )

    findings = [
        (
            "Finding 1 (Q1): Regional YoY Food Price Resurgence",
            f"While annual index averages show the decline from the 2023 livestock price peak (2023 mean 3.465 vs. 1.744 in 2025), 12-month National Food Price Index inflation ({overall['recent_12m_start']} to {overall['recent_12m_end']}) rose {overall['yoy_inflation_recent_12m'] * 100:.2f}%. Tharaka Nithi (+25.13%), Marsabit (+19.85%), and Kisumu (+18.43%) recorded the largest county increases (Page 1 Top 10 YoY Bar Chart, [YoY Inflation %]).",
        ),
        (
            "Finding 2 (Q2): Composite Index Co-Moves With Goats Over Staples",
            f"Although the source components label assigns Goat (1 head) weight 0, monthly closing prices for Goat (1 head) explain {comms['livestock_goat_s_fao']['r2_with_food_index'] * 100:.2f}% of c_food_price_index variance across 55,454 physical market-months (r = {comms['livestock_goat_s_fao']['corr_with_food_index']:.5f}), versus {comms['beans']['r2_with_food_index'] * 100:.2f}% for Beans and {comms['maize_fao']['r2_with_food_index'] * 100:.2f}% for Maize. Over the latest 12 months, Maize fell {abs(comms['maize_fao']['yoy_inflation_12m'] * 100):.2f}% (to 80.13 KES/kg) while Goats rose {comms['livestock_goat_s_fao']['yoy_inflation_12m'] * 100:.2f}% (to 5,438.29 KES/head) (Page 1 Commodity Matrix, [Commodity YoY Inflation %]).",
        ),
        (
            "Finding 3 (Q3): Structural ASAL Maize Price Premium and Dispersion",
            f"ASAL markets (202 markets in 16 counties) show higher CV on the Food Index ({groups['Arid & Semi-Arid (ASAL)']['food_index_cv'] * 100:.2f}% vs. {groups['Agricultural & Urban']['food_index_cv'] * 100:.2f}%), Maize (40.21% vs. 38.52%), and Goats (85.64% vs. 78.82%), higher outlier rates (1.14% vs. 1.03%), and +{asal_maize_diff:.2f} KES/kg higher maize prices than Agricultural & Urban markets (31 markets), while Beans CV is slightly lower in ASAL (30.82% vs. 31.89%). Relative to the national mean (56.02 KES/kg), {top2_gap[0]['county']} (+{top2_gap[0]['gap_maize_kes']:.2f} KES/kg) and {top2_gap[1]['county']} (+{top2_gap[1]['gap_maize_kes']:.2f} KES/kg) carry the largest maize premiums, compared to {cheapest_gap['county']} ({cheapest_gap['gap_maize_kes']:.2f} KES/kg) (Page 2 Gap Bar Chart & Grouped Bars, [Affordability Gap (KES)]).",
        ),
        (
            "Finding 4 (Q4): Inverse Crop vs. Livestock Seasonal Price Cycles",
            f"Staple crops and livestock follow inverse annual cycles across 238 months. Maize ({sw['maize_fao']['Cool Dry / Harvest (Jun-Sep)']:.3f}) and Beans ({sw['beans']['Cool Dry / Harvest (Jun-Sep)']:.3f}) reach seasonal highs during Cool Dry / Harvest (Jun-Sep) as prior-season stocks tighten before main harvests and hit annual lows during Hot Dry / Lean (Jan-Feb) (0.972 and 0.970), when Goat prices peak at {sw['livestock_goat_s_fao']['Hot Dry / Lean (Jan-Feb)']:.3f} before falling to {sw['livestock_goat_s_fao']['Cool Dry / Harvest (Jun-Sep)']:.3f} in Jun-Sep (Page 3 Seasonal Cycle, [Seasonal Index]).",
        ),
        (
            "Finding 5 (Q5): Uneven County Coverage and High-Risk Field Survey Gaps",
            f"Modeled OHLC series populate 100.00% of the 233 x 238 x 3 grid ({etl_result.qa_metrics['fact_prices_rows']:,} rows), yet raw field surveys cover {overall['survey_coverage_rate_pct'] * 100:.2f}% of records and omit Western Province (27 of 47 counties covered). Five counties rely on one market, while Samburu (20 markets, 0.00% survey coverage), Kisumu (0.00% coverage, +18.43% YoY on Page 1), and Garissa (21 markets, 3.85% all-commodity coverage on the sub-5% bar chart) fall in the blind-spot quadrant (Page 4 Priority Quadrant & Low-Survey Bar Chart, [Survey Coverage Rate %]).",
        ),
    ]

    recommendations = [
        (
            "Recommendation 1: Decouple Grain Price Tracking From the Composite Index",
            "County food-security dashboards should alert on commodity-specific [Commodity YoY Inflation %] and [Avg Price (KES)] for Maize (1 kg) and Beans (1 kg) alongside [National Food Price Index], because raw index shifts reflect 99.99% co-movement with Goat (1 head) prices.",
        ),
        (
            "Recommendation 2: Deploy Field Price Audits to Zero-Survey High-Risk Counties",
            "Assign county agricultural enumerators first to Samburu (20 markets, 0.00% raw survey coverage), Kisumu (0.00% coverage, +18.43% YoY), and large northern ASAL clusters (Turkana at 1.96%, Marsabit at 3.00%, and Garissa at 3.85%) to raise [Survey Coverage Rate %] above the 5% blind-spot threshold.",
        ),
        (
            "Recommendation 3: Pre-Position Grain Buffers Ahead of June-to-September Peaks",
            "Trigger county maize and bean strategic reserve releases in May before the Cool Dry / Harvest (Jun-Sep) seasonal price peak (1.023 maize index, 1.013 beans index), and schedule livestock offtake or pastoral support for Jan-Feb (1.060 goat peak).",
        ),
        (
            "Recommendation 4: Target Staple Grain Logistics Using Affordability Gaps",
            "Direct maize transport and price-stabilization support toward chronic high-price counties with the largest positive [Affordability Gap (KES)], including Turkana (+15.26 KES/kg), Mandera (+10.65 KES/kg), and Kisumu (+9.89 KES/kg), and build trade links with nearby lower-price agricultural markets such as Kitui (-15.59 KES/kg).",
        ),
        (
            "Recommendation 5: Expand Market Coverage to Unmonitored Counties",
            "Partner with the Kenya National Bureau of Statistics (KNBS) and county trade offices to add physical monitoring sites across the 20 unrepresented counties (including Western Province) and single-market counties (Embu, Lamu, Machakos, Nyeri, Uasin Gishu) so future World Bank RTFP releases cover all 47 Kenyan counties.",
        ),
    ]

    _ = top3_12m
    return findings, recommendations


def _save_step_visual(
    img: Image.Image,
    filename: str,
    screenshots_dir: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Save 300 DPI step screenshot to screenshots/ and copy to output/."""
    s_dir = screenshots_dir or SCREENSHOTS_DIR
    o_dir = output_dir or OUTPUT_DIR
    s_dir.mkdir(parents=True, exist_ok=True)
    o_dir.mkdir(parents=True, exist_ok=True)
    target = s_dir / filename
    img.save(target, format="PNG", dpi=(300, 300))
    shutil.copy2(target, o_dir / filename)
    return target


def render_week2_cleaning_screenshot(
    etl_result: ETLResult,
    screenshots_dir: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Render 300 DPI visual audit of Week 2 Power Query transformations and QA metrics."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_CANVAS)
    draw = ImageDraw.Draw(img)
    fonts = _fonts_bundle()
    qa = etl_result.qa_metrics

    draw.rectangle([0, 0, CANVAS_W, 102], fill=NAVY)
    draw.text(
        (40, 16),
        "MZIGO CHAKULA | Week 2: Power Query M Data Cleaning & QA Audit (Steps T1 to T10)",
        font=fonts["title"],
        fill="#FFFFFF",
    )
    draw.text(
        (40, 62),
        "Source: KEN_RTFP_mkt_2007_2026-10-05.csv -> powerquery/*.pq -> 166,362 verified fact_prices rows",
        font=fonts["sub"],
        fill="#BAE6FD",
    )

    kpis = [
        ("Raw CSV Grain", f"{qa['raw_rows']:,} x 46", "233 physical markets + 1 avg series", COLOR_BLUE),
        ("Physical Market Grid", f"{qa['physical_market_rows']:,} rows", "238 Market Average rows excluded", COLOR_AGRI),
        ("Long Fact Output", f"{qa['fact_prices_rows']:,} rows", "55,454 market-months x 3 staples", NAVY),
        ("Outliers Flagged (T9)", f"{qa['outlier_rows']:,} (1.12%)", "Retained with is_outlier = TRUE", COLOR_ASAL),
    ]
    kx = 40
    for lbl, val, foot, acc in kpis:
        _draw_kpi_card(draw, (kx, 122, kx + 565, 290), lbl, val, foot, acc, fonts)
        kx += 585

    p_steps = _draw_panel(
        draw,
        (40, 312, 1450, 1310),
        "Reproducible Power Query M Transformation Log (T1 to T10)",
        "Implemented with QuoteStyle.Csv & en-US locale parity in powerquery/*.pq and Python",
        fonts,
    )
    step_headers = [
        ("Step", 72, "l"),
        ("M Transformation Scope", 360, "l"),
        ("Verified QA Outcome", 930, "l"),
    ]
    step_rows = [
        ["T1", "Parse dates & integer key", "238 valid dates (20070101..20261001), 0 parse nulls"],
        ["T2", "Calendar & Kenya seasons", "100% populated month_name, quarter, and 4 crop seasons"],
        ["T3", "Exclude aggregate rows", "Removed 238 Market Average rows; 0 missing coordinates"],
        ["T4", "Normalize 35 admin pairs", "233 markets mapped to 27 counties (16 ASAL / 11 Agri)"],
        ["T5", "Unpivot wide commodity OHLC", "55,454 physical market-months -> 166,362 long fact rows"],
        ["T6", "Clean commodity names", "Standardized Beans (1 kg), Maize (1 kg), Goat (1 head)"],
        ["T7", "Assign categories & units", "KG vs Head unit tags prevent summing mixed cereal & livestock"],
        ["T8", "Compute MoM price change", "165,663 lag deltas computed inside (mkt, item) series"],
        ["T9", "Flag statistical outliers", "1,866 spikes flagged (|MoM%| > 50 or |z| > 3), 0 dropped"],
        ["T10", "Mark recency windows", "Flagged 12 recent months and 36 trailing 3-year months"],
    ]
    _draw_table(draw, p_steps, step_headers, step_rows, fonts)

    p_qa = _draw_panel(
        draw,
        (1474, 312, 2360, 790),
        "Before vs. After Quality & Integrity Audit",
        "Automated pytest checks confirm zero key or coordinate defects",
        fonts,
    )
    qa_headers = [
        ("Audit Dimension", 355, "l"),
        ("Before ETL", 225, "l"),
        ("After Week 2 M", 260, "l"),
    ]
    qa_rows = [
        ["Primary Key Duplicates", "Unindexed CSV", "0 / 0 / 0 / 0 dupes"],
        ["Foreign Key Orphans", "Flat file", "0 across 166,362 rows"],
        ["Missing Coordinates", "238 rows null", "0 missing lat/lon"],
        ["Prices <= 0 KES", "Unchecked", "0 non-positive values"],
        ["ASAL / Agri Assignment", "Mixed provinces", "202 ASAL / 31 Agri mkts"],
    ]
    _draw_table(draw, p_qa, qa_headers, qa_rows, fonts)

    p_out = _draw_panel(
        draw,
        (1474, 812, 2360, 1310),
        "Outlier Flags by Commodity & County Group",
        "Market shock rows retained for historical audit",
        fonts,
    )
    cb = qa["commodity_breakdown"]
    gb = qa["county_group_breakdown"]
    out_items = [
        ("Goat (1 head)", float(cb["livestock_goat_s_fao"]["outlier_rows"]), f"{cb['livestock_goat_s_fao']['outlier_rows']:,}", COLOR_BLUE),
        ("Beans (1 kg)", float(cb["beans"]["outlier_rows"]), f"{cb['beans']['outlier_rows']:,}", COLOR_AMBER),
        ("Maize (1 kg)", float(cb["maize_fao"]["outlier_rows"]), f"{cb['maize_fao']['outlier_rows']:,}", COLOR_AGRI),
        ("ASAL Group", float(gb["Arid & Semi-Arid (ASAL)"]["outlier_rows"]), f"{gb['Arid & Semi-Arid (ASAL)']['outlier_rows']:,} (1.14%)", COLOR_ASAL),
        ("Agri/Urban", float(gb["Agricultural & Urban"]["outlier_rows"]), f"{gb['Agricultural & Urban']['outlier_rows']:,} (1.03%)", COLOR_SLATE),
    ]
    _draw_hbar_chart(draw, p_out, out_items, 0.0, 2100.0, fonts)

    return _save_step_visual(img, "week2-powerquery-cleaning.png", screenshots_dir, output_dir)


def render_week3_dax_validation_screenshot(
    summary: dict[str, Any],
    screenshots_dir: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Render 300 DPI verification card for the 15 DAX measures and live Power BI check."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_CANVAS)
    draw = ImageDraw.Draw(img)
    fonts = _fonts_bundle()
    overall = summary["overall"]
    comms = summary["commodities"]
    sw = summary["seasonal_by_window"]

    draw.rectangle([0, 0, CANVAS_W, 102], fill=NAVY)
    draw.text(
        (40, 16),
        "MZIGO CHAKULA | Week 3: Validated 15-Measure DAX Engine & Live Model Verification",
        font=fonts["title"],
        fill="#FFFFFF",
    )
    draw.text(
        (40, 62),
        "fact_prices.tmdl | Gap-safe EDATE + TREATAS time intelligence | Verified on Power BI Desktop msmdsrv",
        font=fonts["sub"],
        fill="#BAE6FD",
    )

    kpis = [
        ("238m Composite Index", f"{overall['national_food_index_full']:.4f}", "Market-month SUMMARIZE(mkt, date)", COLOR_BLUE),
        ("Time Intelligence", "EDATE + TREATAS", "Zero DATEADD non-contiguous errors", COLOR_ASAL),
        ("Multi-Commodity Safety", "AVERAGEX(cid)", "Separates KG cereal & Head goats", COLOR_AGRI),
        ("Live Season Query", "12 Rows / 67ms", "Verified across 166,362 fact rows", NAVY),
    ]
    kx = 40
    for lbl, val, foot, acc in kpis:
        _draw_kpi_card(draw, (kx, 122, kx + 565, 290), lbl, val, foot, acc, fonts)
        kx += 585

    p_dax = _draw_panel(
        draw,
        (40, 312, 1380, 1310),
        "15 Validated DAX Measures Across 4 Display Folders",
        "Synchronized between fact_prices.tmdl, dax_validator.py, and live PBIR visuals",
        fonts,
    )
    d_headers = [
        ("#", 48, "r"),
        ("Measure Name", 340, "l"),
        ("Folder", 300, "l"),
        ("Key Pattern", 590, "l"),
    ]
    d_rows = []
    for m in DAX_MEASURES:
        compact = " ".join(m.dax_expression.split())
        snippet = compact[:52] + ("..." if len(compact) > 52 else "")
        d_rows.append([str(m.measure_number), m.name, m.display_folder.split(". ", 1)[-1], snippet])
    _draw_table(draw, p_dax, d_headers, d_rows, fonts)

    p_bench = _draw_panel(
        draw,
        (1404, 312, 2360, 770),
        "Verified Commodity Benchmarks (DAX vs Python)",
        "Exact match across all 3 tracked Kenyan staples",
        fonts,
    )
    b_headers = [
        ("Commodity", 210, "l"),
        ("Full Mean", 140, "r"),
        ("12m Mean", 140, "r"),
        ("12m YoY%", 135, "r"),
        ("CV %", 115, "r"),
        ("Index R^2", 145, "r"),
    ]
    b_rows = [
        [
            comms[s.commodity_id]["commodity_name"],
            f"{comms[s.commodity_id]['avg_price_kes']:,.2f}",
            f"{comms[s.commodity_id]['recent_12m_avg_kes']:,.2f}",
            f"{comms[s.commodity_id]['yoy_inflation_12m'] * 100:+.2f}%",
            f"{comms[s.commodity_id]['volatility_cv'] * 100:.2f}%",
            f"{comms[s.commodity_id]['r2_with_food_index'] * 100:.2f}%",
        ]
        for s in COMMODITY_SPECS
    ]
    _draw_table(draw, p_bench, b_headers, b_rows, fonts)

    p_seas = _draw_panel(
        draw,
        (1404, 792, 2360, 1310),
        "Non-Contiguous Cropping Season Verification",
        "EDATE MoM % and Seasonal Index evaluated by cropping window",
        fonts,
    )
    s_headers = [
        ("Cropping Season", 335, "l"),
        ("Beans Idx", 180, "r"),
        ("Maize Idx", 180, "r"),
        ("Goat Idx", 180, "r"),
    ]
    s_rows = [
        [
            season,
            f"{sw['beans'][season]:.3f}",
            f"{sw['maize_fao'][season]:.3f}",
            f"{sw['livestock_goat_s_fao'][season]:.3f}",
        ]
        for season in (
            "Hot Dry / Lean (Jan-Feb)",
            "Long Rains (Mar-May)",
            "Cool Dry / Harvest (Jun-Sep)",
            "Short Rains (Oct-Dec)",
        )
    ]
    _draw_table(draw, p_seas, s_headers, s_rows, fonts)

    return _save_step_visual(img, "week3-dax-validation.png", screenshots_dir, output_dir)


def build_final_report_markdown(etl_result: ETLResult, summary: dict[str, Any]) -> str:
    """Build Markdown companion for docs/report.md in plain human prose."""
    overall = summary["overall"]
    comms = summary["commodities"]
    qa = etl_result.qa_metrics
    findings, recommendations = _findings_and_recommendations(etl_result, summary)

    lines: list[str] = [
        "# Mzigo Chakula: Kenya Food Price Inflation and Household Affordability (2007 to 2026)",
        "",
        "**Course:** DSA 3050A | Business Intelligence and Data Visualization (Group Project B)",
        "**Authors:** Prince Nzamuwe, Yizere Denis Derick",
        "**Date:** 17 November 2026",
        "**Full Report:** [docs/report.pdf](docs/report.pdf) (12-page technical report)",
        "",
        "## Executive Summary",
        "",
        (
            f"This report summarizes a Microsoft Power BI and Python analysis of "
            f"{qa['raw_rows']:,} raw monthly market rows ({qa['physical_market_rows']:,} physical market-months expanded "
            f"to {qa['fact_prices_rows']:,} commodity observations) across {qa['dim_markets_rows']} Kenyan markets, 27 counties, "
            f"and 238 consecutive months (`2007-01-01` to `2026-10-01`). Over the latest 12 months "
            f"(`{overall['recent_12m_start']}` to `{overall['recent_12m_end']}`), the National Food Price Index "
            f"(deduplicated at the market-month grain) rose {overall['yoy_inflation_recent_12m'] * 100:.2f}% year over year "
            f"to {overall['national_food_index_recent_12m']:.2f} against a 238-month mean of {overall['national_food_index_full']:.2f}, "
            "led by Tharaka Nithi (+25.13%), Marsabit (+19.85%), and Kisumu (+18.43%)."
        ),
        "",
        "## Five Evidence-Backed Findings",
        "",
    ]
    for title, body in findings:
        lines.append(f"- **{title}:** {body}")

    lines.extend(["", "## Five Stakeholder Recommendations", ""])
    for title, body in recommendations:
        lines.append(f"- **{title}:** {body}")

    lines.extend(
        [
            "",
            "## Summary Commodity Benchmarks",
            "",
            "| Commodity | Full Mean (KES) | 12m Mean (KES) | 12m YoY % | CV % | Correlation `r` vs. Index | R^2 vs. Index |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for spec in COMMODITY_SPECS:
        c = comms[spec.commodity_id]
        lines.append(
            f"| {c['commodity_name']} | {c['avg_price_kes']:,.2f} | {c['recent_12m_avg_kes']:,.2f} | "
            f"{c['yoy_inflation_12m'] * 100:+.2f}% | {c['volatility_cv'] * 100:.2f}% | "
            f"{c['corr_with_food_index']:.5f} | {c['r2_with_food_index'] * 100:.2f}% |"
        )

    lines.extend(
        [
            "",
            "## Workflow Step Evidence & Verification Screenshots",
            "",
            "| Stage | Visual Evidence | Scope Captured |",
            "| --- | --- | --- |",
            "| Week 1: Raw Import & Profiling | `screenshots/week1-initial-import.png` | Power Query raw 46-column CSV preview prior to transformations |",
            "| Week 2: Data Cleaning & QA | `screenshots/week2-powerquery-cleaning.png` | 10 Power Query M steps (`T1` to `T10`), zero orphan foreign keys, and 1,866 flagged outlier rows |",
            "| Week 3: Star Schema Diagram | `docs/model-diagram.png` | 4-table single-direction `1:*` schema with market-month index deduplication |",
            "| Week 3: Power BI Desktop Model View | `screenshots/week3-powerbi-model-view.png` | Live Power BI Desktop Model View with all 4 joined tables |",
            "| Week 3: DAX Verification Audit | `screenshots/week3-dax-validation.png` | 15 DAX measures using `EDATE` and `TREATAS` to handle missing months, plus commodity benchmarks |",
            "| Week 4: Dashboard Pages 1 to 4 | `screenshots/page1-executive-pulse.png`, `screenshots/page2-county-commodity.png`, `screenshots/page3-trends-diagnostics.png`, `screenshots/page4-decisions-action.png` | Power BI Desktop captures of all 4 report pages (46 visuals, custom theme, and top header page navigator) |",
            "",
            "## AI Assistance Disclosure and Data Authenticity Statement",
            "",
            (
                "All 55,692 raw records, market coordinates, and commodity price observations come directly from the World Bank "
                "Real Time Food Prices (RTFP) Kenya release (CC BY 4.0) without synthetic observations. AI coding and documentation "
                "tools assisted with Python validation scripting, Power Query M drafting, Tabular Model Definition Language (TMDL) packaging, "
                "report formatting, and slide generation. An automated pytest suite verifies ETL invariants, PBIR/TMDL bindings, "
                "and Python reference benchmarks against the raw CSV."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def render_final_report_pdf(
    etl_result: ETLResult,
    summary: dict[str, Any],
    output_path: Path,
    screenshots_dir: Path | None = None,
) -> Path:
    """Render a 12-page technical PDF report strictly within the 10-to-15-page brief range."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shots = screenshots_dir or SCREENSHOTS_DIR
    overall = summary["overall"]
    comms = summary["commodities"]
    counties = summary["counties"]
    groups = summary["group_comparison"]
    qa = etl_result.qa_metrics
    findings, recommendations = _findings_and_recommendations(etl_result, summary)

    pdf = ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(15, 16, 15)
    pdf.alias_nb_pages()

    # PAGE 1: Cover Header, Executive Summary, Problem Statement
    pdf.add_page()
    pdf.set_fill_color(15, 41, 66)
    pdf.rect(0, 0, 210, 48, style="F")
    pdf.set_xy(15, 11)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.multi_cell(
        180,
        8,
        "Mzigo Chakula: Kenya Food Price Inflation and Household Affordability (2007 to 2026)",
    )
    pdf.set_xy(15, 34)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(191, 219, 254)
    pdf.cell(
        180,
        5,
        "DSA 3050A | Business Intelligence & Data Visualization | Group Project B (Theme 10) | 17 November 2026",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_xy(15, 40)
    pdf.cell(180, 5, "Authors: Prince Nzamuwe, Yizere Denis Derick")
    pdf.set_y(56)

    _pdf_heading(pdf, "1. Executive Summary")
    _pdf_body(
        pdf,
        f"National food inflation statistics in Kenya report one aggregate rate and hide wide price gaps between northern arid counties, highland farm zones, and urban wholesale centers. Mzigo Chakula is a Microsoft Power BI report covering {qa['dim_markets_rows']} physical Kenyan markets across 27 counties and {qa['dim_date_rows']} consecutive months from January 2007 to October 2026 ({qa['fact_prices_rows']:,} cleaned market-month-commodity records).",
    )
    _pdf_body(
        pdf,
        f"Across the latest 12 months ({overall['recent_12m_start']} to {overall['recent_12m_end']}), the National Food Price Index (deduplicated at the market-month grain) rose {overall['yoy_inflation_recent_12m'] * 100:.2f}% year over year to {overall['national_food_index_recent_12m']:.2f} (238-month mean: {overall['national_food_index_full']:.2f}), led by Tharaka Nithi (+25.13%), Marsabit (+19.85%), Kisumu (+18.43%), and Nakuru (+17.52%). Individual commodity prices diverged: Maize fell 10.51% YoY to 80.13 KES/kg while Beans rose 0.55% (150.42 KES/kg) and Goats rose 7.77% (5,438.29 KES/head). ASAL counties also carry an average +9.75 KES/kg maize price premium above Agricultural & Urban counties alongside raw survey blind spots.",
    )

    _pdf_heading(pdf, "2. Problem Context & Project Scope")
    _pdf_body(
        pdf,
        "County agricultural officers, humanitarian NGOs, and household policy analysts need granular geographic and seasonal visibility into staple food costs. Treating Turkana, Mombasa, and Nyeri with uniform national timing causes delayed subsidies in northern deficit corridors and overlooks localized market instability. This report answers five questions across four interactive pages backed by ten Power Query steps and fifteen DAX measures.",
    )
    _pdf_table(
        pdf,
        ["Project Milestone", "Scope Delivered", "Verification Artifact"],
        [
            ["Week 1: Framing & Profiling", "55,692 raw rows & 46 columns audited; 3-page proposal + raw Power BI screenshot", "docs/proposal.pdf, docs/dataset-dictionary.csv"],
            ["Week 2: Power Query & QA", "10 M steps (T1 to T10); 166,362 fact rows; 0 duplicate PKs & 0 orphan FKs", "powerquery/*.pq, docs/transformation-log.md"],
            ["Week 3: Star Schema & DAX", "4 tables (233 mkts, 238 dates, 3 items); 3 single-dir 1:* joins; 15 DAX measures", "pbip/mzigo-chakula.pbip, docs/dax-catalogue.md"],
            ["Week 4: Dashboard & Insights", "4 report pages, 46 PBIR visuals, native page navigation, 300 DPI PNGs", "pbip/mzigo-chakula.Report/, 4 PNGs in screenshots/"],
            ["Week 5: Final Report & Defense", "12-page PDF report with workflow & Desktop screenshots, 12-slide PPTX, README", "docs/report.pdf, slides/presentation.pptx"],
        ],
        [45, 78, 57],
        font_size=7.9,
    )

    # PAGE 2: Stakeholders, Decisions, Questions, KPIs
    pdf.add_page()
    _pdf_heading(pdf, "3. Target Stakeholders and Supported Business Decisions")
    _pdf_table(
        pdf,
        ["Decision Domain", "Operational Choice Supported", "Primary Dashboard Signals Used"],
        [
            ["1. Monitoring Deployment", "Where to prioritize field market price enumerators and verification audits", "Low Survey Coverage Rate % (<5%) combined with high Maize Volatility CV % (>38%) on Page 4"],
            ["2. Seasonal Subsidy Timing", "When to release county buffer stocks or cash transfers ahead of price peaks", "Calendar-month & agricultural season Seasonal Index peaking Jun-Sep (crops) and Jan-Feb (goats)"],
            ["3. Commodity Targeting", "Which specific staple needs intervention independent of composite basket bias", "Per-commodity Avg Price (KES), Commodity YoY Inflation %, and Maize Affordability Gap (KES)"],
        ],
        [44, 66, 70],
        font_size=8.2,
    )

    _pdf_heading(pdf, "4. Five Analytical Questions and Five Defined KPIs")
    _pdf_body(
        pdf,
        "1. Which Kenyan counties experienced the highest 12-month food price inflation over the last three years (2024 to 2026)?\n"
        "2. Which tracked commodity (maize, beans, or goats) drives the largest share of movements in the composite food price index?\n"
        "3. Is monthly price volatility higher in arid and semi-arid counties than in agricultural or urban counties?\n"
        "4. What seasonal price cycles repeat across the year, and how do peak months differ between staples and livestock?\n"
        "5. How uneven is market coverage across counties, and where are survey blind spots concentrated?",
    )
    _pdf_table(
        pdf,
        ["KPI Name", "DAX Calculation Basis", "Full Span Value", "Recent 12m / Key Benchmark"],
        [
            ["National Food Price Index", "AVERAGEX(SUMMARIZE(fact_prices, mkt_id, date_key), AVERAGE(food_price_index))", f"{overall['national_food_index_full']:.4f}", f"{overall['national_food_index_recent_12m']:.4f}"],
            ["YoY Inflation %", "(CurrentIdx - EDATE(12m) PriorIdx) / PriorIdx", "Varies by year", f"{overall['yoy_inflation_recent_12m'] * 100:+.2f}%"],
            ["Price Volatility (KES / CV %)", "STDEV.S(price_value) and AVERAGEX CV per commodity", "Maize CV 40.56%", "ASAL Maize CV 40.21%"],
            ["Data Completeness / Survey %", "Observed/Expected grid; COUNT(raw_spot_price)/COUNTROWS", f"{overall['data_completeness_pct'] * 100:.2f}% / {overall['survey_coverage_rate_pct'] * 100:.2f}%", "4.49% field survey share"],
            ["Affordability Gap (KES)", "AVERAGEX per commodity: Local Avg - ALL(dim_markets) Avg", "Maize 56.02 baseline", "Turkana +15.26 KES/kg"],
        ],
        [45, 72, 31, 32],
        font_size=7.9,
    )

    # PAGE 3: Data Provenance, Quality Profile & Week 1 Import
    pdf.add_page()
    _pdf_heading(pdf, "5. Dataset Provenance and Initial Quality Profile")
    _pdf_table(
        pdf,
        ["Attribute", "Verified Specification"],
        [
            ["Source & Publisher", "World Bank Real Time Food Prices (RTFP), Kenya (https://microdata.worldbank.org/index.php/catalog/6167)"],
            ["Date Accessed & License", "29 October 2026 | Creative Commons Attribution 4.0 (CC BY 4.0)"],
            ["Raw Shape & Date Span", "55,692 rows x 46 columns | 238 continuous monthly dates (2007-01-01 to 2026-10-01)"],
            ["Physical Coverage", "233 physical markets (+ 1 synthetic Market Average series) across 27 counties and 7 regions"],
            ["Key Audit Findings", "(1) 238 Market Average rows lack lat/lon; (2) 35 raw (adm1, adm2) pairs mix provinces & counties; (3) Raw survey spot cols are 94.5% to 96.7% null vs. 0.00% null on modeled OHLC series; (4) Inflation cols blank in 2007 baseline year"],
        ],
        [45, 135],
        font_size=8.1,
    )
    import_shot = shots / "week1-initial-import.png"
    if not import_shot.is_file():
        import_shot = SCREENSHOTS_DIR / "week1-initial-import.png"
    if import_shot.is_file():
        _pdf_subheading(pdf, "Week 1 Raw CSV Import Evidence (Power Query Editor, Before Cleaning)")
        pdf.image(str(import_shot), x=20, y=pdf.get_y(), w=170)

    # PAGE 4: Week 2 Power Query & QA Summary + Step 2 Visual
    pdf.add_page()
    _pdf_heading(pdf, "6. Power Query Data Preparation (10 Transformations) and QA Audit")
    _pdf_body(
        pdf,
        "All data cleaning steps were implemented as repeatable Power Query M scripts under powerquery/ and cross-verified in Python (src/mzigo_chakula/etl.py) so every model refresh reproduces identical tables.",
    )
    _pdf_table(
        pdf,
        ["Step", "Transformation", "M Operation & Justification", "Verification Outcome"],
        [
            ["T1", "Parse price_date & date_key", "TransformColumnTypes ('en-US') + Int64 YYYYMMDD key", "238 valid Date rows (20070101..20261001)"],
            ["T2", "Calendar & Kenya Seasons", "Date.ToText, QuarterOfYear, 4 Kenya agricultural windows", "100% populated month_name, quarter, season"],
            ["T3", "Exclude Market Average", "SelectRows excluding gid_ken_national_average & empty rows", "55,692 -> 55,454 physical rows; 0 null lat/lon"],
            ["T4", "Normalize 35 Admin Pairs", "NestedJoin lookup + Kitengela override + ASAL list", "233 mkts -> 27 counties (16 ASAL, 11 Agri/Urban)"],
            ["T5", "Unpivot Commodity OHLC", "ProjectCommodity + Table.Combine across 3 items", "55,454 wide -> 166,362 long fact rows"],
            ["T6", "Clean Commodity Names", "Standardize codes to Beans (1 kg), Maize (1 kg), Goat (1 head)", "3 immutable keys linked to dim_commodity"],
            ["T7", "Add Categories & Units", "Assign Legume Staple / Cereal Staple / Livestock & KG / Head", "Prevents mixing kg grain & per-head goat units"],
            ["T8", "Compute MoM Price Change", "Group by (mkt_id, commodity_id), sort date_key, List.Buffer lag", "165,663 valid MoM rows (699 Jan-2007 nulls)"],
            ["T9", "Flag Statistical Outliers", "Flag |MoM%| > 50 or |z-score| > 3 without dropping months", "1,866 spikes flagged (1.12%), 0 prices <= 0"],
            ["T10", "Add Recency Filter Flags", "Boolean is_recent (last 12m) and is_last_36m on dim_date", "12 recent months & 36 3-year months flagged"],
        ],
        [12, 40, 68, 60],
        font_size=7.4,
    )
    _pdf_table(
        pdf,
        ["QA Integrity Check", "Before Cleaning", "After Week 2 ETL", "Status"],
        [
            ["Primary Key Duplicates (all 4 tables)", "Flat unindexed CSV", "0 / 0 / 0 / 0 duplicates", "Pass"],
            ["Foreign Key Orphans (mkt_id / date_key / commodity_id)", "N/A (single flat table)", "0 / 0 / 0 orphans across 166,362 rows", "Pass"],
            ["Commodity Outlier Distribution", "Unflagged spikes", "Goat 1,766 | Beans 97 | Maize 3 (ASAL 1,638 vs Agri 228)", "Verified"],
        ],
        [68, 36, 58, 18],
        font_size=7.5,
    )
    clean_shot = shots / "week2-powerquery-cleaning.png"
    if not clean_shot.is_file():
        clean_shot = SCREENSHOTS_DIR / "week2-powerquery-cleaning.png"
    if clean_shot.is_file():
        _pdf_subheading(pdf, "Week 2 Power Query Transformation & Outlier Audit Summary")
        pdf.image(str(clean_shot), x=32, y=pdf.get_y(), w=146)

    # PAGE 5: Star Schema & Model Diagram
    pdf.add_page()
    _pdf_heading(pdf, "7. Star Schema Data Model and Grain Governance")
    _pdf_body(
        pdf,
        "The semantic model (pbip/mzigo-chakula.pbip, compatibility level 1606) separates descriptors from measurements using three dimension tables filtering a central fact table. All relationships are single-direction (Many-to-One) from dimension tables into fact_prices. Because raw c_food_price_index originates at the market-month level rather than the commodity level, [National Food Price Index] aggregates across distinct (mkt_id, date_key) pairs via SUMMARIZE so selecting multiple commodities never triple-counts the composite index.",
    )
    _pdf_table(
        pdf,
        ["Relationship", "Cardinality", "Cross-Filter Direction", "Integrity Check"],
        [
            ["fact_prices[mkt_id] -> dim_markets[mkt_id]", "Many to One (*:1)", "Single (dim_markets filters fact_prices)", "Active, 0 orphans"],
            ["fact_prices[date_key] -> dim_date[date_key]", "Many to One (*:1)", "Single (dim_date filters fact_prices; MarkAsDateTable)", "Active, 0 orphans"],
            ["fact_prices[commodity_id] -> dim_commodity[commodity_id]", "Many to One (*:1)", "Single (dim_commodity filters fact_prices)", "Active, 0 orphans"],
        ],
        [65, 32, 53, 30],
        font_size=7.7,
    )
    diag_path = DOCS_DIR / "model-diagram.png"
    if diag_path.is_file():
        _pdf_subheading(pdf, "Star Schema Architecture Diagram")
        pdf.image(str(diag_path), x=20, y=pdf.get_y() + 1, w=170)

    # PAGE 6: Live Power BI Desktop Model View & DAX Verification Visual
    pdf.add_page()
    _pdf_heading(pdf, "8. Live Power BI Desktop Verification (Model View & DAX Validation)")
    _pdf_body(
        pdf,
        "After importing all Power Query M partitions into Power BI Desktop (2.159.1231.0), live validation confirmed 166,362 rows loaded and all 15 measures evaluate without DATEADD errors on non-contiguous groupings (such as season and month_name).",
        size=8.8,
    )
    pbi_model_shot = shots / "week3-powerbi-model-view.png"
    if not pbi_model_shot.is_file():
        pbi_model_shot = SCREENSHOTS_DIR / "week3-powerbi-model-view.png"
    if pbi_model_shot.is_file():
        _pdf_subheading(pdf, "Power BI Desktop Live Model View (4 Joined Tables & Date Table Marker)")
        pdf.image(str(pbi_model_shot), x=26, y=pdf.get_y(), w=158)
        pdf.set_y(pdf.get_y() + 101)

    dax_val_shot = shots / "week3-dax-validation.png"
    if not dax_val_shot.is_file():
        dax_val_shot = SCREENSHOTS_DIR / "week3-dax-validation.png"
    if dax_val_shot.is_file():
        _pdf_subheading(pdf, "DAX Measure Engine Verification & Commodity Benchmark Audit")
        pdf.image(str(dax_val_shot), x=26, y=pdf.get_y(), w=158)

    # PAGE 7: DAX Measures & Benchmarks
    pdf.add_page()
    _pdf_heading(pdf, "9. Validated DAX Measure Catalogue (15 Measures) & Benchmarks")
    _pdf_table(
        pdf,
        ["#", "Measure Name", "Display Folder", "Simplified DAX Logic & Purpose"],
        [
            [
                str(spec.measure_number),
                spec.name,
                spec.display_folder,
                " ".join(spec.dax_expression.split())[:96]
                + ("..." if len(" ".join(spec.dax_expression.split())) > 96 else ""),
            ]
            for spec in DAX_MEASURES
        ],
        [9, 44, 42, 85],
        font_size=7.4,
    )
    _pdf_subheading(pdf, "Commodity Validation Benchmarks Against Python Reference Engine")
    _pdf_table(
        pdf,
        ["Commodity", "Full Avg (KES)", "12m Avg (KES)", "12m YoY %", "Oct MoM %", "CV %", "12m Roll Avg", "Index R^2"],
        [
            [
                comms[s.commodity_id]["commodity_name"],
                f"{comms[s.commodity_id]['avg_price_kes']:,.2f}",
                f"{comms[s.commodity_id]['recent_12m_avg_kes']:,.2f}",
                f"{comms[s.commodity_id]['yoy_inflation_12m'] * 100:+.2f}%",
                f"{comms[s.commodity_id]['latest_mom_pct'] * 100:+.2f}%",
                f"{comms[s.commodity_id]['volatility_cv'] * 100:.2f}%",
                f"{comms[s.commodity_id]['rolling_12m_avg_kes']:,.2f}",
                f"{comms[s.commodity_id]['r2_with_food_index'] * 100:.2f}%",
            ]
            for s in COMMODITY_SPECS
        ],
        [28, 22, 22, 20, 20, 18, 25, 25],
        font_size=7.8,
    )

    # PAGE 8: Dashboard Pages 1 & 2 Walkthrough
    pdf.add_page()
    _pdf_heading(pdf, "10. Interactive Dashboard Design: Pages 1 and 2")
    _pdf_body(
        pdf,
        "Page 1 (Executive Pulse) provides a national and county overview with top header page navigation (Ctrl + Click in Power BI Desktop; single-click in Power BI Service), 5 dropdown slicers, 5 KPI cards (1.88 recent index, 7.56% YoY, 1.92 YTD mean, 100.00% completeness, 4.49% survey coverage), the 238-month National Food Price Index trend, all 10 Top Counties by Recent 12m YoY Inflation, the full-width Commodity Matrix, and the full 10-row County Watchlist.",
        size=8.8,
    )
    p1 = SCREENSHOTS_DIR / "page1-executive-pulse.png"
    if p1.is_file():
        pdf.image(str(p1), x=28, y=pdf.get_y(), w=154)
        pdf.set_y(pdf.get_y() + 89)
    _pdf_body(
        pdf,
        "Page 2 (County & Commodity) compares county affordability gaps via Top 5 Deficit vs. Bottom 5 Surplus maize gap bars (+15.26 KES/kg in Turkana vs. -17.51 KES/kg in Lamu and -15.59 KES/kg in Kitui), 233-market Lon/Lat coordinate scatter map, ASAL vs. Agricultural/Urban CV% comparison, and a full-width County Maize Affordability table.",
        size=8.8,
    )
    p2 = SCREENSHOTS_DIR / "page2-county-commodity.png"
    if p2.is_file():
        pdf.image(str(p2), x=28, y=pdf.get_y(), w=154)

    # PAGE 9: Dashboard Pages 3 & 4 Walkthrough
    pdf.add_page()
    _pdf_heading(pdf, "11. Interactive Dashboard Design: Pages 3 and 4")
    _pdf_body(
        pdf,
        "Page 3 (Trends & Diagnostics) tracks Beans and Maize monthly prices from 2007 to 2026 (with 12m Rolling Avg, MoM %, and StdDev hover tooltips), plots the repeating Jan-to-Dec Seasonal Index cycle curves, ranks all 10 Top counties by Maize CV %, and summarizes Cropping Window seasonal index bars.",
        size=8.8,
    )
    p3 = SCREENSHOTS_DIR / "page3-trends-diagnostics.png"
    if p3.is_file():
        pdf.image(str(p3), x=28, y=pdf.get_y(), w=154)
        pdf.set_y(pdf.get_y() + 89)
    _pdf_body(
        pdf,
        "Page 4 (Decisions & Action) maps all 27 counties onto a Monitoring Priority Quadrant (Maize Survey % vs. Maize CV %, where Maize zero-survey hubs plot at 0.00%), orders the full-width Maize Priority Action Matrix, isolates 10 low-survey counties below 5% across all commodities, and compares Average Maize Price (KES/kg) across 7 regions.",
        size=8.8,
    )
    p4 = SCREENSHOTS_DIR / "page4-decisions-action.png"
    if p4.is_file():
        pdf.image(str(p4), x=28, y=pdf.get_y(), w=154)

    # PAGE 10: Five Evidence-Backed Findings
    pdf.add_page()
    _pdf_heading(pdf, "12. Five Evidence-Backed Findings (Answering Q1 to Q5)")
    for title, body in findings:
        _pdf_subheading(pdf, title)
        _pdf_body(pdf, body, size=9.1)

    _pdf_subheading(pdf, "Regional Dispersion Benchmark: ASAL vs. Agricultural & Urban")
    _pdf_table(
        pdf,
        ["County Group", "Counties", "Markets", "Food Index CV %", "Maize CV %", "Beans CV %", "Goat CV %", "Outlier Rate"],
        [
            [
                g_name,
                str(qa["county_group_breakdown"][g_name]["counties"]),
                str(qa["county_group_breakdown"][g_name]["markets"]),
                f"{groups[g_name]['food_index_cv'] * 100:.2f}%",
                f"{groups[g_name]['commodities']['maize_fao']['volatility_cv'] * 100:.2f}%",
                f"{groups[g_name]['commodities']['beans']['volatility_cv'] * 100:.2f}%",
                f"{groups[g_name]['commodities']['livestock_goat_s_fao']['volatility_cv'] * 100:.2f}%",
                f"{groups[g_name]['outlier_rate'] * 100:.2f}%",
            ]
            for g_name in ("Arid & Semi-Arid (ASAL)", "Agricultural & Urban")
        ],
        [40, 18, 17, 27, 20, 20, 19, 19],
        font_size=7.9,
    )

    # PAGE 11: Five Stakeholder Recommendations
    pdf.add_page()
    _pdf_heading(pdf, "13. Five Stakeholder Recommendations Tied to Findings")
    for title, body in recommendations:
        _pdf_subheading(pdf, title)
        _pdf_body(pdf, body, size=9.2)

    _pdf_subheading(pdf, "Immediate Action Summary by County Type")
    top5_12m = sorted(counties, key=lambda c: c["rank_12m"])[:5]
    _pdf_table(
        pdf,
        ["County", "Region", "Markets", "12m YoY %", "Maize Gap (KES)", "Survey %", "Priority Lever"],
        [
            [
                c["county"],
                c["region"],
                str(c["markets"]),
                f"{c['yoy_12m'] * 100:+.2f}%",
                f"{c['gap_maize_kes']:+.2f}",
                f"{c['survey_coverage_rate'] * 100:.2f}%",
                "Audit + inflation tracking" if c["survey_coverage_rate"] < 0.05 else "Seasonal buffer monitoring",
            ]
            for c in top5_12m
        ],
        [28, 26, 15, 22, 26, 19, 44],
        font_size=8.0,
    )

    # PAGE 12: Limitations, Ethics, AI Disclosure, Contributors, References
    pdf.add_page()
    _pdf_heading(pdf, "14. Limitations, Ethics, and Academic Integrity")
    _pdf_body(
        pdf,
        "1. Retail Prices vs. Household Income: The dataset captures market selling prices without household earnings or expenditure weights; affordability pressure is inferred from cross-county price premiums and dispersion.\n"
        "2. Geographic Coverage Imbalance: Only 27 of 47 Kenyan counties appear in this release. Western Province has zero markets, five counties rely on one monitored market, and Turkana alone represents 57 of 233 markets.\n"
        "3. Composite Index Composition Bias: Raw c_food_price_index tracks unscaled livestock goat prices (r = 0.99996), so commodity-level filtering is mandatory when sizing cereal interventions.\n"
        "4. Open Data Ethics: All series are anonymized public aggregate market indicators distributed under CC BY 4.0 with zero personal or sensitive records.",
    )
    _pdf_heading(pdf, "15. AI Assistance Disclosure (Brief Section 10 Compliance)")
    _pdf_body(
        pdf,
        "All 55,692 raw observations, coordinates, and price values come directly from the World Bank Real Time Food Prices (RTFP) dataset with zero synthetic observations. AI assistant tooling supported Python profiling, test authoring, Power Query M drafting, Tabular Model Definition Language (TMDL) packaging, PDF/slide assembly, and prose copy editing under human review. An automated pytest suite verifies ETL invariants, PBIR/TMDL bindings, and Python reference benchmarks against the raw CSV.",
    )
    _pdf_heading(pdf, "16. Group Contributors & References")
    _pdf_table(
        pdf,
        ["Contributor", "Role", "Verified Responsibilities"],
        [
            ["Prince Nzamuwe", "Lead Analyst & BI Architect", "Dataset acquisition, Power Query M ETL, star schema model, DAX validation, dashboard design, report & defense"],
            ["Yizere Denis Derick", "Group Contributor", "Problem framing, stakeholder scoping, requirement alignment (lecturer notified of medical situation)"],
        ],
        [40, 42, 98],
        font_size=8.0,
    )
    _pdf_body(
        pdf,
        "References:\n"
        "- World Bank. (2026). Real Time Food Prices (RTFP), Kenya. Microdata Library (https://microdata.worldbank.org/index.php/catalog/6167). Retrieved 29 October 2026.\n"
        "- Kenya National Bureau of Statistics (KNBS). (2025). Consumer Price Index, Kenya.\n"
        "- Central Bank of Kenya (CBK). (2026). Monetary Policy Statement.",
        size=8.6,
    )

    output_path.write_bytes(bytes(pdf.output()))
    return output_path


def _add_slide_header(
    slide: Any,
    title: str,
    subtitle: str,
    slide_num: int,
    total_slides: int,
) -> None:
    """Apply consistent navy top header and bottom footer on content slides."""
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.08))
    bar.fill.solid()
    bar.fill.fore_color.rgb = PPTX_NAVY
    bar.line.fill.background()

    tf = bar.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.55)
    tf.margin_top = Inches(0.14)
    p1 = tf.paragraphs[0]
    p1.text = title
    p1.font.size = Pt(24)
    p1.font.bold = True
    p1.font.color.rgb = PPTX_WHITE

    p2 = tf.add_paragraph()
    p2.text = subtitle
    p2.font.size = Pt(13)
    p2.font.color.rgb = RGBColor(0xBA, 0xE6, 0xFD)

    footer = slide.shapes.add_textbox(Inches(0.55), Inches(7.08), Inches(12.2), Inches(0.32))
    ftf = footer.text_frame
    fp = ftf.paragraphs[0]
    fp.text = f"DSA 3050A Group Project B | Mzigo Chakula   |   Slide {slide_num} of {total_slides}"
    fp.font.size = Pt(11)
    fp.font.color.rgb = PPTX_MUTED


def _add_bullets_box(
    slide: Any,
    left: float,
    top: float,
    width: float,
    height: float,
    heading: str,
    bullets: list[str],
    accent: RGBColor = PPTX_BLUE,
    font_pt: int = 14,
) -> None:
    """Add bordered white content card with colored top accent strip and crisp bullets."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    card.fill.solid()
    card.fill.fore_color.rgb = PPTX_WHITE
    card.line.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)

    strip = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(0.08))
    strip.fill.solid()
    strip.fill.fore_color.rgb = accent
    strip.line.fill.background()

    tb = slide.shapes.add_textbox(Inches(left + 0.22), Inches(top + 0.16), Inches(width - 0.44), Inches(height - 0.28))
    tf = tb.text_frame
    tf.word_wrap = True
    p_hdr = tf.paragraphs[0]
    p_hdr.text = heading
    p_hdr.font.size = Pt(font_pt + 3)
    p_hdr.font.bold = True
    p_hdr.font.color.rgb = PPTX_NAVY
    p_hdr.space_after = Pt(8)

    for b in bullets:
        p = tf.add_paragraph()
        p.text = f"- {b}"
        p.font.size = Pt(font_pt)
        p.font.color.rgb = PPTX_DARK
        p.space_after = Pt(6)


def _set_speaker_notes(slide: Any, notes: str) -> None:
    slide.notes_slide.notes_text_frame.text = notes


def render_presentation_pptx(
    etl_result: ETLResult,
    summary: dict[str, Any],
    output_path: Path,
) -> Path:
    """Create 12-slide 16:9 PowerPoint presentation with speaker notes for live defence."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    total_slides = 12

    overall = summary["overall"]
    comms = summary["commodities"]
    qa = etl_result.qa_metrics

    # Slide 1: Cover Slide
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = PPTX_NAVY
    bg1.line.fill.background()

    tb1 = s1.shapes.add_textbox(Inches(0.9), Inches(1.75), Inches(11.5), Inches(3.8))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "MZIGO CHAKULA"
    p.font.size = Pt(46)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0x38, 0xBD, 0xF8)
    p2 = tf1.add_paragraph()
    p2.text = "Food Price Inflation and Household Affordability in Kenya (2007 to 2026)"
    p2.font.size = Pt(28)
    p2.font.bold = True
    p2.font.color.rgb = PPTX_WHITE
    p2.space_before = Pt(10)
    p3 = tf1.add_paragraph()
    p3.text = "DSA 3050A: Business Intelligence & Data Visualization | Group Project B (Theme 10)"
    p3.font.size = Pt(16)
    p3.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)
    p3.space_before = Pt(22)
    p4 = tf1.add_paragraph()
    p4.text = "Group Members: Prince Nzamuwe, Yizere Denis Derick   |   Date: 17 November 2026"
    p4.font.size = Pt(15)
    p4.font.color.rgb = RGBColor(0xBA, 0xE6, 0xFD)
    p4.space_before = Pt(8)
    _set_speaker_notes(s1, "Welcome assessors. Today we present Mzigo Chakula, a Microsoft Power BI report measuring Kenyan retail staple food costs across 233 physical markets and 27 counties from January 2007 to October 2026.")

    # Slide 2: Problem Context, Stakeholders, and 3 Decisions
    s2 = prs.slides.add_slide(blank_layout)
    _add_slide_header(s2, "Problem Statement, Stakeholders, and Three Decisions", "Why single national inflation rates fail regional food-security planning", 2, total_slides)
    _add_bullets_box(
        s2,
        0.55,
        1.35,
        6.0,
        5.4,
        "Real-World Problem & Intended Users",
        [
            "Headline national inflation hides wide sub-national dispersion across arid north, agricultural rift, and urban centers.",
            "Stakeholders: County agricultural planners, NGO food-security teams, and household policy analysts.",
            "5 Analytical Questions focus on 12m county inflation, commodity index drivers, ASAL volatility, seasonal cycles, and survey blind spots.",
        ],
        accent=PPTX_BLUE,
    )
    _add_bullets_box(
        s2,
        6.8,
        1.35,
        5.98,
        5.4,
        "Three Operational Decisions Supported",
        [
            "Decision 1 (Monitoring): Deploy price enumerators to counties pairing low raw survey coverage (<5%) with high maize volatility.",
            "Decision 2 (Timing): Release seasonal food reserves before Jun-Sep grain peaks and Jan-Feb goat peaks.",
            "Decision 3 (Commodities): Target ASAL maize corridors (+9.75 KES/kg premium) instead of relying on goat-heavy composite indices.",
        ],
        accent=PPTX_ORANGE,
    )
    _set_speaker_notes(s2, "Explain why Mzigo Chakula is built for county planners and NGOs rather than generic visualization: every table and measure directly answers one of three resource allocation decisions.")

    # Slide 3: Dataset Provenance & Profiling Audit
    s3 = prs.slides.add_slide(blank_layout)
    _add_slide_header(s3, "Dataset Provenance and Week 1 Profiling Audit", "World Bank RTFP Kenya release (CC BY 4.0) with four discovered data quirks", 3, total_slides)
    _add_bullets_box(
        s3,
        0.55,
        1.35,
        5.7,
        5.4,
        "Verified Source & Structural Audit",
        [
            "Source: World Bank RTFP Kenya (accessed 29 Oct 2026, CC BY 4.0).",
            "Volume: 55,692 raw rows x 46 columns spanning 238 months (2007-01 to 2026-10).",
            "Quirk 1: 238 Market Average aggregate rows lack coordinates.",
            "Quirk 2: 35 raw (adm1, adm2) pairs mix provinces and counties.",
            "Quirk 3: Raw spot survey cols 94.5% to 96.7% null vs. 0% null modeled OHLC prices.",
            "Quirk 4: Year-2007 YoY inflation cells are blank due to missing 2006 baseline.",
        ],
        accent=PPTX_TEAL,
        font_pt=13,
    )
    imp_img = SCREENSHOTS_DIR / "week1-initial-import.png"
    if imp_img.is_file():
        s3.shapes.add_picture(str(imp_img), Inches(6.45), Inches(1.45), width=Inches(6.3))
    _set_speaker_notes(s3, "Point to our Power Query initial import screenshot showing 46 columns and zero manual transformations applied yet. Profiling uncovered all four structural quirks.")

    # Slide 4: 10 Power Query Transformations & QA Integrity
    s4 = prs.slides.add_slide(blank_layout)
    _add_slide_header(s4, "Power Query Cleaning (T1 to T10) and Before/After QA", "Reproducible M pipelines producing 166,362 verified fact rows with zero orphan keys", 4, total_slides)
    _add_bullets_box(
        s4,
        0.55,
        1.35,
        6.0,
        5.4,
        "Ten Implemented M Transformations",
        [
            "T1-T2: Parse 'en-US' price_date -> Date, date_key, year, quarter, and 4 Kenya seasons.",
            "T3: Filter out 238 Market Average rows (55,454 physical market-months remain).",
            "T4: Reconcile all 35 admin pairs + Kitengela override into 27 counties & ASAL/Agri groups.",
            "T5-T7: Unpivot 3 commodities into long fact rows (166,362 rows) with KG/Head units.",
            "T8-T10: Compute within-series MoM%, flag 1,866 outliers (1.12%), add 12m/36m flags.",
        ],
        accent=PPTX_BLUE,
        font_pt=13,
    )
    _add_bullets_box(
        s4,
        6.8,
        1.35,
        5.98,
        5.4,
        "Verified Before/After QA Metrics",
        [
            f"Raw rows {qa['raw_rows']:,} -> Physical {qa['physical_market_rows']:,} -> Fact {qa['fact_prices_rows']:,}.",
            "Duplicate primary keys across all 4 tables: 0 / 0 / 0 / 0.",
            "Orphan foreign keys across 166,362 rows: 0 / 0 / 0.",
            "Null coordinates after cleaning: 0 (down from 238 Market Average pairs).",
            "Non-positive modeled close prices (<= 0 KES): 0 across all commodities.",
            "Verified by 44 automated pytest unit tests.",
        ],
        accent=PPTX_TEAL,
        font_pt=13,
    )
    _set_speaker_notes(s4, "Emphasize reproducibility: every M query sits under powerquery/*.pq with invariant parity verified in Python.")

    # Slide 5: Star Schema Data Model & Grain Protection
    s5 = prs.slides.add_slide(blank_layout)
    _add_slide_header(s5, "Star Schema Semantic Model and Grain Governance", "4 tables, single-direction 1:* relationships, official Date Table, and market-month deduplicated DAX", 5, total_slides)
    _add_bullets_box(
        s5,
        0.55,
        1.35,
        4.4,
        5.4,
        "Model Architecture Rules",
        [
            "All relationships are 1:* single-direction from dimensions into fact_prices.",
            "dim_date[full_date] marked as official Date Table; month_name sorted by month.",
            "Foreign keys hidden in Report View.",
            "Grain guard: SUMMARIZE(mkt_id, date_key) avoids 3x counting food_price_index.",
        ],
        accent=PPTX_TEAL,
        font_pt=13,
    )
    diag_img = DOCS_DIR / "model-diagram.png"
    if diag_img.is_file():
        s5.shapes.add_picture(str(diag_img), Inches(5.15), Inches(1.38), width=Inches(7.65))
    _set_speaker_notes(s5, "Highlight our grain protection pattern: unpivoting 3 commodities repeats market-month food_price_index 3 times, so SUMMARIZE enforces market-month distinct averaging.")

    # Slide 6: 15 DAX Measures & Validated Benchmarks
    s6 = prs.slides.add_slide(blank_layout)
    _add_slide_header(s6, "Validated 15-Measure DAX Catalogue and Benchmarks", "Time intelligence, county ranking, volatility CV, seasonality, and survey checks", 6, total_slides)
    _add_bullets_box(
        s6,
        0.55,
        1.35,
        5.7,
        5.4,
        "DAX Measure Suite (Organized in 4 Folders)",
        [
            "Core & Index: Avg Price (KES), National Food Price Index (market-month deduplicated).",
            "Time Intelligence: Gap-safe EDATE + TREATAS for YoY Inflation %, Commodity YoY %, MoM Change %, Cumulative YTD, 12m Roll Avg.",
            "Risk & Seasonality: STDEV.S Volatility KES, unit-safe AVERAGEX Volatility CV %, Seasonal Index.",
            "Disparities: RANKX County Inflation Rank, unit-safe Affordability Gap KES, Data Completeness %, Survey Coverage Rate %.",
        ],
        accent=PPTX_BLUE,
        font_pt=13,
    )
    _add_bullets_box(
        s6,
        6.5,
        1.35,
        6.28,
        5.4,
        "Verified Model Output Benchmarks",
        [
            f"Full-Span Index: {overall['national_food_index_full']:.4f} vs. Recent 12m: {overall['national_food_index_recent_12m']:.4f} (+{overall['yoy_inflation_recent_12m'] * 100:.2f}% YoY).",
            "Beans (1 kg): 105.69 full / 150.42 12m KES (+0.55% YoY, CV 31.02%).",
            "Maize (1 kg): 56.02 full / 80.13 12m KES (-10.51% YoY, CV 40.56%).",
            f"Goat (1 head): 3,456.14 full / 5,438.29 12m KES (+7.77% YoY, R^2 = {comms['livestock_goat_s_fao']['r2_with_food_index'] * 100:.2f}%).",
            f"Data Completeness: {overall['data_completeness_pct'] * 100:.2f}% | Field Survey Rate: {overall['survey_coverage_rate_pct'] * 100:.2f}%.",
        ],
        accent=PPTX_ORANGE,
        font_pt=13,
    )
    _set_speaker_notes(s6, "Walk through the gap-safe EDATE and TREATAS time-intelligence pattern (preventing non-contiguous date selection errors on seasons) and unit-safe AVERAGEX across commodities, which match Python benchmarks.")

    # Slides 7-10: Full Visual Showcase of the 4 Report Pages
    page_slides = [
        (7, "Page 1: Executive Pulse", "Top pageNavigator, recent 12m KPI cards, 238-month index trend, Top 10 YoY counties, and matrices", SCREENSHOTS_DIR / "page1-executive-pulse.png", "Remind assessors to use Ctrl + Click on the top header navigation pills in Power BI Desktop (single-click in Service), and highlight the 2023 index spike and recent +7.56% recovery led by Tharaka Nithi (+25.13%), Marsabit, and Kisumu."),
        (8, "Page 2: County and Commodity Disparities", "Top 5 Deficit vs. Bottom 5 Surplus maize gap bars, 233-market scatter, ASAL CV%, and county table", SCREENSHOTS_DIR / "page2-county-commodity.png", "Highlight the +9.75 KES/kg chronic maize price gap in ASAL markets like Turkana (+15.26 KES/kg) versus surplus zones like Kitui (-15.59 KES/kg) and Lamu (-17.51 KES/kg)."),
        (9, "Page 3: Trends, Seasonality, and Diagnostics", "2007 to 2026 Beans/Maize curves, Jan-Dec seasonality, Top 10 Maize CV%, and cropping window columns", SCREENSHOTS_DIR / "page3-trends-diagnostics.png", "Point out the inverse seasonal timing between Jun-Sep crop highs (1.023 maize) and Jan-Feb goat peaks (1.060)."),
        (10, "Page 4: Decisions and Action Playbook", "Survey % vs. Maize CV% blind-spot quadrant, priority matrix, sub-5% survey bars, and regional maize prices", SCREENSHOTS_DIR / "page4-decisions-action.png", "Walk assessors through the blind-spot quadrant: Samburu (20 markets, 0.00% raw survey coverage) and Kisumu (+18.43% YoY, 0.00% survey)."),
    ]
    for s_num, s_title, s_sub, img_path, notes in page_slides:
        sl = prs.slides.add_slide(blank_layout)
        _add_slide_header(sl, s_title, s_sub, s_num, total_slides)
        if img_path.is_file():
            sl.shapes.add_picture(str(img_path), Inches(1.15), Inches(1.22), width=Inches(11.03))
        _set_speaker_notes(sl, notes)

    # Slide 11: 5 Findings & 5 Recommendations
    s11 = prs.slides.add_slide(blank_layout)
    _add_slide_header(s11, "Five Evidence-Backed Findings and Five Recommendations", "Direct mapping from analytical questions to operational county interventions", 11, total_slides)
    _add_bullets_box(
        s11,
        0.55,
        1.35,
        6.0,
        5.4,
        "Key Verified Findings (Q1 to Q5)",
        [
            "F1: Recent 12m index inflation rose 7.56% (Tharaka Nithi +25.13%, Marsabit +19.85%).",
            "F2: Composite index moves 99.99% with Goat prices; Maize fell 10.51% while Beans held +0.55%.",
            "F3: ASAL markets face +9.75 KES/kg higher maize cost and higher volatility on Index/Maize/Goat.",
            "F4: Maize & Beans peak Jun-Sep (1.023 / 1.013); Goats peak Jan-Feb (1.060).",
            "F5: Raw field surveys cover 4.49%; Western Province absent; Samburu at 0.00% across 20 markets.",
        ],
        accent=PPTX_BLUE,
        font_pt=13,
    )
    _add_bullets_box(
        s11,
        6.8,
        1.35,
        5.98,
        5.4,
        "Stakeholder Recommendations",
        [
            "R1: Track Maize & Beans YoY measures separately from the Goat-heavy composite index.",
            "R2: Deploy field enumerators to Samburu, Kisumu, Turkana, and Garissa.",
            "R3: Release grain reserves in May ahead of Jun-Sep peaks; time pastoral aid for Jan-Feb.",
            "R4: Target grain support to Turkana (+15.3 KES) & Mandera (+10.7 KES) linked to nearby markets like Kitui (-15.59 KES/kg).",
            "R5: Expand market coverage to 20 unrepresented counties (incl. Western Kenya) and single-market hubs.",
        ],
        accent=PPTX_TEAL,
        font_pt=13,
    )
    _set_speaker_notes(s11, "Tie each finding directly to one numbered operational recommendation.")

    # Slide 12: Limitations, AI Disclosure & Live Defense Readiness
    s12 = prs.slides.add_slide(blank_layout)
    _add_slide_header(s12, "Limitations, Academic Integrity, and Live Defense Readiness", "Dataset limits and Section 10 AI tooling disclosure", 12, total_slides)
    _add_bullets_box(
        s12,
        0.55,
        1.35,
        6.0,
        5.4,
        "Scope Limits & Ethics",
        [
            "No household income or expenditure weights; affordability is inferred from price premiums.",
            "27 of 47 counties covered unevenly (Turkana 57 markets; Western Province absent).",
            "Series ends October 2026; subsequent seasonal shocks require future refresh.",
            "CC BY 4.0 aggregate market prices with zero personal data.",
        ],
        accent=PPTX_ORANGE,
        font_pt=13,
    )
    _add_bullets_box(
        s12,
        6.8,
        1.35,
        5.98,
        5.4,
        "AI Disclosure & Reproducibility",
        [
            "All 55,692 source rows come directly from World Bank RTFP records (zero synthetic observations).",
            "AI tooling assisted code scaffolding, TMDL export, documentation, and testing.",
            "Automated pytest checks verify ETL invariants, PBIR/TMDL bindings, and Python benchmarks.",
            "Thank you. Ready for live model inspection and questions.",
        ],
        accent=PPTX_NAVY,
        font_pt=13,
    )
    _set_speaker_notes(s12, "Review dataset limits, note that all 55,692 rows come from World Bank RTFP records, disclose AI tool use per Section 10, and invite questions.")

    prs.save(str(output_path))
    return output_path


def build_contribution_matrix_markdown() -> str:
    """Write contribution/contribution-matrix.md accurately crediting the 2-member group."""
    lines: list[str] = [
        "# Group Project Contribution Matrix (DSA 3050A)",
        "",
        "**Project:** Mzigo Chakula (Kenya Food Price Inflation and Household Affordability, 2007 to 2026)",
        "**Repository:** `princenzmw/mzigo-chakula`",
        "**Group Composition Note:** Two-member group (`Prince Nzamuwe` and `Yizere Denis Derick`). Yizere Denis Derick notified the course lecturer of a medical situation during execution; his framing and review contributions are recorded below.",
        "",
        "## Individual Contribution Register",
        "",
        "| Group Member | Assigned Role | Tasks Completed | Evidence in Repository (Files, Branches & PRs) |",
        "| --- | --- | --- | --- |",
        "| Prince Nzamuwe | Lead Analyst & BI Architect | Dataset sourcing and audit, 46-column profiling, 4 Power Query M scripts (10 transformations T1 to T10), star schema model and 15 DAX measures, Python QA/DAX validation suite (44 automated tests), 4-page 46-visual Power BI report with native page navigation, 12-page PDF report, 12-slide presentation, PR workflow management | `src/mzigo_chakula/*.py`, `tests/*.py`, `powerquery/*.pq`, `pbip/`, `README.md`, `docs/proposal.pdf`, `docs/dataset-dictionary.csv`, `docs/data-quality-profile.md`, `docs/transformation-log.md`, `docs/model-diagram.png`, `docs/dax-catalogue.md`, `docs/usability-and-insights.md`, `docs/report.md`, `docs/report.pdf`, `slides/presentation.pptx`, `screenshots/`, `output/`, `contribution/contribution-matrix.md`, PRs #1 to #12 |",
        "| Yizere Denis Derick | Group Contributor | Problem framing alignment, stakeholder and operational decision specification, analytical question review, deliverable checklist verification | `README.md` (Problem statement, Business decisions supported, Analytical questions, Contributors) |",
        "",
        "## Weekly Submission Traceability",
        "",
        "| Checkpoint | Primary Deliverable | Repository Evidence |",
        "| --- | --- | --- |",
        "| Week 1 | Proposal, 46-column dictionary, data quality profile, initial Power BI import screenshot | PR #2, PR #4 (`docs/proposal.pdf`, `docs/dataset-dictionary.csv`, `docs/data-quality-profile.md`, `screenshots/week1-initial-import.png`) |",
        "| Week 2 | 10 Power Query M transforms, dimension CSVs (`dim_markets.csv`, `dim_date.csv`, `dim_commodity.csv`), transformation QA log, Python cleaning card | PR #3, PR #4 (`powerquery/*.pq`, `data/processed/dim_*.csv`, `docs/transformation-log.md`, `screenshots/week2-powerquery-cleaning.png`) |",
        "| Week 3 | 4-table star schema packaged in Tabular Model Definition Language (TMDL) and Power BI Project (PBIP), 15 DAX measures, Model View screenshot, DAX validation card and schema diagram | PR #5, PR #8, PR #9 (`pbip/`, `docs/model-diagram.png`, `screenshots/week3-powerbi-model-view.png`, `screenshots/week3-dax-validation.png`, `docs/dax-catalogue.md`) |",
        "| Week 4 | 4-page Power BI Enhanced Report Format (PBIR) layout (46 visuals, native page navigation, custom theme, full-width tables), 300 DPI PNG screenshots, usability insights | PR #6, PR #8, PR #9, PR #10 (`pbip/mzigo-chakula.Report/`, `screenshots/page1-executive-pulse.png`, `screenshots/page2-county-commodity.png`, `screenshots/page3-trends-diagnostics.png`, `screenshots/page4-decisions-action.png`, `output/page1-executive-pulse.png`, `output/page2-county-commodity.png`, `output/page3-trends-diagnostics.png`, `output/page4-decisions-action.png`, `docs/usability-and-insights.md`) |",
        "| Week 5 | 12-page final PDF report with workflow visuals and Power BI Desktop captures, 12-slide presentation, README, contribution matrix | PR #7, PR #8, PR #9, PR #10 (`docs/report.pdf`, `docs/report.md`, `slides/presentation.pptx`, `README.md`, `contribution/contribution-matrix.md`) |",
        "",
    ]
    return "\n".join(lines)


def update_readme_final_sections(
    etl_result: ETLResult,
    summary: dict[str, Any],
    readme_path: Path,
) -> Path:
    """Populate README.md Findings, Recommendations, Dashboard Preview, and Reproduction steps."""
    content = readme_path.read_text(encoding="utf-8")
    findings, recommendations = _findings_and_recommendations(etl_result, summary)

    new_findings_lines = ["## Findings", ""]
    for idx, (title, body) in enumerate(findings, start=1):
        new_findings_lines.append(f"{idx}. **{title}:** {body}")

    new_rec_lines = ["## Recommendations", ""]
    for idx, (title, body) in enumerate(recommendations, start=1):
        new_rec_lines.append(f"{idx}. **{title}:** {body}")
    new_rec_lines.extend(
        [
            "",
            "## Dashboard preview",
            "",
            "All four report pages (300 DPI) and the star schema diagram are saved in the repository:",
            "",
            "* Star Schema Model: [docs/model-diagram.png](docs/model-diagram.png)",
            "* Page 1 Executive Pulse: [screenshots/page1-executive-pulse.png](screenshots/page1-executive-pulse.png)",
            "* Page 2 County and Commodity: [screenshots/page2-county-commodity.png](screenshots/page2-county-commodity.png)",
            "* Page 3 Trends and Diagnostics: [screenshots/page3-trends-diagnostics.png](screenshots/page3-trends-diagnostics.png)",
            "* Page 4 Decisions and Action: [screenshots/page4-decisions-action.png](screenshots/page4-decisions-action.png)",
            "",
        ]
    )

    normalized = content.replace("\r\n", "\n")
    start_idx = normalized.index("## Findings\n")
    end_idx = normalized.index("## Limitations\n")
    replacement_section = "\n".join(new_findings_lines) + "\n\n" + "\n".join(new_rec_lines) + "\n"
    updated = normalized[:start_idx] + replacement_section + normalized[end_idx:]

    old_repro = (
        "3. Open the Power BI file:\n```text\nopen mzigo-chakula.pbix\n\n```\n\n\n"
        "* Power BI will prompt to refresh data. Point it to data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv.\n"
        "* All Power Query transformations will replay automatically."
    )
    new_repro = (
        "3. Open the Power BI Project (`pbip/mzigo-chakula.pbip`) in Microsoft Power BI Desktop:\n"
        "```powershell\n"
        "start pbip/mzigo-chakula.pbip\n"
        "```\n"
        "* The semantic model loads all Power Query M partitions, star-schema relationships, and 15 DAX measures from `pbip/mzigo-chakula.SemanticModel/`.\n"
        "* Optionally run validation tests with `uv sync` and `uv run pytest -v`, or regenerate docs via `uv run python -m mzigo_chakula.generate_week5_deliverables`."
    )
    if old_repro in updated:
        updated = updated.replace(old_repro, new_repro)

    readme_path.write_text(updated, encoding="utf-8")
    return readme_path


def generate_week5_outputs(
    csv_path: Path | None = None,
    docs_dir: Path | None = None,
    slides_dir: Path | None = None,
    contribution_dir: Path | None = None,
    screenshots_dir: Path | None = None,
    output_dir: Path | None = None,
    update_readme: bool = True,
) -> dict[str, Path]:
    """Generate step screenshots, final PDF/MD report, 12-slide PPTX, contribution matrix, and README."""
    source_csv = csv_path or DEFAULT_RAW_CSV
    out_docs = docs_dir or DOCS_DIR
    out_slides = slides_dir or SLIDES_DIR
    out_contrib = contribution_dir or CONTRIBUTION_DIR
    resolved_shots = (
        screenshots_dir
        if screenshots_dir is not None
        else (out_docs.parent / "screenshots" if docs_dir is not None else SCREENSHOTS_DIR)
    )
    resolved_out = (
        output_dir
        if output_dir is not None
        else (out_docs.parent / "output" if docs_dir is not None else OUTPUT_DIR)
    )

    etl_result = run_etl(csv_path=source_csv)
    summary = compute_dax_validation_summary(etl_result)

    week2_shot = render_week2_cleaning_screenshot(
        etl_result, screenshots_dir=resolved_shots, output_dir=resolved_out
    )
    week3_dax_shot = render_week3_dax_validation_screenshot(
        summary, screenshots_dir=resolved_shots, output_dir=resolved_out
    )

    out_docs.mkdir(parents=True, exist_ok=True)
    report_md_path = out_docs / "report.md"
    report_md_path.write_text(build_final_report_markdown(etl_result, summary), encoding="utf-8")
    report_pdf_path = render_final_report_pdf(
        etl_result,
        summary,
        out_docs / "report.pdf",
        screenshots_dir=resolved_shots,
    )

    out_slides.mkdir(parents=True, exist_ok=True)
    pptx_path = render_presentation_pptx(etl_result, summary, out_slides / "presentation.pptx")

    out_contrib.mkdir(parents=True, exist_ok=True)
    contrib_path = out_contrib / "contribution-matrix.md"
    contrib_path.write_text(build_contribution_matrix_markdown(), encoding="utf-8")

    outputs: dict[str, Path] = {
        "week2_cleaning_shot": week2_shot,
        "week3_dax_shot": week3_dax_shot,
        "report_md": report_md_path,
        "report_pdf": report_pdf_path,
        "presentation_pptx": pptx_path,
        "contribution_matrix": contrib_path,
    }
    if update_readme:
        outputs["readme"] = update_readme_final_sections(
            etl_result, summary, PROJECT_ROOT / "README.md"
        )
    return outputs


if __name__ == "__main__":
    generated = generate_week5_outputs()
    for name, fpath in generated.items():
        print(f"{name}: {fpath}")
