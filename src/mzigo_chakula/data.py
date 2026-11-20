"""Central dataset loading, schema validation, geographic normalization, and profiling."""

from __future__ import annotations

import csv
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_CSV = PROJECT_ROOT / "data" / "raw" / "KEN_RTFP_mkt_2007_2026-10-05.csv"

EXPECTED_COLUMNS: tuple[str, ...] = (
    "ISO3",
    "country",
    "adm1_name",
    "adm2_name",
    "mkt_name",
    "lat",
    "lon",
    "geo_id",
    "price_date",
    "year",
    "month",
    "currency",
    "components",
    "start_dense_data",
    "last_survey_point",
    "data_coverage",
    "data_coverage_recent",
    "index_confidence_score",
    "spatially_interpolated",
    "beans",
    "livestock_goat_s_fao",
    "maize_fao",
    "o_beans",
    "h_beans",
    "l_beans",
    "c_beans",
    "inflation_beans",
    "trust_beans",
    "o_livestock_goat_s_fao",
    "h_livestock_goat_s_fao",
    "l_livestock_goat_s_fao",
    "c_livestock_goat_s_fao",
    "inflation_livestock_goat_s_fao",
    "trust_livestock_goat_s_fao",
    "o_maize_fao",
    "h_maize_fao",
    "l_maize_fao",
    "c_maize_fao",
    "inflation_maize_fao",
    "trust_maize_fao",
    "o_food_price_index",
    "h_food_price_index",
    "l_food_price_index",
    "c_food_price_index",
    "inflation_food_price_index",
    "trust_food_price_index",
)

# Maps raw (adm1_name, adm2_name) pairs to (clean_region, clean_county, subcounty_note).
# The source mixes former provinces and current counties across both columns.
COUNTY_MAPPING: dict[tuple[str, str], tuple[str, str, str]] = {
    ("Central", "Nyeri"): ("Central", "Nyeri", "Nyeri"),
    ("Coast", "Kilifi"): ("Coast", "Kilifi", "Kilifi"),
    ("Coast", "Kwale"): ("Coast", "Kwale", "Kwale"),
    ("Coast", "Mombasa"): ("Coast", "Mombasa", "Mombasa"),
    ("Coast", "Taita Taveta"): ("Coast", "Taita Taveta", "Taita Taveta"),
    ("Coast", "Tana River"): ("Coast", "Tana River", "Tana River"),
    ("Eastern", "Isiolo"): ("Eastern", "Isiolo", "Isiolo"),
    ("Eastern", "Kitui"): ("Eastern", "Kitui", "Kitui"),
    ("Eastern", "Machakos"): ("Eastern", "Machakos", "Machakos"),
    ("Eastern", "Makueni"): ("Eastern", "Makueni", "Makueni"),
    ("Eastern", "Marsabit"): ("Eastern", "Marsabit", "Marsabit"),
    ("Eastern", "Meru North"): ("Eastern", "Meru", "Meru North"),
    ("Eastern", "Meru South"): ("Eastern", "Tharaka Nithi", "Meru South"),
    ("Eastern", "Moyale"): ("Eastern", "Marsabit", "Moyale"),
    ("Embu", "Mbeere North"): ("Eastern", "Embu", "Mbeere North"),
    ("Hola (Tana River)", "Hola (Tana River)"): ("Coast", "Tana River", "Hola"),
    ("Kajiado", "Ongata Rongai"): ("Rift Valley", "Kajiado", "Ongata Rongai"),
    ("Kwale", "Matuga"): ("Coast", "Kwale", "Matuga"),
    ("Lamu", "Lamu West"): ("Coast", "Lamu", "Lamu West"),
    ("Market Average", "Market Average"): (
        "National Aggregate",
        "National Aggregate",
        "Market Average",
    ),
    ("Meru", "North Imenti"): ("Eastern", "Meru", "North Imenti"),
    ("Nairobi", "Nairobi"): ("Nairobi", "Nairobi", "Nairobi"),
    ("North Eastern", "Garissa"): ("North Eastern", "Garissa", "Garissa"),
    ("North Eastern", "Ijara"): ("North Eastern", "Garissa", "Ijara"),
    ("North Eastern", "Mandera"): ("North Eastern", "Mandera", "Mandera"),
    ("North Eastern", "Wajir"): ("North Eastern", "Wajir", "Wajir"),
    ("Nyanza", "Kisumu"): ("Nyanza", "Kisumu", "Kisumu"),
    ("Rift Valley", "Baringo"): ("Rift Valley", "Baringo", "Baringo"),
    ("Rift Valley", "Kajiado"): ("Rift Valley", "Kajiado", "Kajiado"),
    ("Rift Valley", "Nakuru"): ("Rift Valley", "Nakuru", "Nakuru"),
    ("Rift Valley", "Samburu"): ("Rift Valley", "Samburu", "Samburu"),
    ("Rift Valley", "Turkana"): ("Rift Valley", "Turkana", "Turkana"),
    ("Rift Valley", "Uasin Gishu"): ("Rift Valley", "Uasin Gishu", "Uasin Gishu"),
    ("Rift Valley", "West Pokot"): ("Rift Valley", "West Pokot", "West Pokot"),
    ("Taita Taveta", "Voi"): ("Coast", "Taita Taveta", "Voi"),
    ("Tharaka Nithi", "Chuka/Igambang'Ombe"): (
        "Eastern",
        "Tharaka Nithi",
        "Chuka/Igambang'Ombe",
    ),
}

