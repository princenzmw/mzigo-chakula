"""Generate Week 3 star-schema model diagram (300 DPI) and DAX measure catalogue."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from mzigo_chakula.data import DEFAULT_RAW_CSV, PROJECT_ROOT
from mzigo_chakula.dax_validator import DAX_MEASURES, compute_dax_validation_summary
from mzigo_chakula.etl import COMMODITY_SPECS, ETLResult, run_etl

DOCS_DIR = PROJECT_ROOT / "docs"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"

# Colors
CANVAS_BG = "#F8FAFC"
NAVY_HEADER = "#0F2942"
DIM_HEADER = "#1E40AF"
FACT_HEADER = "#0F766E"
CARD_BG = "#FFFFFF"
CARD_BORDER = "#CBD5E1"
SHADOW_COLOR = "#E2E8F0"
ROW_ALT_BG = "#F1F5F9"
TEXT_DARK = "#0F172A"
TEXT_MUTED = "#475569"
BADGE_PK_BG = "#FEF3C7"
BADGE_PK_FG = "#92400E"
BADGE_FK_BG = "#E0F2FE"
BADGE_FK_FG = "#075985"
BADGE_DATE_BG = "#DCFCE7"
BADGE_DATE_FG = "#166534"
LINE_COLOR = "#1D4ED8"


def _load_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.ImageFont:
    """Load crisp Windows system TrueType font with safe fallback."""
    windir_fonts = Path("C:/Windows/Fonts")
    candidates: list[str]
    if mono:
        candidates = ["consolab.ttf", "consola.ttf"] if bold else ["consola.ttf", "lucon.ttf"]
    elif bold:
        candidates = ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf"]
    else:
        candidates = ["segoeui.ttf", "arial.ttf", "calibri.ttf"]

    for name in candidates:
        font_path = windir_fonts / name
        if font_path.is_file():
            return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default(size=size)


def _draw_table_card(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    title: str,
    subtitle: str,
    header_color: str,
    rows: list[tuple[str, str, str]],
    fonts: dict[str, ImageFont.ImageFont],
    anchor_columns: dict[str, int],
    table_key: str,
) -> int:
    """Draw a semantic model table card and record Y coordinates of join keys."""
    header_h = 84
    row_h = 44
    total_h = header_h + len(rows) * row_h + 12

    # Subtle shadow + card body
    draw.rounded_rectangle(
        [x + 6, y + 6, x + width + 6, y + total_h + 6],
        radius=12,
        fill=SHADOW_COLOR,
    )
    draw.rounded_rectangle(
        [x, y, x + width, y + total_h],
        radius=12,
        fill=CARD_BG,
        outline=CARD_BORDER,
        width=2,
    )

    # Header band
    draw.rounded_rectangle(
        [x, y, x + width, y + header_h],
        radius=12,
        fill=header_color,
    )
    draw.rectangle([x, y + header_h - 14, x + width, y + header_h], fill=header_color)
    draw.text((x + 20, y + 14), title, font=fonts["card_title"], fill="#FFFFFF")
    draw.text((x + 20, y + 50), subtitle, font=fonts["card_sub"], fill="#DBEAFE")

    # Columns
    curr_y = y + header_h + 6
    for idx, (col_name, col_type, badge) in enumerate(rows):
        if idx % 2 == 1:
            draw.rectangle([x + 2, curr_y, x + width - 2, curr_y + row_h], fill=ROW_ALT_BG)

        center_y = curr_y + row_h // 2
        anchor_columns[f"{table_key}.{col_name}"] = center_y

        text_x = x + 20
        if badge:
            if badge == "PK":
                bg, fg = BADGE_PK_BG, BADGE_PK_FG
            elif badge == "FK":
                bg, fg = BADGE_FK_BG, BADGE_FK_FG
            else:
                bg, fg = BADGE_DATE_BG, BADGE_DATE_FG
            badge_w = 52 if len(badge) <= 2 else 112
            draw.rounded_rectangle(
                [text_x, curr_y + 8, text_x + badge_w, curr_y + row_h - 8],
                radius=6,
                fill=bg,
            )
            draw.text((text_x + 10, curr_y + 11), badge, font=fonts["badge"], fill=fg)
            text_x += badge_w + 12

        draw.text((text_x, curr_y + 10), col_name, font=fonts["col"], fill=TEXT_DARK)
        draw.text(
            (x + width - 20, curr_y + 11),
            col_type,
            font=fonts["type"],
            fill=TEXT_MUTED,
            anchor="ra",
        )
        curr_y += row_h

    return y + total_h


def _draw_orthogonal_relationship(
    draw: ImageDraw.ImageDraw,
    x_dim: int,
    y_dim: int,
    x_fact: int,
    y_fact: int,
    direction: str,
    label_font: ImageFont.ImageFont,
) -> None:
    """Draw a 1:* orthogonal relationship connector with filter-direction arrow."""
    mid_x = (x_dim + x_fact) // 2
    points = [(x_dim, y_dim), (mid_x, y_dim), (mid_x, y_fact), (x_fact, y_fact)]
    draw.line(points, fill=LINE_COLOR, width=4)

    # Cardinality markers (1 near dimension edge, * near fact edge)
    dim_sign = 1 if x_fact > x_dim else -1
    fact_sign = -dim_sign
    draw.text((x_dim + 16 * dim_sign, y_dim - 28), "1", font=label_font, fill=LINE_COLOR, anchor="ma")
    draw.text((x_fact + 18 * fact_sign, y_fact - 28), "*", font=label_font, fill=LINE_COLOR, anchor="ma")

    # Single-direction filter arrow on horizontal entry segment into fact table
    arrow_x = (mid_x + x_fact) // 2
    if direction == "right":
        tri = [(arrow_x + 12, y_fact), (arrow_x - 10, y_fact - 11), (arrow_x - 10, y_fact + 11)]
    else:
        tri = [(arrow_x - 12, y_fact), (arrow_x + 10, y_fact - 11), (arrow_x + 10, y_fact + 11)]
    draw.polygon(tri, fill=LINE_COLOR)


def render_model_diagram(output_path: Path) -> Path:
    """Render 300 DPI star-schema diagram PNG to docs/model-diagram.png."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 2400, 1650
    img = Image.new("RGB", (width, height), CANVAS_BG)
    draw = ImageDraw.Draw(img)

    fonts = {
        "banner_title": _load_font(42, bold=True),
        "banner_sub": _load_font(22, bold=False),
        "card_title": _load_font(28, bold=True),
        "card_sub": _load_font(19, bold=False),
        "col": _load_font(21, bold=False, mono=True),
        "type": _load_font(18, bold=False),
        "badge": _load_font(16, bold=True),
        "rel": _load_font(24, bold=True),
        "footer_title": _load_font(22, bold=True),
        "footer": _load_font(19, bold=False),
    }

    # Top title banner
    draw.rectangle([0, 0, width, 130], fill=NAVY_HEADER)
    draw.text(
        (70, 22),
        "Mzigo Chakula: Star Schema Semantic Model",
        font=fonts["banner_title"],
        fill="#FFFFFF",
    )
    draw.text(
        (70, 78),
        "4 Related Tables | 3 Active Single-Direction 1:* Relationships | 15 DAX Measures | Fact Grain: (mkt_id, date_key, commodity_id)",
        font=fonts["banner_sub"],
        fill="#BFDBFE",
    )

    anchors: dict[str, int] = {}

    _draw_table_card(
        draw=draw,
        x=70,
        y=170,
        width=660,
        title="dim_markets",
        subtitle="233 physical markets | 27 counties | 7 regions",
        header_color=DIM_HEADER,
        rows=[
            ("mkt_id", "text", "PK"),
            ("mkt_name", "text", ""),
            ("adm1_name (Region)", "text", ""),
            ("adm2_name (County)", "text", "COUNTY"),
            ("subcounty_or_district", "text", ""),
            ("county_group", "text", ""),
            ("lat", "double", "LAT"),
            ("lon", "double", "LON"),
            ("data_coverage", "double", ""),
            ("data_coverage_recent", "double", ""),
        ],
        fonts=fonts,
        anchor_columns=anchors,
        table_key="dim_markets",
    )

    _draw_table_card(
        draw=draw,
        x=70,
        y=770,
        width=660,
        title="dim_commodity",
        subtitle="3 tracked staple commodities (Beans, Maize, Goat)",
        header_color=DIM_HEADER,
        rows=[
            ("commodity_id", "text", "PK"),
            ("commodity_name", "text", ""),
            ("category", "text", ""),
            ("unit", "text", ""),
            ("index_weight_note", "text", ""),
        ],
        fonts=fonts,
        anchor_columns=anchors,
        table_key="dim_commodity",
    )

    _draw_table_card(
        draw=draw,
        x=1670,
        y=170,
        width=660,
        title="dim_date  [Date Table]",
        subtitle="238 consecutive months (2007-01-01 to 2026-10-01)",
        header_color=DIM_HEADER,
        rows=[
            ("date_key", "int64", "KEY"),
            ("full_date", "dateTime", "DATE"),
            ("year", "int64", ""),
            ("month", "int64", ""),
            ("month_name", "text", "SORT"),
            ("year_month", "text", ""),
            ("quarter", "text", ""),
            ("season", "text", ""),
            ("is_recent", "bool", ""),
            ("is_last_36m", "bool", ""),
        ],
        fonts=fonts,
        anchor_columns=anchors,
        table_key="dim_date",
    )

    _draw_table_card(
        draw=draw,
        x=870,
        y=220,
        width=660,
        title="fact_prices  (+15 DAX Measures)",
        subtitle="166,362 rows (55,454 physical market-months x 3 commodities)",
        header_color=FACT_HEADER,
        rows=[
            ("price_id", "text", "PK"),
            ("mkt_id", "text", "FK"),
            ("date_key", "int64", "FK"),
            ("commodity_id", "text", "FK"),
            ("price_value (Close KES)", "double", ""),
            ("open_price / high / low", "double", ""),
            ("raw_spot_price", "double", ""),
            ("commodity_inflation_yoy", "double", ""),
            ("food_price_index", "double", "GRAIN"),
            ("inflation_food_price_index", "double", ""),
            ("trust_score", "double", ""),
            ("price_change_mom", "double", ""),
            ("price_change_mom_pct", "double", ""),
            ("z_score", "double", ""),
            ("is_outlier", "bool", ""),
        ],
        fonts=fonts,
        anchor_columns=anchors,
        table_key="fact_prices",
    )

    # Relationships
    _draw_orthogonal_relationship(
        draw,
        x_dim=730,
        y_dim=anchors["dim_markets.mkt_id"],
        x_fact=870,
        y_fact=anchors["fact_prices.mkt_id"],
        direction="right",
        label_font=fonts["rel"],
    )
    _draw_orthogonal_relationship(
        draw,
        x_dim=730,
        y_dim=anchors["dim_commodity.commodity_id"],
        x_fact=870,
        y_fact=anchors["fact_prices.commodity_id"],
        direction="right",
        label_font=fonts["rel"],
    )
    _draw_orthogonal_relationship(
        draw,
        x_dim=1670,
        y_dim=anchors["dim_date.date_key"],
        x_fact=1530,
        y_fact=anchors["fact_prices.date_key"],
        direction="left",
        label_font=fonts["rel"],
    )

    # Bottom architecture note strip
    footer_y = 1350
    draw.rounded_rectangle(
        [70, footer_y, 2330, 1590],
        radius=12,
        fill=CARD_BG,
        outline=CARD_BORDER,
        width=2,
    )
    draw.text(
        (100, footer_y + 24),
        "Model Governance, Grain Rules, and Referential Integrity",
        font=fonts["footer_title"],
        fill=NAVY_HEADER,
    )
    notes = [
        "1. Filter Direction: Strictly single-direction (1:*) from all three dimensions into fact_prices. Zero bidirectional filters or ambiguous paths.",
        "2. Calendar Table: dim_date[full_date] is marked as the official Date Table for EDATE and TREATAS time intelligence; month_name sorts by month.",
        "3. Composite Index Grain Rule: food_price_index lives at (mkt_id, date_key) grain. National Food Price Index uses SUMMARIZE(mkt_id, date_key) to avoid 3x counting.",
        "4. Integrity Verified: 0 duplicate PKs, 0 orphan FKs across all 166,362 fact rows, 100.00% modeled completeness, 4.49% raw spot survey coverage.",
    ]
    ny = footer_y + 68
    for line in notes:
        draw.text((100, ny), line, font=fonts["footer"], fill=TEXT_DARK)
        ny += 38

    img.save(output_path, format="PNG", dpi=(300, 300))
    return output_path


