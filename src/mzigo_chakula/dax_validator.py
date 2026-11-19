"""Deterministic DAX measure specifications and validation reference engine."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from mzigo_chakula.etl import COMMODITY_SPECS, MONTH_ABBREVIATIONS, ETLResult


@dataclass(frozen=True)
class DAXMeasureSpec:
    """Metadata and DAX definition for a model measure."""

    measure_number: int
    name: str
    table_name: str
    display_folder: str
    format_string: str
    dax_expression: str
    description: str


DAX_MEASURES: tuple[DAXMeasureSpec, ...] = (
    DAXMeasureSpec(
        measure_number=1,
        name="Avg Price (KES)",
        table_name="fact_prices",
        display_folder="01. Core Price & Index",
        format_string="#,0.00",
        dax_expression="AVERAGE(fact_prices[price_value])",
        description="Mean closing commodity price in KES within the active filter context.",
    ),
    DAXMeasureSpec(
        measure_number=2,
        name="National Food Price Index",
        table_name="fact_prices",
        display_folder="01. Core Price & Index",
        format_string="0.00",
        dax_expression=(
            "AVERAGEX(\n"
            "    SUMMARIZE(fact_prices, fact_prices[mkt_id], fact_prices[date_key]),\n"
            "    CALCULATE(AVERAGE(fact_prices[food_price_index]))\n"
            ")"
        ),
        description=(
            "Grain-safe mean closing composite food price index averaged at the distinct "
            "(mkt_id, date_key) grain so unpivoting three commodities does not triple-count index weight."
        ),
    ),
    DAXMeasureSpec(
        measure_number=3,
        name="Prior Year Price (KES)",
        table_name="fact_prices",
        display_folder="02. Time Intelligence & Growth",
        format_string="#,0.00",
        dax_expression=(
            "VAR PriorDates =\n"
            "    SELECTCOLUMNS(\n"
            "        VALUES(dim_date[full_date]),\n"
            '        "prior_date", EDATE(dim_date[full_date], -12)\n'
            "    )\n"
            "RETURN\n"
            "    CALCULATE(\n"
            "        [Avg Price (KES)],\n"
            "        REMOVEFILTERS(dim_date),\n"
            "        TREATAS(PriorDates, dim_date[full_date])\n"
            "    )"
        ),
        description=(
            "Mean closing commodity price shifted back 12 months via gap-safe EDATE and TREATAS."
        ),
    ),
    DAXMeasureSpec(
        measure_number=4,
        name="YoY Inflation %",
        table_name="fact_prices",
        display_folder="02. Time Intelligence & Growth",
        format_string="0.00%",
        dax_expression=(
            "VAR CurrentIdx = [National Food Price Index]\n"
            "VAR PriorDates =\n"
            "    SELECTCOLUMNS(\n"
            "        VALUES(dim_date[full_date]),\n"
            '        "prior_date", EDATE(dim_date[full_date], -12)\n'
            "    )\n"
            "VAR PriorYearIdx =\n"
            "    CALCULATE(\n"
            "        [National Food Price Index],\n"
            "        REMOVEFILTERS(dim_date),\n"
            "        TREATAS(PriorDates, dim_date[full_date])\n"
            "    )\n"
            "RETURN\n"
            "    DIVIDE(CurrentIdx - PriorYearIdx, PriorYearIdx)"
        ),
        description="Year-over-year percentage change in the grain-safe composite food price index.",
    ),
    DAXMeasureSpec(
        measure_number=5,
        name="Commodity YoY Inflation %",
        table_name="fact_prices",
        display_folder="02. Time Intelligence & Growth",
        format_string="0.00%",
        dax_expression=(
            "VAR CurrentPrice = [Avg Price (KES)]\n"
            "VAR PriorYearPrice = [Prior Year Price (KES)]\n"
            "RETURN\n"
            "    DIVIDE(CurrentPrice - PriorYearPrice, PriorYearPrice)"
        ),
        description="Year-over-year percentage change in average commodity price (KES).",
    ),
    DAXMeasureSpec(
        measure_number=6,
        name="MoM Change %",
        table_name="fact_prices",
        display_folder="02. Time Intelligence & Growth",
        format_string="0.00%",
        dax_expression=(
            "VAR CurrentPrice = [Avg Price (KES)]\n"
            "VAR PriorDates =\n"
            "    SELECTCOLUMNS(\n"
            "        VALUES(dim_date[full_date]),\n"
            '        "prior_date", EDATE(dim_date[full_date], -1)\n'
            "    )\n"
            "VAR PriorMonthPrice =\n"
            "    CALCULATE(\n"
            "        [Avg Price (KES)],\n"
            "        REMOVEFILTERS(dim_date),\n"
            "        TREATAS(PriorDates, dim_date[full_date])\n"
            "    )\n"
            "RETURN\n"
            "    DIVIDE(CurrentPrice - PriorMonthPrice, PriorMonthPrice)"
        ),
        description=(
            "Month-over-month percentage change in average commodity price via gap-safe EDATE."
        ),
    ),
    DAXMeasureSpec(
        measure_number=7,
        name="Price Volatility (KES)",
        table_name="fact_prices",
        display_folder="03. Risk & Seasonality",
        format_string="#,0.00",
        dax_expression="STDEV.S(fact_prices[price_value])",
        description="Sample standard deviation of monthly closing prices in KES.",
    ),
    DAXMeasureSpec(
        measure_number=8,
        name="Price Volatility CV %",
        table_name="fact_prices",
        display_folder="03. Risk & Seasonality",
        format_string="0.00%",
        dax_expression=(
            "AVERAGEX(\n"
            "    VALUES(fact_prices[commodity_id]),\n"
            "    DIVIDE([Price Volatility (KES)], [Avg Price (KES)])\n"
            ")"
        ),
        description=(
            "Unit-safe coefficient of variation computed per commodity for cross-commodity comparisons."
        ),
    ),
    DAXMeasureSpec(
        measure_number=9,
        name="Cumulative Index YTD",
        table_name="fact_prices",
        display_folder="02. Time Intelligence & Growth",
        format_string="0.00",
        dax_expression=(
            "VAR AnchorDate = MAX(dim_date[full_date])\n"
            "VAR AnchorYear = YEAR(AnchorDate)\n"
            "RETURN\n"
            "    CALCULATE(\n"
            "        [National Food Price Index],\n"
            "        REMOVEFILTERS(dim_date),\n"
            "        dim_date[year] = AnchorYear,\n"
            "        dim_date[full_date] <= AnchorDate\n"
            "    )"
        ),
        description="Year-to-date running mean composite food price index within the anchor year.",
    ),
    DAXMeasureSpec(
        measure_number=10,
        name="County Inflation Rank",
        table_name="fact_prices",
        display_folder="04. Coverage & Disparities",
        format_string="0",
        dax_expression=(
            "IF(\n"
            "    ISINSCOPE(dim_markets[adm2_name]),\n"
            "    RANKX(ALL(dim_markets[adm2_name]), [YoY Inflation %], , DESC, Dense)\n"
            ")"
        ),
        description="Dense descending rank of Kenyan counties by YoY food index inflation (1 = highest inflation).",
    ),
    DAXMeasureSpec(
        measure_number=11,
        name="Data Completeness %",
        table_name="fact_prices",
        display_folder="04. Coverage & Disparities",
        format_string="0.00%",
        dax_expression=(
            "VAR ObservedRows = COUNTROWS(fact_prices)\n"
            "VAR ExpectedRows = COUNTROWS(dim_markets) * COUNTROWS(dim_date) * COUNTROWS(dim_commodity)\n"
            "RETURN\n"
            "    DIVIDE(ObservedRows, ExpectedRows)"
        ),
        description="Share of expected market-month-commodity cells populated with non-null modelled closing prices.",
    ),
    DAXMeasureSpec(
        measure_number=12,
        name="Survey Coverage Rate %",
        table_name="fact_prices",
        display_folder="04. Coverage & Disparities",
        format_string="0.00%",
        dax_expression="DIVIDE(COUNT(fact_prices[raw_spot_price]), COUNTROWS(fact_prices))",
        description="Share of market-month-commodity records backed by a direct raw field survey observation.",
    ),
    DAXMeasureSpec(
        measure_number=13,
        name="Affordability Gap (KES)",
        table_name="fact_prices",
        display_folder="04. Coverage & Disparities",
        format_string="#,0.00",
        dax_expression=(
            "AVERAGEX(\n"
            "    VALUES(fact_prices[commodity_id]),\n"
            "    VAR LocalAvg = [Avg Price (KES)]\n"
            "    VAR NationalAvg = CALCULATE([Avg Price (KES)], ALL(dim_markets))\n"
            "    RETURN\n"
            "        LocalAvg - NationalAvg\n"
            ")"
        ),
        description=(
            "Unit-safe local price premium or discount in KES compared to the national mean."
        ),
    ),
    DAXMeasureSpec(
        measure_number=14,
        name="Seasonal Index",
        table_name="fact_prices",
        display_folder="03. Risk & Seasonality",
        format_string="0.000",
        dax_expression=(
            "VAR CurrentMonthAvg = [Avg Price (KES)]\n"
            "VAR AllMonthsAvg = CALCULATE([Avg Price (KES)], ALL(dim_date[month], dim_date[month_name], dim_date[season], dim_date[quarter]))\n"
            "RETURN\n"
            "    DIVIDE(CurrentMonthAvg, AllMonthsAvg)"
        ),
        description="Ratio of a calendar month or season average price to the all-month average (>1.000 = seasonal peak).",
    ),
    DAXMeasureSpec(
        measure_number=15,
        name="12-Month Rolling Avg (KES)",
        table_name="fact_prices",
        display_folder="02. Time Intelligence & Growth",
        format_string="#,0.00",
        dax_expression=(
            "VAR AnchorDate = MAX(dim_date[full_date])\n"
            "VAR StartDate = EDATE(AnchorDate, -11)\n"
            "RETURN\n"
            "    CALCULATE(\n"
            "        AVERAGEX(\n"
            "            VALUES(dim_date[full_date]),\n"
            "            [Avg Price (KES)]\n"
            "        ),\n"
            "        REMOVEFILTERS(dim_date),\n"
            "        dim_date[full_date] >= StartDate,\n"
            "        dim_date[full_date] <= AnchorDate\n"
            "    )"
        ),
        description="Trailing 12-month smoothed commodity price average via gap-safe EDATE.",
    ),
)


def _mean(values: list[float]) -> float:
    """Compute arithmetic mean or return 0.0 if empty."""
    return sum(values) / len(values) if values else 0.0


def _stdev_s(values: list[float]) -> float:
    """Compute sample standard deviation matching DAX STDEV.S."""
    return statistics.stdev(values) if len(values) > 1 else 0.0


def _national_food_price_index(rows: list[dict[str, Any]]) -> float:
    """Mirror DAX National Food Price Index at distinct (mkt_id, date_key) grain."""
    market_month: dict[tuple[str, int], float] = {}
    for row in rows:
        key = (row["mkt_id"], int(row["date_key"]))
        if key not in market_month:
            market_month[key] = float(row["food_price_index"])
    return _mean(list(market_month.values()))


def _yoy_pct(current_val: float, prior_val: float) -> float | None:
    """Mirror DAX DIVIDE(current - prior, prior)."""
    if prior_val == 0.0:
        return None
    return (current_val - prior_val) / prior_val


def _pearson_corr(xs: list[float], ys: list[float]) -> float:
    """Compute Pearson correlation coefficient between two equal-length series."""
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    mx = _mean(xs)
    my = _mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    var_x = sum((x - mx) ** 2 for x in xs)
    var_y = sum((y - my) ** 2 for y in ys)
    denom = math.sqrt(var_x * var_y)
    return cov / denom if denom > 0.0 else 0.0


def compute_dax_validation_summary(etl_result: ETLResult) -> dict[str, Any]:
    """Evaluate all 15 DAX measures and analytical questions directly from cleaned ETL data."""
    markets_by_id = {m["mkt_id"]: m for m in etl_result.dim_markets}
    dates_by_key = {int(d["date_key"]): d for d in etl_result.dim_date}
    sorted_date_keys = sorted(dates_by_key.keys())

    latest_key = sorted_date_keys[-1]
    prior_month_key = sorted_date_keys[-2]
    recent_12m_keys = {int(d["date_key"]) for d in etl_result.dim_date if d["is_recent"]}
    prior_12m_keys = set(sorted_date_keys[-24:-12])
    last_36m_keys = {int(d["date_key"]) for d in etl_result.dim_date if d["is_last_36m"]}
    prior_36m_keys = set(sorted_date_keys[-48:-12])
    ytd_2026_keys = {int(d["date_key"]) for d in etl_result.dim_date if int(d["year"]) == 2026}

    fact = etl_result.fact_prices
    recent_12m_rows = [r for r in fact if int(r["date_key"]) in recent_12m_keys]
    prior_12m_rows = [r for r in fact if int(r["date_key"]) in prior_12m_keys]
    ytd_2026_rows = [r for r in fact if int(r["date_key"]) in ytd_2026_keys]

    expected_cells = (
        len(etl_result.dim_markets) * len(etl_result.dim_date) * len(etl_result.dim_commodity)
    )
    data_completeness = len(fact) / expected_cells
    survey_total = sum(1 for r in fact if r["raw_spot_price"] is not None)
    survey_coverage = survey_total / len(fact)

    idx_full = _national_food_price_index(fact)
    idx_recent_12m = _national_food_price_index(recent_12m_rows)
    idx_prior_12m = _national_food_price_index(prior_12m_rows)
    idx_yoy_recent_12m = _yoy_pct(idx_recent_12m, idx_prior_12m) or 0.0
    idx_ytd_2026 = _national_food_price_index(ytd_2026_rows)

    # Analytical Question 2: co-movement with composite food index at (mkt_id, date_key) grain
    by_mkt_date: dict[tuple[str, int], dict[str, float]] = defaultdict(dict)
    for row in fact:
        mk_key = (row["mkt_id"], int(row["date_key"]))
        by_mkt_date[mk_key]["food_price_index"] = float(row["food_price_index"])
        by_mkt_date[mk_key][row["commodity_id"]] = float(row["price_value"])
        if row["price_change_mom_pct"] is not None:
            by_mkt_date[mk_key][f"mom_{row['commodity_id']}"] = float(row["price_change_mom_pct"])
        if row["commodity_inflation_yoy"] is not None:
            by_mkt_date[mk_key][f"yoy_{row['commodity_id']}"] = float(row["commodity_inflation_yoy"])
        if row["inflation_food_price_index"] is not None:
            by_mkt_date[mk_key]["yoy_idx"] = float(row["inflation_food_price_index"])

    idx_series = [item["food_price_index"] for item in by_mkt_date.values()]
    yoy_pairs = [item for item in by_mkt_date.values() if "yoy_idx" in item]
    yoy_idx_series = [item["yoy_idx"] for item in yoy_pairs]

    commodity_metrics: dict[str, dict[str, Any]] = {}
    national_commodity_avg: dict[str, float] = {}
    for spec in COMMODITY_SPECS:
        cid = spec.commodity_id
        c_rows = [r for r in fact if r["commodity_id"] == cid]
        c_recent = [r for r in c_rows if int(r["date_key"]) in recent_12m_keys]
        c_prior = [r for r in c_rows if int(r["date_key"]) in prior_12m_keys]
        c_latest = [float(r["price_value"]) for r in c_rows if int(r["date_key"]) == latest_key]
        c_prev_mo = [float(r["price_value"]) for r in c_rows if int(r["date_key"]) == prior_month_key]

        all_prices = [float(r["price_value"]) for r in c_rows]
        recent_prices = [float(r["price_value"]) for r in c_recent]
        prior_prices = [float(r["price_value"]) for r in c_prior]

        avg_full = _mean(all_prices)
        avg_recent = _mean(recent_prices)
        avg_prior = _mean(prior_prices)
        vol_kes = _stdev_s(all_prices)
        vol_cv = vol_kes / avg_full if avg_full else 0.0

        # Rolling 12m matches AVERAGEX(DATESINPERIOD(..., -12, MONTH), [Avg Price (KES)])
        monthly_avgs_12m: list[float] = []
        for dk in sorted_date_keys[-12:]:
            month_vals = [float(r["price_value"]) for r in c_recent if int(r["date_key"]) == dk]
            monthly_avgs_12m.append(_mean(month_vals))
        rolling_12m = _mean(monthly_avgs_12m)

        corr_level = _pearson_corr(
            [item[cid] for item in by_mkt_date.values()],
            idx_series,
        )
        corr_yoy = _pearson_corr(
            [item[f"yoy_{cid}"] for item in yoy_pairs],
            yoy_idx_series,
        )
        national_commodity_avg[cid] = avg_full

        commodity_metrics[cid] = {
            "commodity_name": spec.commodity_name,
            "avg_price_kes": avg_full,
            "recent_12m_avg_kes": avg_recent,
            "yoy_inflation_12m": _yoy_pct(avg_recent, avg_prior) or 0.0,
            "latest_mom_pct": _yoy_pct(_mean(c_latest), _mean(c_prev_mo)) or 0.0,
            "volatility_kes": vol_kes,
            "volatility_cv": vol_cv,
            "rolling_12m_avg_kes": rolling_12m,
            "corr_with_food_index": corr_level,
            "r2_with_food_index": corr_level ** 2,
            "corr_yoy_with_index_yoy": corr_yoy,
            "r2_yoy_with_index_yoy": corr_yoy ** 2,
            "survey_coverage_rate": sum(1 for r in c_rows if r["raw_spot_price"] is not None) / len(c_rows),
        }

    # County-level aggregations (Questions 1 & 5 + Affordability Gap invariant check)
    rows_by_county: dict[str, list[dict[str, Any]]] = defaultdict(list)
    markets_by_county: dict[str, int] = defaultdict(int)
    for m in etl_result.dim_markets:
        markets_by_county[m["adm2_name"]] += 1
    for r in fact:
        county = markets_by_id[r["mkt_id"]]["adm2_name"]
        rows_by_county[county].append(r)

    county_metrics: list[dict[str, Any]] = []
    for county, c_rows in sorted(rows_by_county.items()):
        c_rec12 = [r for r in c_rows if int(r["date_key"]) in recent_12m_keys]
        c_pri12 = [r for r in c_rows if int(r["date_key"]) in prior_12m_keys]
        c_rec36 = [r for r in c_rows if int(r["date_key"]) in last_36m_keys]
        c_pri36 = [r for r in c_rows if int(r["date_key"]) in prior_36m_keys]

        yoy_12m = _yoy_pct(_national_food_price_index(c_rec12), _national_food_price_index(c_pri12)) or 0.0
        yoy_36m = _yoy_pct(_national_food_price_index(c_rec36), _national_food_price_index(c_pri36)) or 0.0

        # Point-in-time YoY at latest month vs 3 years prior for comparison context
        c_2026_10 = [r for r in c_rows if int(r["date_key"]) == latest_key]
        c_2023_10 = [r for r in c_rows if int(r["date_key"]) == 20231001]
        c_3yr_cum = _yoy_pct(_national_food_price_index(c_2026_10), _national_food_price_index(c_2023_10)) or 0.0

        gaps: dict[str, float] = {}
        vols: dict[str, float] = {}
        for spec in COMMODITY_SPECS:
            cid = spec.commodity_id
            prices = [float(r["price_value"]) for r in c_rows if r["commodity_id"] == cid]
            c_mean = _mean(prices)
            gaps[cid] = c_mean - national_commodity_avg[cid]
            vols[cid] = _stdev_s(prices) / c_mean if c_mean else 0.0

        sample_mkt = next(m for m in etl_result.dim_markets if m["adm2_name"] == county)
        survey_rate = sum(1 for r in c_rows if r["raw_spot_price"] is not None) / len(c_rows)
        county_metrics.append(
            {
                "county": county,
                "region": sample_mkt["adm1_name"],
                "county_group": sample_mkt["county_group"],
                "markets": markets_by_county[county],
                "yoy_12m": yoy_12m,
                "yoy_36m": yoy_36m,
                "cum_3yr_index_growth": c_3yr_cum,
                "gap_beans_kes": gaps["beans"],
                "gap_maize_kes": gaps["maize_fao"],
                "gap_goat_kes": gaps["livestock_goat_s_fao"],
                "maize_cv": vols["maize_fao"],
                "beans_cv": vols["beans"],
                "goat_cv": vols["livestock_goat_s_fao"],
                "survey_coverage_rate": survey_rate,
            }
        )

    # Dense rank by last-36m YoY inflation (descending) and recent-12m YoY inflation (descending)
    distinct_36m = sorted({round(c["yoy_36m"], 10) for c in county_metrics}, reverse=True)
    distinct_12m = sorted({round(c["yoy_12m"], 10) for c in county_metrics}, reverse=True)
    for c in county_metrics:
        c["rank_36m"] = distinct_36m.index(round(c["yoy_36m"], 10)) + 1
        c["rank_12m"] = distinct_12m.index(round(c["yoy_12m"], 10)) + 1

    # Zero-sum invariant for market-weighted Affordability Gap across each commodity
    gap_weighted_sums: dict[str, float] = {}
    for cid, gap_key in (
        ("beans", "gap_beans_kes"),
        ("maize_fao", "gap_maize_kes"),
        ("livestock_goat_s_fao", "gap_goat_kes"),
    ):
        gap_weighted_sums[cid] = sum(c["markets"] * c[gap_key] for c in county_metrics)

    # Analytical Question 3: ASAL vs Agricultural & Urban volatility per commodity
    group_comparison: dict[str, dict[str, Any]] = {}
    for group_name in ("Arid & Semi-Arid (ASAL)", "Agricultural & Urban"):
        g_rows = [r for r in fact if markets_by_id[r["mkt_id"]]["county_group"] == group_name]
        moms_abs = [abs(float(r["price_change_mom_pct"])) for r in g_rows if r["price_change_mom_pct"] is not None]
        outlier_rate = sum(1 for r in g_rows if r["is_outlier"]) / len(g_rows)
        per_comm: dict[str, dict[str, float]] = {}
        for spec in COMMODITY_SPECS:
            cid = spec.commodity_id
            cp = [float(r["price_value"]) for r in g_rows if r["commodity_id"] == cid]
            c_mean = _mean(cp)
            c_std = _stdev_s(cp)
            per_comm[cid] = {
                "avg_price": c_mean,
                "volatility_kes": c_std,
                "volatility_cv": c_std / c_mean if c_mean else 0.0,
            }
        group_comparison[group_name] = {
            "rows": len(g_rows),
            "mean_abs_mom_pct": _mean(moms_abs),
            "outlier_rate": outlier_rate,
            "food_index_mean": _national_food_price_index(g_rows),
            "food_index_cv": (
                _stdev_s(
                    [
                        val
                        for val in {
                            (r["mkt_id"], r["date_key"]): float(r["food_price_index"]) for r in g_rows
                        }.values()
                    ]
                )
                / _national_food_price_index(g_rows)
            ),
            "commodities": per_comm,
        }

    # Analytical Question 4: Monthly and Seasonal Index per commodity + overall ASAL vs Agri/Urban
    seasonal_by_month: dict[str, list[dict[str, Any]]] = {}
    for spec in COMMODITY_SPECS:
        cid = spec.commodity_id
        c_rows = [r for r in fact if r["commodity_id"] == cid]
        all_mean = national_commodity_avg[cid]
        monthly_list: list[dict[str, Any]] = []
        for month_num in range(1, 13):
            m_vals = [
                float(r["price_value"])
                for r in c_rows
                if int(dates_by_key[int(r["date_key"])]["month"]) == month_num
            ]
            m_avg = _mean(m_vals)
            monthly_list.append(
                {
                    "month": month_num,
                    "month_name": MONTH_ABBREVIATIONS[month_num - 1],
                    "avg_price": m_avg,
                    "seasonal_index": m_avg / all_mean if all_mean else 0.0,
                }
            )
        seasonal_by_month[cid] = monthly_list

    seasonal_by_window: dict[str, dict[str, float]] = {}
    seasons_order = (
        "Hot Dry / Lean (Jan-Feb)",
        "Long Rains (Mar-May)",
        "Cool Dry / Harvest (Jun-Sep)",
        "Short Rains (Oct-Dec)",
    )
    for spec in COMMODITY_SPECS:
        cid = spec.commodity_id
        c_rows = [r for r in fact if r["commodity_id"] == cid]
        all_mean = national_commodity_avg[cid]
        s_map: dict[str, float] = {}
        for season_name in seasons_order:
            s_vals = [
                float(r["price_value"])
                for r in c_rows
                if dates_by_key[int(r["date_key"])]["season"] == season_name
            ]
            s_map[season_name] = _mean(s_vals) / all_mean if all_mean else 0.0
        seasonal_by_window[cid] = s_map

    return {
        "overall": {
            "latest_date": dates_by_key[latest_key]["full_date"],
            "recent_12m_start": dates_by_key[min(recent_12m_keys)]["full_date"],
            "recent_12m_end": dates_by_key[max(recent_12m_keys)]["full_date"],
            "last_36m_start": dates_by_key[min(last_36m_keys)]["full_date"],
            "last_36m_end": dates_by_key[max(last_36m_keys)]["full_date"],
            "national_food_index_full": idx_full,
            "national_food_index_recent_12m": idx_recent_12m,
            "national_food_index_prior_12m": idx_prior_12m,
            "yoy_inflation_recent_12m": idx_yoy_recent_12m,
            "cumulative_index_ytd_2026": idx_ytd_2026,
            "data_completeness_pct": data_completeness,
            "survey_coverage_rate_pct": survey_coverage,
        },
        "commodities": commodity_metrics,
        "counties": county_metrics,
        "gap_weighted_sums": gap_weighted_sums,
        "group_comparison": group_comparison,
        "seasonal_by_month": seasonal_by_month,
        "seasonal_by_window": seasonal_by_window,
    }