# Market-level overrides where a single market sits in an adjacent county in the source.
MARKET_COUNTY_OVERRIDES: dict[str, tuple[str, str, str]] = {
    "Kitengela (Kajiado)": ("Rift Valley", "Kajiado", "Kitengela"),
}


@dataclass(frozen=True)
class ColumnSpec:
    """Metadata describing one raw column in the Kenya RTFP CSV."""

    data_type: str
    table_target: str
    unit: str
    description: str


COLUMN_SPECS: dict[str, ColumnSpec] = {
    "ISO3": ColumnSpec("text", "dim_markets", "-", "ISO 3166-1 alpha-3 country code (KEN)."),
    "country": ColumnSpec("text", "dim_markets", "-", "Country name (Kenya)."),
    "adm1_name": ColumnSpec(
        "text",
        "dim_markets",
        "-",
        "Raw level-1 administrative label; mixes former provinces and counties.",
    ),
    "adm2_name": ColumnSpec(
        "text",
        "dim_markets",
        "-",
        "Raw level-2 administrative label; mixes counties and sub-counties.",
    ),
    "mkt_name": ColumnSpec(
        "text",
        "dim_markets",
        "-",
        "Market name, or Market Average for the national summary series.",
    ),
    "lat": ColumnSpec(
        "decimal",
        "dim_markets",
        "degrees",
        "Market latitude coordinate; blank for Market Average rows.",
    ),
    "lon": ColumnSpec(
        "decimal",
        "dim_markets",
        "degrees",
        "Market longitude coordinate; blank for Market Average rows.",
    ),
    "geo_id": ColumnSpec(
        "text",
        "dim_markets",
        "-",
        "World Bank RTFP location identifier for each market or national average.",
    ),
    "price_date": ColumnSpec(
        "date",
        "dim_date / fact_prices",
        "YYYY-MM-DD",
        "Monthly observation date stored as ISO text in the raw CSV.",
    ),
    "year": ColumnSpec("integer", "dim_date", "year", "Calendar year (2007 to 2026)."),
    "month": ColumnSpec("integer", "dim_date", "month", "Calendar month number (1 to 12)."),
    "currency": ColumnSpec("text", "fact_prices", "KES", "Local currency code (KES)."),
    "components": ColumnSpec(
        "text",
        "dim_commodity",
        "-",
        "Commodities, measurement units, and weights used in the RTFP food price index.",
    ),
    "start_dense_data": ColumnSpec(
        "text",
        "metadata",
        "-",
        "Start month of the dense price series (Jan 2007).",
    ),
    "last_survey_point": ColumnSpec(
        "text",
        "metadata",
        "-",
        "Latest survey observation month in the release (Sep 2026).",
    ),
    "data_coverage": ColumnSpec(
        "decimal",
        "dim_markets",
        "%",
        "Share of months with raw survey observations across the full span (4.46%).",
    ),
    "data_coverage_recent": ColumnSpec(
        "decimal",
        "dim_markets",
        "%",
        "Share of recent months with raw survey observations (5.45%).",
    ),
    "index_confidence_score": ColumnSpec(
        "decimal",
        "dim_markets",
        "0-1",
        "Overall RTFP model confidence score for the country release (0.97).",
    ),
    "spatially_interpolated": ColumnSpec(
        "integer",
        "dim_markets",
        "0/1",
        "Flag indicating spatial interpolation (0 across all rows in this release).",
    ),
    "beans": ColumnSpec(
        "decimal",
        "fact_prices (raw)",
        "KES / 1 kg",
        "Raw observed retail price for dry beans (96.72% missing).",
    ),
    "livestock_goat_s_fao": ColumnSpec(
        "decimal",
        "fact_prices (raw)",
        "KES / 1 head",
        "Raw observed market price for a live goat (95.33% missing).",
    ),
    "maize_fao": ColumnSpec(
        "decimal",
        "fact_prices (raw)",
        "KES / 1 kg",
        "Raw observed retail price for maize (94.53% missing).",
    ),
    "o_beans": ColumnSpec(
        "decimal", "fact_prices", "KES / 1 kg", "Modeled monthly opening price for beans."
    ),
    "h_beans": ColumnSpec(
        "decimal", "fact_prices", "KES / 1 kg", "Modeled monthly high price for beans."
    ),
    "l_beans": ColumnSpec(
        "decimal", "fact_prices", "KES / 1 kg", "Modeled monthly low price for beans."
    ),
    "c_beans": ColumnSpec(
        "decimal", "fact_prices", "KES / 1 kg", "Modeled monthly closing price for beans."
    ),
    "inflation_beans": ColumnSpec(
        "decimal",
        "fact_prices",
        "%",
        "Year-over-year percentage inflation for beans; blank in 2007.",
    ),
    "trust_beans": ColumnSpec(
        "decimal", "fact_prices", "0-10", "Model trust score for beans price estimates."
    ),
    "o_livestock_goat_s_fao": ColumnSpec(
        "decimal", "fact_prices", "KES / 1 head", "Modeled monthly opening price for a goat."
    ),
    "h_livestock_goat_s_fao": ColumnSpec(
        "decimal", "fact_prices", "KES / 1 head", "Modeled monthly high price for a goat."
    ),
    "l_livestock_goat_s_fao": ColumnSpec(
        "decimal", "fact_prices", "KES / 1 head", "Modeled monthly low price for a goat."
    ),
    "c_livestock_goat_s_fao": ColumnSpec(
        "decimal", "fact_prices", "KES / 1 head", "Modeled monthly closing price for a goat."
    ),
    "inflation_livestock_goat_s_fao": ColumnSpec(
        "decimal",
        "fact_prices",
        "%",
        "Year-over-year percentage inflation for goats; blank in 2007.",
    ),
    "trust_livestock_goat_s_fao": ColumnSpec(
        "decimal", "fact_prices", "0-10", "Model trust score for goat price estimates."
    ),
    "o_maize_fao": ColumnSpec(
        "decimal", "fact_prices", "KES / 1 kg", "Modeled monthly opening price for maize."
    ),
    "h_maize_fao": ColumnSpec(
        "decimal", "fact_prices", "KES / 1 kg", "Modeled monthly high price for maize."
    ),
    "l_maize_fao": ColumnSpec(
        "decimal", "fact_prices", "KES / 1 kg", "Modeled monthly low price for maize."
    ),
    "c_maize_fao": ColumnSpec(
        "decimal", "fact_prices", "KES / 1 kg", "Modeled monthly closing price for maize."
    ),
    "inflation_maize_fao": ColumnSpec(
        "decimal",
        "fact_prices",
        "%",
        "Year-over-year percentage inflation for maize; blank in 2007.",
    ),
    "trust_maize_fao": ColumnSpec(
        "decimal", "fact_prices", "0-10", "Model trust score for maize price estimates."
    ),
    "o_food_price_index": ColumnSpec(
        "decimal",
        "raw source (unused)",
        "index",
        "Modeled monthly opening composite food price index.",
    ),
    "h_food_price_index": ColumnSpec(
        "decimal",
        "raw source (unused)",
        "index",
        "Modeled monthly high composite food price index.",
    ),
    "l_food_price_index": ColumnSpec(
        "decimal",
        "raw source (unused)",
        "index",
        "Modeled monthly low composite food price index.",
    ),
    "c_food_price_index": ColumnSpec(
        "decimal",
        "fact_prices (market-month grain)",
        "index",
        "Modeled monthly closing composite food price index.",
    ),
    "inflation_food_price_index": ColumnSpec(
        "decimal",
        "fact_prices (market-month grain)",
        "%",
        "Year-over-year change in composite food price index; blank in 2007.",
    ),
    "trust_food_price_index": ColumnSpec(
        "decimal",
        "raw source (unused)",
        "0-10",
        "Model trust score for the composite food price index.",
    ),
}


