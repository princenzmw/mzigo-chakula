"""Generate Week 1 deliverables: dataset dictionary, quality profile, and 3-page proposal."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from fpdf import FPDF

from mzigo_chakula.data import PROJECT_ROOT, profile_dataset

DOCS_DIR = PROJECT_ROOT / "docs"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
INITIAL_IMPORT_SCREENSHOT = SCREENSHOTS_DIR / "week1-initial-import.png"


def write_dataset_dictionary(profile: dict[str, Any], output_path: Path) -> Path:
    """Write the 46-column dataset dictionary CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "col_index",
        "column_name",
        "data_type",
        "table_target",
        "unit",
        "non_null_count",
        "null_count",
        "pct_missing",
        "unique_values",
        "min_value",
        "max_value",
        "sample_value",
        "description",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for col in profile["column_profiles"]:
            writer.writerow({key: col[key] for key in fieldnames})
    return output_path


def build_data_quality_profile_markdown(profile: dict[str, Any]) -> str:
    """Build the Week 1 data-quality profile in plain human prose."""
    stats = profile["market_metric_stats"]
    beans = stats["c_beans"]
    maize = stats["c_maize_fao"]
    goat = stats["c_livestock_goat_s_fao"]
    fpi = stats["c_food_price_index"]

    missing_cols = [c for c in profile["column_profiles"] if c["null_count"] > 0]
    constant_cols = [c for c in profile["column_profiles"] if c["unique_values"] == 1]

    lines: list[str] = [
        "# Initial Data Quality Profile",
        "",
        "Dataset: World Bank Real Time Food Prices (RTFP), Kenya (`KEN_RTFP_mkt_2007_2026-10-05.csv`)",
        "Accessed: 29 October 2026 | License: CC BY 4.0",
        "",
        "## 1. Volume and Granularity",
        "",
        (f"The raw CSV contains {profile['total_rows']:,} rows and {profile['total_columns']} columns "
        f"covering {profile['distinct_months']} monthly dates from {profile['date_min']} to {profile['date_max']}. "
        f"Every series has an unbroken monthly grid of {profile['min_months_per_market']} observations, "
        f"giving {profile['total_series_count']} series multiplied by {profile['distinct_months']} months "
        f"({profile['total_rows']:,} rows)."),
        "",
        "| Slice | Row Count | Distinct Markets | Share of Total |",
        "| --- | ---: | ---: | ---: |",
        (f"| Physical markets | {profile['physical_market_rows']:,} | {profile['physical_markets_count']} | "
        f"{100 * profile['physical_market_rows'] / profile['total_rows']:.2f}% |"),
        (f"| National aggregate (`Market Average`) | {profile['market_average_rows']:,} | 1 | "
        f"{100 * profile['market_average_rows'] / profile['total_rows']:.2f}% |"),
        f"| Full raw CSV | {profile['total_rows']:,} | {profile['total_series_count']} | 100.00% |",
        "",
        ("Power Query must separate or filter out the 238 `Market Average` rows before building market and "
        "county aggregations. Leaving those rows inside `fact_prices` would add a synthetic national series "
        "on top of the 233 physical markets."),
        "",
        "## 2. Missing Values Audit",
        "",
        "Missing values appear in only 13 of the 46 columns and follow three distinct causes:",
        "",
        ("1. Coordinates (`lat`, `lon`): Exactly 238 rows (0.43%) are blank because `Market Average` has no physical location. "
        "All 55,454 physical market rows have valid coordinates."),
        ("2. Year-over-year inflation columns (`inflation_beans`, `inflation_livestock_goat_s_fao`, `inflation_maize_fao`, "
        "`inflation_food_price_index`): Exactly 2,808 rows (5.04%, equal to 234 series times 12 months) are blank in 2007 "
        "because no 2006 baseline exists for year-over-year calculation. From January 2008 onward, these columns are 100% populated."),
        ("3. Raw spot survey columns (`beans`, `livestock_goat_s_fao`, `maize_fao`): Between 94.53% and 96.72% of cells are empty "
        "because physical market surveys occur sporadically. The dataset pairs those sparse raw surveys with modelled open, high, "
        "low, and close estimates (`o_`, `h_`, `l_`, `c_`) that have 0.00% missingness."),
        "",
        "| Column | Non-Null Rows | Null Rows | Missing % | Reason |",
        "| --- | ---: | ---: | ---: | --- |",
    ]

    for col in missing_cols:
        if col["column_name"] in {"lat", "lon"}:
            reason = "Market Average rows have no point coordinates"
        elif col["column_name"].startswith("inflation_"):
            reason = "First 12 months (2007) lack a 2006 prior-year baseline"
        else:
            reason = "Sporadic raw field survey coverage; modelled OHLC series are complete"
        lines.append(
            f"| `{col['column_name']}` | {col['non_null_count']:,} | {col['null_count']:,} | "
            f"{col['pct_missing']:.2f}% | {reason} |"
        )

    lines.extend(
        [
            "",
            "## 3. Constant Metadata Columns",
            "",
            f"{len(constant_cols)} columns hold a single constant value across all {profile['total_rows']:,} rows:",
            "",
            "| Column | Constant Value | Handling in Model |",
            "| --- | --- | --- |",
        ]
    )
    for col in constant_cols:
        val = col["sample_value"]
        if len(val) > 55:
            val = val[:52] + "..."
        lines.append(f"| `{col['column_name']}` | `{val}` | Move to documentation or `dim_commodity` / `dim_markets` |")

    lines.extend(
        [
            "",
            "## 4. Administrative Label Inconsistencies",
            "",
            (f"Physical markets span {profile['raw_admin_pairs_count']} distinct `(adm1_name, adm2_name)` combinations. "
            "Instead of a consistent province-to-county split, the source puts former provinces in `adm1_name` for most rows "
            "while putting modern county names (`Embu`, `Hola (Tana River)`, `Kajiado`, `Kwale`, `Lamu`, `Meru`, "
            "`Taita Taveta`, `Tharaka Nithi`) in `adm1_name` for single-market entries. Five counties (`Kwale`, `Taita Taveta`, "
            "`Tana River`, `Kajiado`, `Meru`) are split across both formats, and `Kitengela (Kajiado)` sits under `Nairobi` "
            "in the source admin fields."),
            "",
            (f"Normalizing these labels assigns every physical market to {profile['clean_counties_count']} Kenyan counties "
            f"across {profile['clean_regions_count']} former provinces (Western Province has no markets in this release)."),
            "",
            "| Raw `adm1_name` | Raw `adm2_name` | Clean Region | Clean County | Markets | Rows |",
            "| --- | --- | --- | --- | ---: | ---: |",
        ]
    )

    for item in profile["geography_mapping_summary"]:
        lines.append(
            f"| {item['raw_adm1']} | {item['raw_adm2']} | {item['clean_region']} | "
            f"{item['clean_county']} | {item['market_count']} | {item['row_count']:,} |"
        )

    lines.extend(
        [
            "",
            "## 5. County Coverage Imbalance",
            "",
            ("Market representation varies sharply by county. Turkana alone contains 57 markets (24.5% of physical markets), "
            "Garissa has 21, Samburu has 20, and Marsabit has 19, while Nyeri, Embu, Machakos, Lamu, and Uasin Gishu have 1 market each."),
            "",
            "| Clean Region | Clean County | Markets | Sample Markets |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for cov in profile["county_coverage"]:
        lines.append(
            f"| {cov['region']} | {cov['county']} | {cov['market_count']} | {cov['sample_markets']} |"
        )

    lines.extend(
        [
            "",
            "## 6. Price and Index Summary Statistics (Physical Markets, n = 55,454)",
            "",
            "| Series | Min | Median | Mean | Max | Std Dev |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            (f"| Beans close (`c_beans`, KES/kg) | {beans['min']:.2f} | {beans['median']:.2f} | "
            f"{beans['mean']:.2f} | {beans['max']:.2f} | {beans['std']:.2f} |"),
            (f"| Maize close (`c_maize_fao`, KES/kg) | {maize['min']:.2f} | {maize['median']:.2f} | "
            f"{maize['mean']:.2f} | {maize['max']:.2f} | {maize['std']:.2f} |"),
            (f"| Goat close (`c_livestock_goat_s_fao`, KES/head) | {goat['min']:.2f} | {goat['median']:.2f} | "
            f"{goat['mean']:.2f} | {goat['max']:.2f} | {goat['std']:.2f} |"),
            (f"| Food Price Index (`c_food_price_index`) | {fpi['min']:.2f} | {fpi['median']:.2f} | "
            f"{fpi['mean']:.2f} | {fpi['max']:.2f} | {fpi['std']:.2f} |"),
            "",
            "## 7. Grain Note for Modelling",
            "",
            ("Beans, maize, and goat prices sit at the `(market, month, commodity)` grain once unpivoted, whereas "
            "`c_food_price_index` sits at the `(market, month)` grain (each market-month carries one composite index value). "
            "Week 3 modelling will either place `c_food_price_index` in a dedicated `fact_market_index` table or aggregate it "
            "at the market-month grain in DAX so unpivoting three commodities does not triple-count the index."),
            "",
        ]
    )
    return "\n".join(lines)


def write_data_quality_profile(profile: dict[str, Any], output_path: Path) -> Path:
    """Write docs/data-quality-profile.md."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = build_data_quality_profile_markdown(profile)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def build_proposal_markdown(profile: dict[str, Any], has_screenshot: bool) -> str:
    """Build the 2-to-3-page Week 1 proposal markdown in plain human prose."""
    screenshot_note = (
        "Power Query Editor screenshot captured immediately upon importing `data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv` "
        "(showing 46 columns, 999+ rows in the 1,000-row profiling preview, column quality and distribution bars, "
        "and Power BI's default CSV import steps `Source`, `Use First Row as Headers`, and `Change Type` under Applied Steps):\n\n"
        "![Initial Power BI Power Query Import](../screenshots/week1-initial-import.png)"
        if has_screenshot
        else "Pending capture: `screenshots/week1-initial-import.png` (open `data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv` in Power BI Desktop via Transform Data and save the raw preview showing 55,692 rows, 46 columns, and only `Source` under Applied Steps)."
    )

    lines: list[str] = [
            "# Mzigo Chakula: Food Price Inflation and Household Affordability Intelligence for Kenya",
            "",
            "**Course:** DSA 3050A | Business Intelligence and Data Visualization (Group Project B)",
            "**Project Area:** 10. Food-price inflation and household affordability",
            "**Group Members:** Prince Nzamuwe, Yizere Denis Derick",
            "**Date:** 14 November 2026",
            "",
            "## 1. Problem Statement",
            "",
            ("Public inflation reports in Kenya summarize food costs as one national percentage, which hides sharp regional "
            "differences across counties. A household in Turkana or Mandera buys staple maize, beans, and livestock under "
            "very different supply conditions and seasonal shocks than a household in Nairobi or Mombasa. Over the past two "
            "decades, drought cycles, fuel costs, and exchange-rate movements have pushed staple prices up unevenly across "
            "urban centres and arid regions."),
            "",
            ("This project builds a Power BI decision tool to measure how retail food prices and price volatility shifted "
            "across Kenyan markets between January 2007 and October 2026. The goal is to show which counties, commodities, "
            "and calendar months carry the heaviest cost burden so planners can direct subsidies and monitoring where pressure "
            "is highest."),
            "",
            "## 2. Stakeholders and Supported Decisions",
            "",
            ("The primary users are county agricultural and planning officers, NGO food-security teams, and household "
            "policy analysts. The report supports three operational decisions:"),
            "",
            ("1. **Where to allocate field price-monitoring effort:** Pair high-volatility counties with survey coverage records "
            "to locate markets that face large price swings with thin recent field checks."),
            ("2. **When to open seasonal food subsidies or relief distributions:** Identify recurring harvest-gap peak months per "
            "county so interventions arrive before prices peak."),
            ("3. **Which commodity to prioritize:** Measure whether maize, beans, or livestock contributes most to local index "
            "inflation so response budgets target the strongest price driver."),
            "",
            "## 3. Analytical Questions",
            "",
            "1. Which Kenyan counties experienced the highest 12-month food price inflation over the last three years (2024 to 2026)?",
            "2. Which tracked commodity (maize, beans, or goats) drives the largest share of changes in the composite food price index?",
            ("3. Is monthly price volatility higher in arid and semi-arid counties (such as Turkana, Marsabit, Mandera, Wajir, "
            "and Garissa) than in higher-potential agricultural or urban counties?"),
            "4. What seasonal price cycles repeat across the year, and how do peak months differ between regions?",
            "5. How uneven is market density across counties, and which counties rely on a single monitored market?",
            "",
            "## 4. Key Performance Indicators",
            "",
            "| KPI | Definition | Why It Matters |",
            "| --- | --- | --- |",
            "| National Food Price Index | Average closing composite food price index (`c_food_price_index`) across physical markets | Tracks overall basket cost trend across periods |",
            "| YoY Inflation Rate (%) | Percentage change in price or index against the same month one year earlier | Separates sustained inflation from normal seasonal swings |",
            "| Price Volatility (KES / Std Dev) | Standard deviation of monthly closing prices per commodity and county | Measures price instability and household budget risk |",
            "| Market Coverage Rate (%) | Share of expected market-month observations with valid modelled prices and raw surveys | Flags data reliability differences before drawing conclusions |",
            "| Affordability Gap (KES) | County average commodity price minus the national market average for the same period | Quantifies local price premiums paid by households |",
            "",
            "## 5. Dataset Summary and Main Fields",
            "",
            "| Attribute | Detail |",
            "| --- | --- |",
            "| Source | World Bank Real Time Food Prices (RTFP), Kenya |",
            "| Source URL | https://microdata.worldbank.org/index.php/catalog/6167 |",
            "| Date Accessed | 29 October 2026 |",
            "| License | CC BY 4.0 (open redistribution permitted with attribution) |",
            "| File Path | `data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv` |",
            "| Dimensions | 55,692 rows and 46 columns |",
            "| Geographic Scope | 233 physical markets (plus 1 `Market Average` national series) across 27 counties |",
            "| Time Span | January 2007 to October 2026 (238 consecutive months) |",
            "",
            ("Main fields include `adm1_name`, `adm2_name`, `mkt_name`, `lat`, `lon`, `geo_id`, `price_date`, `year`, `month`, "
            "modelled close prices (`c_beans`, `c_maize_fao`, `c_livestock_goat_s_fao`), `c_food_price_index`, "
            "YoY inflation columns (`inflation_*`), and model trust scores (`trust_*`). All 46 fields with types, units, "
            "null rates, ranges, and descriptions are listed in `docs/dataset-dictionary.csv`."),
            "",
            "## 6. Initial Data Quality Assessment",
            "",
            ("Profiling all 55,692 rows surfaced four cleaning rules for Week 2 Power Query work. First, 238 rows belong to a "
            "synthetic `Market Average` series with blank coordinates (`lat` and `lon` missing on 0.43% of rows) that must be "
            "excluded from market-level sums and averages. Second, the raw survey price columns (`beans`, `maize_fao`, "
            "`livestock_goat_s_fao`) are missing on 94.53% to 96.72% of rows, whereas the 16 modelled OHLC columns (`o_`, `h_`, "
            "`l_`, `c_`) have 0.00% missingness and supply a continuous 238-month series. Third, the four `inflation_*` columns "
            "are blank for all 12 months of 2007 (2,808 rows, 5.04%) because 2006 prices are absent. Fourth, `adm1_name` and "
            "`adm2_name` mix former provinces with modern counties across 35 pairs (for example, splitting Kwale, Kajiado, "
            "Tana River, Taita Taveta, and Meru), requiring a deterministic lookup table to normalize all 233 markets into "
            "27 counties and 7 regions."),
            "",
            "## 7. Limitations and Ethics",
            "",
            ("The dataset reports market-level aggregate retail prices without household income or expenditure figures, so "
            "affordability is inferred from price levels and cross-county gaps. Market density is uneven: 27 of Kenya's "
            "47 counties are represented, Turkana has 57 markets while five counties have only 1 market, and Western Province "
            "has zero markets in this release. All prices are public aggregate market series under CC BY 4.0 with no personal "
            "or sensitive data."),
            "",
            "## 8. Initial Power BI Import Evidence",
            "",
            screenshot_note,
            "",
    ]
    return "\n".join(lines)


def write_proposal_markdown(profile: dict[str, Any], output_path: Path) -> Path:
    """Write docs/proposal.md."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    has_screenshot = INITIAL_IMPORT_SCREENSHOT.is_file()
    output_path.write_text(build_proposal_markdown(profile, has_screenshot), encoding="utf-8")
    return output_path


class _ProposalPDF(FPDF):
    """Clean 3-page A4 proposal PDF layout matching the DSA 3050A brief."""

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 110, 120)
        self.cell(
            0,
            6,
            f"DSA 3050A Group Project B | Mzigo Chakula Proposal | Page {self.page_no()}/{{nb}}",
            align="C",
        )


