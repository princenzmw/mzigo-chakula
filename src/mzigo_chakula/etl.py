"""Deterministic ETL pipeline implementing all 10 Week 2 Power Query transformations."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from mzigo_chakula.data import load_data

MONTH_ABBREVIATIONS: tuple[str, ...] = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)

ASAL_COUNTIES: frozenset[str] = frozenset(
    {
        "Turkana",
        "Marsabit",
        "Mandera",
        "Wajir",
        "Garissa",
        "Isiolo",
        "Samburu",
        "Tana River",
        "Baringo",
        "West Pokot",
        "Kajiado",
        "Kitui",
        "Makueni",
        "Taita Taveta",
        "Kwale",
        "Kilifi",
        "Laikipia",
    }
)


@dataclass(frozen=True)
class CommoditySpec:
    """Mapping between raw RTFP commodity columns and dim_commodity attributes."""

    commodity_id: str
    commodity_name: str
    category: str
    unit: str
    close_col: str
    open_col: str
    high_col: str
    low_col: str
    raw_col: str
    inflation_col: str
    trust_col: str
    index_weight_note: str


COMMODITY_SPECS: tuple[CommoditySpec, ...] = (
    CommoditySpec(
        commodity_id="beans",
        commodity_name="Beans (1 kg)",
        category="Legume Staple",
        unit="KG",
        close_col="c_beans",
        open_col="o_beans",
        high_col="h_beans",
        low_col="l_beans",
        raw_col="beans",
        inflation_col="inflation_beans",
        trust_col="trust_beans",
        index_weight_note="RTFP basket item: beans (1 KG, Index Weight = 1)",
    ),
    CommoditySpec(
        commodity_id="maize_fao",
        commodity_name="Maize (1 kg)",
        category="Cereal Staple",
        unit="KG",
        close_col="c_maize_fao",
        open_col="o_maize_fao",
        high_col="h_maize_fao",
        low_col="l_maize_fao",
        raw_col="maize_fao",
        inflation_col="inflation_maize_fao",
        trust_col="trust_maize_fao",
        index_weight_note="RTFP basket item: maize_fao (1 Kg, Index Weight = 1)",
    ),
    CommoditySpec(
        commodity_id="livestock_goat_s_fao",
        commodity_name="Goat (1 head)",
        category="Livestock / Protein",
        unit="Head",
        close_col="c_livestock_goat_s_fao",
        open_col="o_livestock_goat_s_fao",
        high_col="h_livestock_goat_s_fao",
        low_col="l_livestock_goat_s_fao",
        raw_col="livestock_goat_s_fao",
        inflation_col="inflation_livestock_goat_s_fao",
        trust_col="trust_livestock_goat_s_fao",
        index_weight_note="RTFP basket item: livestock_goat_s_fao (1 unit, Index Weight = 0)",
    ),
)


@dataclass(frozen=True)
class ETLResult:
    """Cleaned star-schema tables and verification metrics produced by Week 2 ETL."""

    dim_markets: list[dict[str, Any]]
    dim_date: list[dict[str, Any]]
    dim_commodity: list[dict[str, Any]]
    fact_prices: list[dict[str, Any]]
    qa_metrics: dict[str, Any]


def _parse_float(value: str) -> float | None:
    """Convert non-empty numeric string to float, or return None for blank cells."""
    stripped = value.strip()
    if not stripped:
        return None
    return float(stripped)


def _require_float(value: str, column_name: str, row_context: str) -> float:
    """Parse a required numeric field or raise ValueError when blank."""
    parsed = _parse_float(value)
    if parsed is None:
        raise ValueError(f"Expected non-null float in {column_name} for {row_context}")
    return parsed


def classify_county_group(county_name: str) -> str:
    """Classify a Kenyan county as ASAL or Agricultural & Urban."""
    return "Arid & Semi-Arid (ASAL)" if county_name in ASAL_COUNTIES else "Agricultural & Urban"


def classify_kenya_season(month: int) -> str:
    """Map calendar month (1 to 12) to Kenyan agricultural seasonality windows."""
    if month in (1, 2):
        return "Hot Dry / Lean (Jan-Feb)"
    if month in (3, 4, 5):
        return "Long Rains (Mar-May)"
    if month in (6, 7, 8, 9):
        return "Cool Dry / Harvest (Jun-Sep)"
    if month in (10, 11, 12):
        return "Short Rains (Oct-Dec)"
    raise ValueError(f"Invalid calendar month: {month}")


def _date_to_key(parsed_date: date) -> int:
    """Convert a Python date to integer YYYYMMDD surrogate key."""
    return parsed_date.year * 10000 + parsed_date.month * 100 + parsed_date.day


def _build_dim_markets(physical_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Build distinct 233-row market dimension from normalized physical rows."""
    seen: dict[str, dict[str, Any]] = {}
    for row in physical_rows:
        mkt_id = row["geo_id"]
        if mkt_id in seen:
            continue
        county_name = row["clean_county"]
        seen[mkt_id] = {
            "mkt_id": mkt_id,
            "mkt_name": row["mkt_name"],
            "adm1_name": row["clean_region"],
            "adm2_name": county_name,
            "subcounty_or_district": row["subcounty_note"],
            "raw_adm1_name": row["adm1_name"],
            "raw_adm2_name": row["adm2_name"],
            "county_group": classify_county_group(county_name),
            "lat": _require_float(row["lat"], "lat", mkt_id),
            "lon": _require_float(row["lon"], "lon", mkt_id),
            "data_coverage": _require_float(row["data_coverage"], "data_coverage", mkt_id),
            "data_coverage_recent": _require_float(
                row["data_coverage_recent"],
                "data_coverage_recent",
                mkt_id,
            ),
        }
    return sorted(seen.values(), key=lambda item: (item["adm2_name"], item["mkt_name"]))