def resolve_geography(adm1_name: str, adm2_name: str, mkt_name: str) -> tuple[str, str, str]:
    """Resolve raw source admin labels and market overrides to (region, county, subcounty)."""
    if mkt_name in MARKET_COUNTY_OVERRIDES:
        return MARKET_COUNTY_OVERRIDES[mkt_name]
    key = (adm1_name, adm2_name)
    if key not in COUNTY_MAPPING:
        raise ValueError(f"Unmapped administrative pair: {key} for market {mkt_name!r}")
    return COUNTY_MAPPING[key]


def load_data(
    csv_path: Path | str | None = None,
    include_market_average: bool = False,
) -> list[dict[str, str]]:
    """Load the Kenya RTFP CSV, validate its 46-column schema, and normalize geography.

    Args:
        csv_path: Path to the raw CSV file. Defaults to the tracked World Bank RTFP file.
        include_market_average: Whether to keep the 238 national Market Average rows.

    Returns:
        List of row dictionaries enriched with ``clean_region``, ``clean_county``,
        and ``subcounty_note``.
    """
    target = Path(csv_path) if csv_path is not None else DEFAULT_RAW_CSV
    if not target.is_file():
        raise FileNotFoundError(f"Dataset file not found: {target}")

    with target.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or tuple(reader.fieldnames) != EXPECTED_COLUMNS:
            raise ValueError(
                f"Schema mismatch in {target}. Expected {len(EXPECTED_COLUMNS)} columns, "
                f"got {len(reader.fieldnames or ())}."
            )

        rows: list[dict[str, str]] = []
        for raw_row in reader:
            if not include_market_average and raw_row["mkt_name"] == "Market Average":
                continue
            region, county, subcounty = resolve_geography(
                raw_row["adm1_name"],
                raw_row["adm2_name"],
                raw_row["mkt_name"],
            )
            enriched = dict(raw_row)
            enriched["clean_region"] = region
            enriched["clean_county"] = county
            enriched["subcounty_note"] = subcounty
            rows.append(enriched)

    if not rows:
        raise ValueError(f"Dataset {target} yielded zero rows.")
    return rows