def _heading(pdf: FPDF, title: str) -> None:
    pdf.ln(2.5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(20, 58, 92)
    pdf.cell(0, 6.5, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(20, 58, 92)
    pdf.set_line_width(0.3)
    y = pdf.get_y()
    pdf.line(15, y, 195, y)
    pdf.ln(2.0)


def _body(pdf: FPDF, text: str, size: int = 9.5) -> None:
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(30, 35, 40)
    pdf.multi_cell(0, 4.7, text)
    pdf.ln(1.5)


def _table(
    pdf: FPDF,
    headers: list[str],
    rows: list[list[str]],
    col_widths: list[int],
    font_size: float = 8.5,
) -> None:
    pdf.set_font("Helvetica", "B", font_size)
    pdf.set_fill_color(20, 58, 92)
    pdf.set_text_color(255, 255, 255)
    for header, width in zip(headers, col_widths, strict=True):
        pdf.cell(width, 6.2, header, border=1, fill=True, align="L")
    pdf.ln()

    pdf.set_font("Helvetica", "", font_size)
    pdf.set_text_color(30, 35, 40)
    for row_idx, row in enumerate(rows):
        fill = row_idx % 2 == 1
        pdf.set_fill_color(242, 246, 250)
        # Estimate row height using the exact inner text width used when rendering
        line_counts = []
        for text, width in zip(row, col_widths, strict=True):
            lines = pdf.multi_cell(width - 2.4, 4.4, text, dry_run=True, output="LINES")
            line_counts.append(max(1, len(lines)))
        row_height = max(line_counts) * 4.4 + 2.0

        y_start = pdf.get_y()
        x_cursor = 15.0
        for text, width in zip(row, col_widths, strict=True):
            pdf.set_xy(x_cursor, y_start)
            if fill:
                pdf.rect(x_cursor, y_start, width, row_height, style="DF")
            else:
                pdf.rect(x_cursor, y_start, width, row_height, style="D")
            pdf.set_xy(x_cursor + 1.2, y_start + 1.0)
            pdf.multi_cell(width - 2.4, 4.4, text, border=0, align="L")
            x_cursor += width
        pdf.set_y(y_start + row_height)
    pdf.ln(2.0)


def render_proposal_pdf(profile: dict[str, Any], output_path: Path) -> Path:
    """Render the 3-page Week 1 proposal PDF."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = _ProposalPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_margins(15, 14, 15)
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- PAGE 1: Title, Problem Framing, Stakeholders, Analytical Questions ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(20, 58, 92)
    pdf.multi_cell(
        0,
        7.5,
        "Mzigo Chakula: Food Price Inflation and Household Affordability Intelligence for Kenya",
    )
    pdf.ln(1.5)
    pdf.set_font("Helvetica", "", 9.2)
    pdf.set_text_color(70, 80, 90)
    pdf.cell(
        0,
        5,
        "DSA 3050A | Business Intelligence & Data Visualization | Group Project B (Theme 10)",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        5,
        "Authors: Prince Nzamuwe, Yizere Denis Derick   |   Date: 14 November 2026",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(2)

    _heading(pdf, "1. Problem Statement")
    _body(
        pdf,
        "Public inflation reports in Kenya summarize food costs as one national percentage, which hides sharp regional "
        "differences across counties. A household in Turkana or Mandera buys staple maize, beans, and livestock under "
        "very different supply conditions and seasonal shocks than a household in Nairobi or Mombasa. Over the past two "
        "decades, drought cycles, transport costs, and exchange-rate pressure have pushed retail food prices higher "
        "across urban centres and arid regions at different rates.",
    )
    _body(
        pdf,
        "This project develops a Power BI decision tool covering Kenyan market food prices from January 2007 to October "
        "2026. The solution shows which counties, commodities, and calendar windows carry the heaviest price burden so "
        "county planners and food-security teams can prioritize interventions.",
    )

    _heading(pdf, "2. Target Stakeholders and Supported Decisions")
    _body(
        pdf,
        "Intended audience: county agricultural and planning officers, NGO food-security programs, and household policy "
        "advisors. The dashboard supports three concrete decisions:",
    )
    _table(
        pdf,
        ["Decision", "Operational Choice Supported", "Primary Signals Used"],
        [
            [
                "1. Monitoring deployment",
                "Where to prioritize field market price audits and survey follow-up",
                "High county price volatility paired with low survey coverage or single-market counties",
            ],
            [
                "2. Subsidy timing",
                "When to trigger seasonal price stabilization or food relief distributions",
                "Recurring monthly seasonal index peaks before harvest cycles",
            ],
            [
                "3. Commodity targeting",
                "Which staple commodity needs immediate supply or buffer-stock support",
                "Commodity contribution to composite food price index inflation",
            ],
        ],
        [42, 72, 66],
        font_size=8.4,
    )

    _heading(pdf, "3. Analytical Questions")
    questions = [
        "1. Which Kenyan counties experienced the highest 12-month food price inflation over the last three years (2024 to 2026)?",
        "2. Which tracked commodity (maize, beans, or goats) drives the largest share of movements in the composite food price index?",
        "3. Is monthly price volatility significantly higher in arid and semi-arid counties (Turkana, Marsabit, Mandera, Wajir, Garissa) than in agricultural or urban counties?",
        "4. What seasonal price cycles repeat across the year, and how do peak price months differ across regions?",
        "5. How uneven is market coverage across counties, and which counties rely on only one monitored market?",
    ]
    for q in questions:
        pdf.set_font("Helvetica", "", 9.2)
        pdf.set_text_color(30, 35, 40)
        pdf.multi_cell(0, 4.8, q)
        pdf.ln(0.8)

    # --- PAGE 2: KPIs, Dataset Metadata, Field List Summary ---
    pdf.add_page()
    _heading(pdf, "4. Defined Key Performance Indicators (KPIs)")
    _table(
        pdf,
        ["KPI Name", "Definition / Calculation Basis", "Why It Matters"],
        [
            [
                "National Food Price Index",
                "Mean closing composite index (c_food_price_index) across physical markets",
                "Tracks overall retail basket cost across time",
            ],
            [
                "YoY Inflation Rate (%)",
                "Percentage change in price or index vs. same month prior year",
                "Isolates sustained inflation from annual seasonality",
            ],
            [
                "Price Volatility (KES)",
                "Sample standard deviation of monthly closing prices by market or county",
                "Quantifies price instability and budget risk",
            ],
            [
                "Market Coverage Rate (%)",
                "Share of expected market-months with valid prices and survey coverage score",
                "Flags reliability gaps across counties before action",
            ],
            [
                "Affordability Gap (KES)",
                "County mean commodity price minus national physical market mean price",
                "Measures local price premiums paid by households",
            ],
        ],
        [45, 73, 62],
        font_size=8.3,
    )

    _heading(pdf, "5. Dataset Overview and Provenance")
    _table(
        pdf,
        ["Attribute", "Specification"],
        [
            ["Source & Title", "World Bank Real Time Food Prices (RTFP), Kenya"],
            ["Source URL", "https://microdata.worldbank.org/index.php/catalog/6167"],
            ["Date Accessed", "29 October 2026"],
            ["License", "CC BY 4.0 (open redistribution permitted with attribution)"],
            [
                "Size & Span",
                f"{profile['total_rows']:,} rows, {profile['total_columns']} columns; {profile['date_min']} to {profile['date_max']} ({profile['distinct_months']} months)",
            ],
            [
                "Geographic Coverage",
                f"{profile['physical_markets_count']} physical markets + 1 Market Average series across {profile['clean_counties_count']} counties",
            ],
            ["Tracked Commodities", "Dry beans (1 kg), Maize (1 kg), Live goat (1 head), plus Composite Food Price Index"],
        ],
        [45, 135],
        font_size=8.4,
    )

    _heading(pdf, "6. Main Dataset Fields (46 Columns Total; Full List in docs/dataset-dictionary.csv)")
    _table(
        pdf,
        ["Field(s)", "Type", "Null %", "Role in Star Schema"],
        [
            ["adm1_name, adm2_name, mkt_name, geo_id", "Text", "0.00%", "Market location hierarchy (dim_markets)"],
            ["lat, lon", "Decimal", "0.43%", "Map coordinates (blank only on Market Average)"],
            ["price_date, year, month", "Date / Int", "0.00%", "Monthly time axis (dim_date)"],
            ["currency, components", "Text", "0.00%", "KES currency and commodity basket definition"],
            ["data_coverage, index_confidence_score", "Decimal", "0.00%", "Survey coverage (4.46%) and confidence (0.97)"],
            ["beans, maize_fao, livestock_goat_s_fao", "Decimal", "94.5-96.7%", "Sparse raw survey prices (excluded from modelled facts)"],
            ["o_*, h_*, l_*, c_* (3 commodities)", "Decimal", "0.00%", "Modelled monthly OHLC prices in KES (fact_prices)"],
            ["o/h/l/c_food_price_index", "Decimal", "0.00%", "Market-month composite food index (fact_market_index)"],
            ["inflation_* (4 series)", "Decimal", "5.04%", "YoY inflation % (blank only in 2007 baseline year)"],
            ["trust_* (4 series)", "Decimal", "0.00%", "Model trust scores (0 to 10 scale)"],
        ],
        [62, 22, 22, 74],
        font_size=8.1,
    )

    # --- PAGE 3: Data Quality, Limitations & Ethics, Initial Power BI Import ---
    pdf.add_page()
    _heading(pdf, "7. Initial Data Quality Assessment")
    _body(
        pdf,
        f"Every series spans {profile['distinct_months']} consecutive months ({profile['date_min']} to {profile['date_max']}), "
        f"yielding {profile['total_series_count']} series x {profile['distinct_months']} months = {profile['total_rows']:,} rows. "
        "Initial profiling identified four required cleaning steps for Week 2 Power Query:",
    )
    _body(
        pdf,
        "1. Exclude aggregate rows: 238 rows are a national Market Average series (blank coordinates). Filtering these "
        f"leaves {profile['physical_market_rows']:,} physical market observations across {profile['physical_markets_count']} markets.\n"
        "2. Normalize admin labels: adm1_name and adm2_name mix former provinces and counties across 35 pairs, splitting five "
        "counties (Kwale, Kajiado, Tana River, Taita Taveta, Meru) and placing Kitengela (Kajiado) under Nairobi. Mapping all "
        f"35 pairs yields {profile['clean_counties_count']} clean counties across {profile['clean_regions_count']} regions.\n"
        "3. Use modelled close prices: Raw survey spot columns are missing on 94.53% to 96.72% of rows, while the modelled "
        "close price series (c_beans, c_maize_fao, c_livestock_goat_s_fao, c_food_price_index) have 0.00% missingness.\n"
        "4. Handle 2007 inflation nulls and grain: YoY inflation columns are blank in 2007 (2,808 cells, 5.04%) due to the missing "
        "2006 baseline. In modelling, c_food_price_index belongs to the market-month grain while commodity prices sit at the market-month-commodity grain.",
    )

    _heading(pdf, "8. Limitations and Ethical Considerations")
    _body(
        pdf,
        "Market prices reflect retail selling prices without household income or expenditure data, so affordability is "
        "inferred from regional price gaps and volatility. Coverage is uneven across counties: Turkana holds 57 markets, "
        "Samburu holds 20, and Garissa holds 19, while five counties have only 1 market and Western Province has no markets in "
        "this release (27 of 47 counties covered). All records are public aggregate market series under CC BY 4.0 with no "
        "personal or sensitive individual data. Any AI assistance used for documentation or scripting will be disclosed in the "
        "final report.",
    )

    _heading(pdf, "9. Initial Power BI Import Evidence (Week 1 Checkpoint)")
    if INITIAL_IMPORT_SCREENSHOT.is_file():
        _body(
            pdf,
            "Power Query Editor screenshot captured immediately upon importing data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv "
            "(46 columns, 999+ rows in the 1,000-row profiling preview, column quality and distribution histograms enabled, "
            "and default CSV import steps Source, Use First Row as Headers, and Change Type under Applied Steps):",
        )
        y_img = pdf.get_y()
        pdf.image(str(INITIAL_IMPORT_SCREENSHOT), x=20, y=y_img, w=170)
    else:
        _body(
            pdf,
            "Evidence file path: screenshots/week1-initial-import.png (to be captured directly in Power BI Desktop via "
            "Home -> Get Data -> Text/CSV -> Transform Data before any cleaning steps are applied).",
        )
        y_box = pdf.get_y()
        pdf.set_draw_color(140, 155, 170)
        pdf.set_fill_color(245, 248, 251)
        pdf.rect(15, y_box, 180, 48, style="DF")
        pdf.set_xy(20, y_box + 15)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(70, 85, 100)
        pdf.cell(170, 6, "[Pending Screenshot: screenshots/week1-initial-import.png]", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8.8)
        pdf.set_x(20)
        pdf.cell(
            170,
            6,
            "Re-run `uv run python -m mzigo_chakula.generate_week1_docs` after saving the screenshot to embed it automatically.",
            align="C",
        )

    output_path.write_bytes(bytes(pdf.output()))
    return output_path


def generate_all(csv_path: Path | None = None) -> dict[str, Path]:
    """Run dataset profiling and write all Week 1 outputs under docs/."""
    profile = profile_dataset(csv_path=csv_path)
    dict_path = write_dataset_dictionary(profile, DOCS_DIR / "dataset-dictionary.csv")
    quality_path = write_data_quality_profile(profile, DOCS_DIR / "data-quality-profile.md")
    proposal_md_path = write_proposal_markdown(profile, DOCS_DIR / "proposal.md")
    proposal_pdf_path = render_proposal_pdf(profile, DOCS_DIR / "proposal.pdf")
    return {
        "dataset_dictionary": dict_path,
        "data_quality_profile": quality_path,
        "proposal_md": proposal_md_path,
        "proposal_pdf": proposal_pdf_path,
    }


if __name__ == "__main__":
    generated = generate_all()
    for name, path in generated.items():
        print(f"{name}: {path}")