def _build_dim_date(physical_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Build 238-row monthly calendar dimension with Kenya seasons and recency flags."""
    distinct_dates = sorted({date.fromisoformat(row["price_date"]) for row in physical_rows})
    if not distinct_dates:
        raise ValueError("Cannot build dim_date from empty dataset")

    recent_12m_cutoff = set(distinct_dates[-12:])
    last_36m_cutoff = set(distinct_dates[-36:])

    records: list[dict[str, Any]] = []
    for d in distinct_dates:
        records.append(
            {
                "date_key": _date_to_key(d),
                "full_date": d.isoformat(),
                "year": d.year,
                "month": d.month,
                "month_name": MONTH_ABBREVIATIONS[d.month - 1],
                "year_month": f"{d.year:04d}-{d.month:02d}",
                "quarter": f"Q{(d.month - 1) // 3 + 1}",
                "season": classify_kenya_season(d.month),
                "is_recent": d in recent_12m_cutoff,
                "is_last_36m": d in last_36m_cutoff,
            }
        )
    return records


def _build_dim_commodity() -> list[dict[str, Any]]:
    """Build 3-row commodity dimension matching RTFP staple categories and units."""
    return [
        {
            "commodity_id": spec.commodity_id,
            "commodity_name": spec.commodity_name,
            "category": spec.category,
            "unit": spec.unit,
            "index_weight_note": spec.index_weight_note,
        }
        for spec in COMMODITY_SPECS
    ]


def _enrich_series_metrics(series_rows: list[dict[str, Any]]) -> None:
    """Compute MoM price changes, z-scores, and outlier flags in-place for one series."""
    series_rows.sort(key=lambda item: item["date_key"])
    prices = [float(item["price_value"]) for item in series_rows]
    n = len(prices)
    mean_price = sum(prices) / n
    variance = sum((p - mean_price) ** 2 for p in prices) / (n - 1) if n > 1 else 0.0
    std_price = math.sqrt(variance)

    for idx, row in enumerate(series_rows):
        current_price = float(row["price_value"])
        if idx == 0:
            mom_abs = None
            mom_pct = None
        else:
            prev_price = float(series_rows[idx - 1]["price_value"])
            mom_abs = round(current_price - prev_price, 4)
            mom_pct = round(((current_price - prev_price) / prev_price) * 100.0, 4) if prev_price else None

        z_val = round((current_price - mean_price) / std_price, 4) if std_price > 0.0 else 0.0
        large_jump = mom_pct is not None and abs(mom_pct) > 50.0
        extreme_z = abs(z_val) > 3.0

        row["price_change_mom"] = mom_abs
        row["price_change_mom_pct"] = mom_pct
        row["z_score"] = z_val
        row["is_outlier"] = large_jump or extreme_z


def _build_fact_prices(physical_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Unpivot commodity columns and enrich each market-commodity series."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for row in physical_rows:
        mkt_id = row["geo_id"]
        parsed_date = date.fromisoformat(row["price_date"])
        date_key = _date_to_key(parsed_date)
        ctx = f"{mkt_id}@{row['price_date']}"
        food_idx = _require_float(row["c_food_price_index"], "c_food_price_index", ctx)
        idx_inflation = _parse_float(row["inflation_food_price_index"])

        for spec in COMMODITY_SPECS:
            close_val = _parse_float(row[spec.close_col])
            if close_val is None:
                continue
            record: dict[str, Any] = {
                "price_id": f"{mkt_id}_{date_key}_{spec.commodity_id}",
                "mkt_id": mkt_id,
                "date_key": date_key,
                "commodity_id": spec.commodity_id,
                "price_value": close_val,
                "open_price": _require_float(row[spec.open_col], spec.open_col, ctx),
                "high_price": _require_float(row[spec.high_col], spec.high_col, ctx),
                "low_price": _require_float(row[spec.low_col], spec.low_col, ctx),
                "raw_spot_price": _parse_float(row[spec.raw_col]),
                "commodity_inflation_yoy": _parse_float(row[spec.inflation_col]),
                "food_price_index": food_idx,
                "inflation_food_price_index": idx_inflation,
                "trust_score": _require_float(row[spec.trust_col], spec.trust_col, ctx),
            }
            grouped[(mkt_id, spec.commodity_id)].append(record)

    fact_rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        series_rows = grouped[key]
        _enrich_series_metrics(series_rows)
        fact_rows.extend(series_rows)
    return fact_rows


def _count_duplicates(records: list[dict[str, Any]], key_field: str) -> int:
    """Count duplicate primary key values in a table."""
    seen: set[Any] = set()
    dupes = 0
    for row in records:
        key_val = row[key_field]
        if key_val in seen:
            dupes += 1
        seen.add(key_val)
    return dupes


def _compute_qa_metrics(
    raw_rows: int,
    market_average_removed: int,
    all_null_removed: int,
    physical_rows: list[dict[str, str]],
    dim_markets: list[dict[str, Any]],
    dim_date: list[dict[str, Any]],
    dim_commodity: list[dict[str, Any]],
    fact_prices: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute comprehensive before/after quality and integrity metrics."""
    market_lookup = {row["mkt_id"]: row for row in dim_markets}
    date_keys = {row["date_key"] for row in dim_date}
    commodity_keys = {row["commodity_id"] for row in dim_commodity}

    recent_dates = [row["full_date"] for row in dim_date if row["is_recent"]]
    last_36_dates = [row["full_date"] for row in dim_date if row["is_last_36m"]]

    asal_counties = {row["adm2_name"] for row in dim_markets if row["county_group"] == "Arid & Semi-Arid (ASAL)"}
    agri_counties = {row["adm2_name"] for row in dim_markets if row["county_group"] == "Agricultural & Urban"}
    asal_markets = sum(1 for row in dim_markets if row["county_group"] == "Arid & Semi-Arid (ASAL)")
    agri_markets = sum(1 for row in dim_markets if row["county_group"] == "Agricultural & Urban")

    orphan_mkt = sum(1 for r in fact_prices if r["mkt_id"] not in market_lookup)
    orphan_date = sum(1 for r in fact_prices if r["date_key"] not in date_keys)
    orphan_commodity = sum(1 for r in fact_prices if r["commodity_id"] not in commodity_keys)

    commodity_breakdown: dict[str, dict[str, Any]] = {}
    for spec in COMMODITY_SPECS:
        c_rows = [r for r in fact_prices if r["commodity_id"] == spec.commodity_id]
        prices = [float(r["price_value"]) for r in c_rows]
        moms = [float(r["price_change_mom_pct"]) for r in c_rows if r["price_change_mom_pct"] is not None]
        commodity_breakdown[spec.commodity_id] = {
            "commodity_name": spec.commodity_name,
            "rows": len(c_rows),
            "min_price": min(prices),
            "mean_price": sum(prices) / len(prices),
            "max_price": max(prices),
            "outlier_rows": sum(1 for r in c_rows if r["is_outlier"]),
            "mean_mom_pct": sum(moms) / len(moms),
        }

    group_breakdown: dict[str, dict[str, Any]] = {}
    for group_name in ("Arid & Semi-Arid (ASAL)", "Agricultural & Urban"):
        group_markets = [m for m in dim_markets if m["county_group"] == group_name]
        group_rows = [r for r in fact_prices if market_lookup[r["mkt_id"]]["county_group"] == group_name]
        group_breakdown[group_name] = {
            "counties": len({m["adm2_name"] for m in group_markets}),
            "markets": len(group_markets),
            "fact_rows": len(group_rows),
            "outlier_rows": sum(1 for r in group_rows if r["is_outlier"]),
        }

    outlier_total = sum(1 for r in fact_prices if r["is_outlier"])
    return {
        "raw_rows": raw_rows,
        "market_average_rows_removed": market_average_removed,
        "all_null_physical_rows_removed": all_null_removed,
        "physical_market_rows": len(physical_rows),
        "dim_markets_rows": len(dim_markets),
        "dim_date_rows": len(dim_date),
        "dim_commodity_rows": len(dim_commodity),
        "fact_prices_rows": len(fact_prices),
        "date_min": dim_date[0]["full_date"],
        "date_max": dim_date[-1]["full_date"],
        "recent_12m_dates": len(recent_dates),
        "recent_12m_start": recent_dates[0],
        "recent_12m_end": recent_dates[-1],
        "last_36m_dates": len(last_36_dates),
        "last_36m_start": last_36_dates[0],
        "last_36m_end": last_36_dates[-1],
        "asal_counties_count": len(asal_counties),
        "asal_markets_count": asal_markets,
        "agri_urban_counties_count": len(agri_counties),
        "agri_urban_markets_count": agri_markets,
        "duplicate_pk_counts": {
            "dim_markets": _count_duplicates(dim_markets, "mkt_id"),
            "dim_date": _count_duplicates(dim_date, "date_key"),
            "dim_commodity": _count_duplicates(dim_commodity, "commodity_id"),
            "fact_prices": _count_duplicates(fact_prices, "price_id"),
        },
        "orphan_fk_counts": {
            "mkt_id": orphan_mkt,
            "date_key": orphan_date,
            "commodity_id": orphan_commodity,
        },
        "null_lat_lon_after": sum(1 for r in dim_markets if r["lat"] is None or r["lon"] is None),
        "null_price_value_after": sum(1 for r in fact_prices if r["price_value"] is None),
        "non_positive_price_count": sum(1 for r in fact_prices if float(r["price_value"]) <= 0.0),
        "null_mom_rows": sum(1 for r in fact_prices if r["price_change_mom"] is None),
        "valid_mom_rows": sum(1 for r in fact_prices if r["price_change_mom"] is not None),
        "null_commodity_inflation_rows": sum(
            1 for r in fact_prices if r["commodity_inflation_yoy"] is None
        ),
        "null_index_inflation_rows": sum(
            1 for r in fact_prices if r["inflation_food_price_index"] is None
        ),
        "outlier_rows": outlier_total,
        "outlier_pct": round((outlier_total / len(fact_prices)) * 100.0, 2),
        "commodity_breakdown": commodity_breakdown,
        "county_group_breakdown": group_breakdown,
    }


def run_etl(csv_path: Path | str | None = None) -> ETLResult:
    """Execute all 10 Week 2 transformations and verify star-schema integrity."""
    all_rows = load_data(csv_path=csv_path, include_market_average=True)
    candidate_physical = [
        r for r in all_rows if r["geo_id"] != "gid_ken_national_average" and r["mkt_name"] != "Market Average"
    ]
    market_average_removed = len(all_rows) - len(candidate_physical)

    physical_rows = [
        r
        for r in candidate_physical
        if any(_parse_float(r[spec.close_col]) is not None for spec in COMMODITY_SPECS)
    ]
    all_null_removed = len(candidate_physical) - len(physical_rows)

    dim_markets = _build_dim_markets(physical_rows)
    dim_date = _build_dim_date(physical_rows)
    dim_commodity = _build_dim_commodity()
    fact_prices = _build_fact_prices(physical_rows)
    qa_metrics = _compute_qa_metrics(
        raw_rows=len(all_rows),
        market_average_removed=market_average_removed,
        all_null_removed=all_null_removed,
        physical_rows=physical_rows,
        dim_markets=dim_markets,
        dim_date=dim_date,
        dim_commodity=dim_commodity,
        fact_prices=fact_prices,
    )
    return ETLResult(
        dim_markets=dim_markets,
        dim_date=dim_date,
        dim_commodity=dim_commodity,
        fact_prices=fact_prices,
        qa_metrics=qa_metrics,
    )