def _summarize_numeric(values: list[float]) -> dict[str, float]:
    """Return deterministic summary statistics for a non-empty list of floats."""
    n = len(values)
    mean_val = sum(values) / n
    median_val = statistics.median(values)
    variance = sum((v - mean_val) ** 2 for v in values) / (n - 1) if n > 1 else 0.0
    return {
        "count": n,
        "min": min(values),
        "median": median_val,
        "mean": mean_val,
        "max": max(values),
        "std": math.sqrt(variance),
    }


def profile_dataset(csv_path: Path | str | None = None) -> dict[str, Any]:
    """Compute full dataset and column-level profiling metrics without mutating raw files."""
    all_rows = load_data(csv_path=csv_path, include_market_average=True)
    market_rows = [r for r in all_rows if r["mkt_name"] != "Market Average"]
    avg_rows = [r for r in all_rows if r["mkt_name"] == "Market Average"]

    total_count = len(all_rows)
    column_profiles: list[dict[str, Any]] = []
    for idx, col in enumerate(EXPECTED_COLUMNS, start=1):
        spec = COLUMN_SPECS[col]
        non_empty = [r[col] for r in all_rows if r[col] != ""]
        non_null_count = len(non_empty)
        null_count = total_count - non_null_count
        pct_missing = (null_count / total_count) * 100.0
        unique_values = len(set(non_empty))
        sample_value = non_empty[0] if non_empty else ""

        min_val = ""
        max_val = ""
        mean_val = ""
        median_val = ""
        std_val = ""
        if non_empty:
            if spec.data_type in {"decimal", "integer"}:
                nums = [float(v) for v in non_empty]
                stats = _summarize_numeric(nums)
                if spec.data_type == "integer":
                    min_val = str(int(stats["min"]))
                    max_val = str(int(stats["max"]))
                else:
                    min_val = f"{stats['min']:.4f}".rstrip("0").rstrip(".")
                    max_val = f"{stats['max']:.4f}".rstrip("0").rstrip(".")
                mean_val = f"{stats['mean']:.2f}"
                median_val = f"{stats['median']:.2f}"
                std_val = f"{stats['std']:.2f}"
            else:
                min_val = min(non_empty)
                max_val = max(non_empty)

        column_profiles.append(
            {
                "col_index": idx,
                "column_name": col,
                "data_type": spec.data_type,
                "table_target": spec.table_target,
                "unit": spec.unit,
                "non_null_count": non_null_count,
                "null_count": null_count,
                "pct_missing": round(pct_missing, 2),
                "unique_values": unique_values,
                "min_value": min_val,
                "max_value": max_val,
                "mean_value": mean_val,
                "median_value": median_val,
                "std_value": std_val,
                "sample_value": sample_value,
                "description": spec.description,
            }
        )

    # Geographic mapping summary on physical markets
    pair_markets: dict[tuple[str, str], set[str]] = defaultdict(set)
    pair_rows: Counter[tuple[str, str]] = Counter()
    county_markets: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in market_rows:
        pair = (row["adm1_name"], row["adm2_name"])
        pair_markets[pair].add(row["mkt_name"])
        pair_rows[pair] += 1
        county_markets[(row["clean_region"], row["clean_county"])].add(row["mkt_name"])

    geography_mapping_summary = []
    for pair in sorted(pair_markets):
        region, county, note = COUNTY_MAPPING[pair]
        geography_mapping_summary.append(
            {
                "raw_adm1": pair[0],
                "raw_adm2": pair[1],
                "clean_region": region,
                "clean_county": county,
                "subcounty_note": note,
                "market_count": len(pair_markets[pair]),
                "row_count": pair_rows[pair],
            }
        )

    county_coverage = [
        {
            "region": region,
            "county": county,
            "market_count": len(mkts),
            "sample_markets": ", ".join(sorted(mkts)[:3]),
        }
        for (region, county), mkts in sorted(county_markets.items())
    ]

    # Numeric distributions on physical markets (excluding Market Average rows)
    price_fields = (
        "c_beans",
        "c_maize_fao",
        "c_livestock_goat_s_fao",
        "c_food_price_index",
        "inflation_beans",
        "inflation_maize_fao",
        "inflation_livestock_goat_s_fao",
        "inflation_food_price_index",
    )
    market_metric_stats: dict[str, dict[str, float]] = {}
    for field in price_fields:
        vals = [float(r[field]) for r in market_rows if r[field] != ""]
        market_metric_stats[field] = _summarize_numeric(vals)

    dates = sorted({r["price_date"] for r in all_rows})
    months_per_market = Counter(r["mkt_name"] for r in market_rows)

    return {
        "total_rows": total_count,
        "total_columns": len(EXPECTED_COLUMNS),
        "physical_market_rows": len(market_rows),
        "market_average_rows": len(avg_rows),
        "physical_markets_count": len({r["mkt_name"] for r in market_rows}),
        "total_series_count": len({r["mkt_name"] for r in all_rows}),
        "clean_counties_count": len({r["clean_county"] for r in market_rows}),
        "clean_regions_count": len({r["clean_region"] for r in market_rows}),
        "raw_admin_pairs_count": len(pair_markets),
        "date_min": dates[0],
        "date_max": dates[-1],
        "distinct_months": len(dates),
        "min_months_per_market": min(months_per_market.values()),
        "max_months_per_market": max(months_per_market.values()),
        "column_profiles": column_profiles,
        "geography_mapping_summary": geography_mapping_summary,
        "county_coverage": county_coverage,
        "market_metric_stats": market_metric_stats,
    }