def build_dax_catalogue_markdown(
    etl_result: ETLResult,
    summary: dict[str, Any],
) -> str:
    """Build docs/dax-catalogue.md in plain human prose with verified metrics."""
    overall = summary["overall"]
    commodities = summary["commodities"]
    counties = summary["counties"]
    groups = summary["group_comparison"]
    qa = etl_result.qa_metrics

    top_12m = sorted(counties, key=lambda c: c["rank_12m"])[:5]
    top_36m = sorted(counties, key=lambda c: c["rank_36m"])[:5]
    lowest_survey = sorted(counties, key=lambda c: c["survey_coverage_rate"])[:5]
    highest_survey = sorted(counties, key=lambda c: c["survey_coverage_rate"], reverse=True)[:5]
    maize_expensive = sorted(counties, key=lambda c: c["gap_maize_kes"], reverse=True)[:5]
    maize_cheapest = sorted(counties, key=lambda c: c["gap_maize_kes"])[:5]

    lines: list[str] = [
        "# Week 3 Data Model and DAX Measure Catalogue",
        "",
        "**Course:** DSA 3050A | Business Intelligence and Data Visualization (Group Project B)",
        "**Project:** Mzigo Chakula (Kenya Food Price Inflation and Household Affordability, 2007 to 2026)",
        "**Authors:** Prince Nzamuwe, Yizere Denis Derick",
        "**Semantic Model Project:** `pbip/mzigo-chakula.pbip` (TMDL under `pbip/mzigo-chakula.SemanticModel/definition/`)",
        "",
        "---",
        "",
        "## 1. Star Schema Architecture and Grain Integrity",
        "",
        (
            f"The semantic model organizes {qa['fact_prices_rows']:,} market-month-commodity observations into a four-table star schema "
            "with single-direction filtering from dimension tables into `fact_prices`:"
        ),
        "",
        (
            f"- `dim_markets` ({qa['dim_markets_rows']:,} rows, PK `mkt_id`): Physical Kenyan markets mapped to "
            f"27 counties, 7 regions, and `Arid & Semi-Arid (ASAL)` (16 counties, 202 markets) versus `Agricultural & Urban` "
            "(11 counties, 31 markets). Geographic categories (`County`, `StateOrProvince`, `Latitude`, `Longitude`) are enabled for Power BI maps."
        ),
        (
            f"- `dim_date` ({qa['dim_date_rows']:,} rows, PK `date_key`): Continuous monthly calendar from 2007 "
            f"to {overall['recent_12m_end'][:4]} (`2007-01-01` to `2026-10-01`). `dim_date[full_date]` is marked as the official Date Table and `month_name` is sorted "
            "by `month` (`1` to `12`)."
        ),
        (
            f"- `dim_commodity` ({qa['dim_commodity_rows']} rows, PK `commodity_id`): Lookup dimension mapping `beans` (`Beans (1 kg)`), "
            "`maize_fao` (`Maize (1 kg)`), and `livestock_goat_s_fao` (`Goat (1 head)`) with explicit food categories and physical units (`KG`, `Head`)."
        ),
        (
            f"- `fact_prices` ({qa['fact_prices_rows']:,} rows, PK `price_id`): One row per `(mkt_id, date_key, commodity_id)`. "
            "Foreign keys (`mkt_id`, `date_key`, `commodity_id`) are hidden from Report View so slicers always filter through dimension tables."
        ),
        "",
        (
            "**Grain Protection Rule:** Each physical market-month carries one composite `food_price_index` value in the raw CSV, so unpivoting "
            "three commodities repeats that market-month index three times inside `fact_prices`. The `[National Food Price Index]` measure "
            "wraps `SUMMARIZE(fact_prices, fact_prices[mkt_id], fact_prices[date_key])` so every market-month enters the index mean once "
            "even when multiple commodities are selected."
        ),
        "",
        "![Mzigo Chakula Star Schema Diagram](model-diagram.png)",
        "",
        "---",
        "",
        "## 2. Model Relationships and Integrity Verification",
        "",
        "| Relationship | From Table (Many) | To Table (One) | Cardinality | Filter Direction | Status | Orphan Rows |",
        "| --- | --- | --- | --- | --- | --- | ---: |",
        "| `fact_prices_to_dim_markets` | `fact_prices[mkt_id]` | `dim_markets[mkt_id]` | `*:1` | Single (`dim_markets` filters `fact_prices`) | Active | 0 |",
        "| `fact_prices_to_dim_date` | `fact_prices[date_key]` | `dim_date[date_key]` | `*:1` | Single (`dim_date` filters `fact_prices`) | Active | 0 |",
        "| `fact_prices_to_dim_commodity` | `fact_prices[commodity_id]` | `dim_commodity[commodity_id]` | `*:1` | Single (`dim_commodity` filters `fact_prices`) | Active | 0 |",
        "",
        "---",
        "",
        "## 3. Complete DAX Measure Catalogue (15 Measures)",
        "",
    ]

    for spec in DAX_MEASURES:
        lines.extend(
            [
                f"### {spec.measure_number}. `{spec.name}`",
                "",
                f"- **Table / Folder:** `{spec.table_name}` / `{spec.display_folder}`",
                f"- **Format String:** `{spec.format_string}`",
                f"- **Purpose:** {spec.description}",
                "",
                "```dax",
                spec.dax_expression,
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "",
            "## 4. DAX Validation Results Against Python Reference Engine",
            "",
            "### Overall Model KPI Benchmarks",
            "",
            "| Measure | Evaluation Slice | Computed Value |",
            "| --- | --- | ---: |",
            f"| `National Food Price Index` | Full Span (`2007-01-01` to `2026-10-01`) | {overall['national_food_index_full']:.4f} |",
            f"| `National Food Price Index` | Recent 12 Months (`{overall['recent_12m_start']}` to `{overall['recent_12m_end']}`) | {overall['national_food_index_recent_12m']:.4f} |",
            f"| `National Food Price Index` | Prior 12 Months (`2024-11-01` to `2025-10-01`) | {overall['national_food_index_prior_12m']:.4f} |",
            f"| `YoY Inflation %` | Recent 12 Months vs. Prior 12 Months | {overall['yoy_inflation_recent_12m'] * 100:.2f}% |",
            f"| `Cumulative Index YTD` | Calendar Year 2026 (`2026-01-01` to `2026-10-01`) | {overall['cumulative_index_ytd_2026']:.4f} |",
            f"| `Data Completeness %` | Full Model (`166,362 / (233 x 238 x 3)`) | {overall['data_completeness_pct'] * 100:.2f}% |",
            f"| `Survey Coverage Rate %` | Raw Non-Null Spot Observations (`7,470 / 166,362`) | {overall['survey_coverage_rate_pct'] * 100:.2f}% |",
            "",
            "### Per-Commodity Measures and Food Index Co-Movement",
            "",
            "| Commodity | `Avg Price (KES)` Full | `Avg Price (KES)` 12m | `Commodity YoY Inflation %` 12m | Latest `MoM Change %` (Oct 2026) | `Price Volatility (KES)` | `Price Volatility CV %` | `12-Month Rolling Avg (KES)` | Corr `r` vs. Index | R-Squared vs. Index |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for spec in COMMODITY_SPECS:
        item = commodities[spec.commodity_id]
        lines.append(
            f"| {item['commodity_name']} | {item['avg_price_kes']:,.2f} | {item['recent_12m_avg_kes']:,.2f} | "
            f"{item['yoy_inflation_12m'] * 100:+.2f}% | {item['latest_mom_pct'] * 100:+.2f}% | "
            f"{item['volatility_kes']:,.2f} | {item['volatility_cv'] * 100:.2f}% | "
            f"{item['rolling_12m_avg_kes']:,.2f} | {item['corr_with_food_index']:.4f} | {item['r2_with_food_index'] * 100:.2f}% |"
        )

    lines.extend(
        [
            "",
            "### ASAL vs. Agricultural & Urban Comparison (`group_comparison`)",
            "",
            "| County Group | Fact Rows | Food Index Mean | Food Index CV % | Maize CV % | Beans CV % | Goat CV % | Mean Abs MoM % | Outlier Rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for group_name in ("Arid & Semi-Arid (ASAL)", "Agricultural & Urban"):
        g = groups[group_name]
        gc = g["commodities"]
        lines.append(
            f"| {group_name} | {g['rows']:,} | {g['food_index_mean']:.3f} | {g['food_index_cv'] * 100:.2f}% | "
            f"{gc['maize_fao']['volatility_cv'] * 100:.2f}% | {gc['beans']['volatility_cv'] * 100:.2f}% | "
            f"{gc['livestock_goat_s_fao']['volatility_cv'] * 100:.2f}% | {g['mean_abs_mom_pct']:.2f}% | "
            f"{g['outlier_rate'] * 100:.2f}% |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 5. Quantitative Answers to the 5 Project Analytical Questions",
            "",
            "### Q1. Which counties experienced the highest 12-month food price inflation over the last three years (2024 to 2026)?",
            "",
            (
                "In this World Bank Kenya release, livestock goat prices and the composite `c_food_price_index` hit a peak "
                "in 2023 (annual mean 3.465, goat 10,106 KES), declined through 2024 (3.031) and 2025 (1.744), and rose again in 2026 (1.919). "
                "Because the 36-month window (`2023-11` to `2026-10` vs. `2022-11` to `2025-10`) spans the descent from that 2023 peak, "
                "every county shows a negative 3-year index average, with coastal and eastern counties holding the highest relative rank "
                "(smallest drop from 2023). Over the most recent 12 months (`2025-11` to `2026-10` vs. prior 12 months), overall national index inflation "
                f"rose {overall['yoy_inflation_recent_12m'] * 100:.2f}%, led by the counties below:"
            ),
            "",
            "| Rank (Recent 12m) | County | Group | Markets | Recent 12m `YoY Inflation %` | Last 36m Mean `YoY Inflation %` | Rank (Last 36m) |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )

    for c in top_12m:
        lines.append(
            f"| {c['rank_12m']} | {c['county']} | {c['county_group']} | {c['markets']} | "
            f"{c['yoy_12m'] * 100:+.2f}% | {c['yoy_36m'] * 100:+.2f}% | {c['rank_36m']} |"
        )

    lines.extend(
        [
            "",
            "Highest-ranking counties across the full 36-month window (`2023-11` to `2026-10` relative to `2022-11` to `2025-10`): "
            + ", ".join(f"{c['county']} ({c['yoy_36m'] * 100:+.2f}%)" for c in top_36m)
            + ".",
            "",
            "### Q2. Which tracked commodity drives the largest share of movements in the composite food price index?",
            "",
            (
                f"Although the CSV `components` text column lists `livestock_goat_s_fao (1 unit, Index Weight = 0)`, empirical correlation across all "
                f"55,454 physical market-months shows that `Goat (1 head)` tracks `c_food_price_index` with `r = {commodities['livestock_goat_s_fao']['corr_with_food_index']:.5f}` "
                f"(`R^2 = {commodities['livestock_goat_s_fao']['r2_with_food_index'] * 100:.2f}%` for price levels and "
                f"`r = {commodities['livestock_goat_s_fao']['corr_yoy_with_index_yoy']:.5f}` for YoY index rates). "
                f"`Beans (1 kg)` shows `r = {commodities['beans']['corr_with_food_index']:.4f}` (`R^2 = {commodities['beans']['r2_with_food_index'] * 100:.2f}%`), "
                f"and `Maize (1 kg)` shows `r = {commodities['maize_fao']['corr_with_food_index']:.4f}` (`R^2 = {commodities['maize_fao']['r2_with_food_index'] * 100:.2f}%`). "
                "Because one live goat trades around 3,456 KES per head compared to 56 KES/kg for maize and 106 KES/kg for beans, "
                "goat price levels account for 99.99% of variance in the unscaled index series. Dashboard visuals evaluate individual staple commodities "
                "via `[Avg Price (KES)]` and `[Commodity YoY Inflation %]` alongside the composite index."
            ),
            "",
            "### Q3. Is price volatility higher in ASAL counties than in agricultural and urban counties?",
            "",
            (
                f"Across the composite Food Price Index (CV {groups['Arid & Semi-Arid (ASAL)']['food_index_cv'] * 100:.2f}% vs. "
                f"{groups['Agricultural & Urban']['food_index_cv'] * 100:.2f}%), Maize ({groups['Arid & Semi-Arid (ASAL)']['commodities']['maize_fao']['volatility_cv'] * 100:.2f}% "
                f"vs. {groups['Agricultural & Urban']['commodities']['maize_fao']['volatility_cv'] * 100:.2f}%), and Goats "
                f"({groups['Arid & Semi-Arid (ASAL)']['commodities']['livestock_goat_s_fao']['volatility_cv'] * 100:.2f}% vs. "
                f"{groups['Agricultural & Urban']['commodities']['livestock_goat_s_fao']['volatility_cv'] * 100:.2f}%), "
                f"ASAL counties (16 counties, 202 markets) exhibit higher price dispersion and outlier rates "
                f"({groups['Arid & Semi-Arid (ASAL)']['outlier_rate'] * 100:.2f}% vs. {groups['Agricultural & Urban']['outlier_rate'] * 100:.2f}%) "
                f"than Agricultural & Urban counties (11 counties, 31 markets), whereas dry Beans CV is slightly higher in Agricultural & Urban "
                f"markets ({groups['Agricultural & Urban']['commodities']['beans']['volatility_cv'] * 100:.2f}% vs. "
                f"{groups['Arid & Semi-Arid (ASAL)']['commodities']['beans']['volatility_cv'] * 100:.2f}%). Mean maize prices are "
                f"+{(groups['Arid & Semi-Arid (ASAL)']['commodities']['maize_fao']['avg_price'] - groups['Agricultural & Urban']['commodities']['maize_fao']['avg_price']):.2f} KES/kg higher in ASAL markets."
            ),
            "",
            "Maize `Affordability Gap (KES)` extremes (County average vs. 56.02 KES/kg national physical-market mean):",
            "- Highest cost burden: " + ", ".join(f"{c['county']} (+{c['gap_maize_kes']:.2f} KES/kg)" for c in maize_expensive) + ".",
            "- Lowest cost burden: " + ", ".join(f"{c['county']} ({c['gap_maize_kes']:.2f} KES/kg)" for c in maize_cheapest) + ".",
            "",
            "### Q4. What seasonal price cycles repeat across the year?",
            "",
            "| Season Window | Beans `Seasonal Index` | Maize `Seasonal Index` | Goat `Seasonal Index` |",
            "| --- | ---: | ---: | ---: |",
        ]
    )

    sw = summary["seasonal_by_window"]
    for season_name in (
        "Hot Dry / Lean (Jan-Feb)",
        "Long Rains (Mar-May)",
        "Cool Dry / Harvest (Jun-Sep)",
        "Short Rains (Oct-Dec)",
    ):
        lines.append(
            f"| {season_name} | {sw['beans'][season_name]:.3f} | "
            f"{sw['maize_fao'][season_name]:.3f} | {sw['livestock_goat_s_fao'][season_name]:.3f} |"
        )

    beans_peak = max(sw["beans"].items(), key=lambda kv: kv[1])
    beans_low = min(sw["beans"].items(), key=lambda kv: kv[1])
    maize_peak = max(sw["maize_fao"].items(), key=lambda kv: kv[1])
    maize_low = min(sw["maize_fao"].items(), key=lambda kv: kv[1])
    goat_peak = max(sw["livestock_goat_s_fao"].items(), key=lambda kv: kv[1])
    goat_low = min(sw["livestock_goat_s_fao"].items(), key=lambda kv: kv[1])

    lines.extend(
        [
            "",
            (
                f"Staple maize peaks during `{maize_peak[0]}` ({maize_peak[1]:.3f}) and dips during `{maize_low[0]}` ({maize_low[1]:.3f}), "
                f"while dry beans peak in `{beans_peak[0]}` ({beans_peak[1]:.3f}) and reach their low in `{beans_low[0]}` ({beans_low[1]:.3f}). "
                f"Live goats stay firmest during `{goat_peak[0]}` ({goat_peak[1]:.3f}) and lowest in `{goat_low[0]}` ({goat_low[1]:.3f})."
            ),
            "",
            "### Q5. How uneven is market coverage across counties and where are survey gaps largest?",
            "",
            (
                "While modeled closing prices fill 100.00% of the `233 x 238 x 3` grid, raw field observations cover 4.49% of cells "
                "overall and vary widely by county and market count. Five counties (Embu, Lamu, Machakos, Nyeri, Uasin Gishu) rely on "
                "one monitored market, whereas Turkana accounts for 57 markets (24.5% of all markets)."
            ),
            "",
            "| Group | Counties | Lowest vs. Highest `Survey Coverage Rate %` |",
            "| --- | --- | --- |",
            "| Lowest Survey Coverage | "
            + ", ".join(f"{c['county']} ({c['survey_coverage_rate'] * 100:.2f}%)" for c in lowest_survey)
            + " | Remote / high-market-count northern counties and large urban wholesale hubs |",
            "| Highest Survey Coverage | "
            + ", ".join(f"{c['county']} ({c['survey_coverage_rate'] * 100:.2f}%)" for c in highest_survey)
            + " | Single- or few-market benchmark stations with regular survey logs |",
            "",
        ]
    )
    return "\n".join(lines)


def generate_week3_outputs(
    csv_path: Path | None = None,
    docs_dir: Path | None = None,
) -> dict[str, Path]:
    """Generate Week 3 model diagram PNG and validated DAX catalogue markdown."""
    source_csv = csv_path or DEFAULT_RAW_CSV
    out_docs = docs_dir or DOCS_DIR

    etl_result = run_etl(csv_path=source_csv)
    summary = compute_dax_validation_summary(etl_result)

    diagram_path = render_model_diagram(out_docs / "model-diagram.png")
    catalogue_path = out_docs / "dax-catalogue.md"
    catalogue_md = build_dax_catalogue_markdown(etl_result, summary)
    catalogue_path.write_text(catalogue_md, encoding="utf-8")

    return {
        "model_diagram": diagram_path,
        "dax_catalogue": catalogue_path,
    }


if __name__ == "__main__":
    outputs = generate_week3_outputs()
    for name, file_path in outputs.items():
        print(f"{name}: {file_path}")
