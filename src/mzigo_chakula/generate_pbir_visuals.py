"""Generate native Power BI Enhanced Report (PBIR) visuals across all four report pages."""

from __future__ import annotations

import json
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mzigo_chakula.data import PROJECT_ROOT

VISUAL_SCHEMA_URL = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.14.0/schema.json"
)
DEFAULT_PAGES_DIR = PROJECT_ROOT / "pbip" / "mzigo-chakula.Report" / "definition" / "pages"


@dataclass(frozen=True)
class SortSpec:
    """Sort definition target measure and direction."""

    entity: str
    prop: str
    direction: str


@dataclass(frozen=True)
class VisualSpec:
    """Compact declarative definition for one PBIR visual container."""

    page_name: str
    visual_id: str
    visual_type: str
    title: str
    x: int
    y: int
    width: int
    height: int
    z: int
    query_state: dict[str, dict[str, Any]]
    sort: SortSpec | None = None
    objects: dict[str, Any] | None = None


def col_proj(entity: str, prop: str, active: bool | None = None) -> dict[str, Any]:
    """Build a PBIR column RoleProjection entry."""
    proj: dict[str, Any] = {
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": entity}},
                "Property": prop,
            }
        },
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
    }
    if active is not None:
        proj["active"] = active
    return proj


def meas_proj(entity: str, prop: str) -> dict[str, Any]:
    """Build a PBIR measure RoleProjection entry."""
    return {
        "field": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": entity}},
                "Property": prop,
            }
        },
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
    }


def _slicer_spec(
    page_name: str,
    visual_id: str,
    title: str,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
    entity: str,
    column: str,
) -> VisualSpec:
    """Create a Dropdown slicer specification bound to a single dimension column."""
    return VisualSpec(
        page_name=page_name,
        visual_id=visual_id,
        visual_type="slicer",
        title=title,
        x=x,
        y=y,
        width=width,
        height=height,
        z=z,
        query_state={"Values": {"projections": [col_proj(entity, column, active=True)]}},
        objects={
            "data": [
                {
                    "properties": {
                        "mode": {"expr": {"Literal": {"Value": "'Dropdown'"}}},
                    }
                }
            ]
        },
    )


def _card_spec(
    page_name: str,
    visual_id: str,
    title: str,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
    measure: str,
    entity: str = "fact_prices",
) -> VisualSpec:
    """Create a KPI card visual specification bound to a single measure."""
    return VisualSpec(
        page_name=page_name,
        visual_id=visual_id,
        visual_type="card",
        title=title,
        x=x,
        y=y,
        width=width,
        height=height,
        z=z,
        query_state={"Values": {"projections": [meas_proj(entity, measure)]}},
    )


def build_visual_specs() -> tuple[VisualSpec, ...]:
    """Return all 40 PBIR visual specifications bound to the 15 model measures."""
    p1 = "ReportSectionExecutivePulse"
    p2 = "ReportSectionCountyCommodity"
    p3 = "ReportSectionTrendsDiagnostics"
    p4 = "ReportSectionDecisionsAction"

    return (
        # Page 1: Executive Pulse (14 visuals)
        _slicer_spec(p1, "v01_slicer_year", "Year", 16, 10, 230, 58, 0, "dim_date", "year"),
        _slicer_spec(
            p1,
            "v02_slicer_group",
            "County Group",
            258,
            10,
            250,
            58,
            1,
            "dim_markets",
            "county_group",
        ),
        _slicer_spec(
            p1,
            "v03_slicer_commodity",
            "Commodity",
            520,
            10,
            250,
            58,
            2,
            "dim_commodity",
            "commodity_name",
        ),
        _slicer_spec(
            p1,
            "v04_slicer_season",
            "Cropping Season",
            782,
            10,
            250,
            58,
            3,
            "dim_date",
            "season",
        ),
        _slicer_spec(
            p1, "v05_slicer_region", "Region", 1044, 10, 220, 58, 4, "dim_markets", "adm1_name"
        ),
        _card_spec(
            p1,
            "v06_card_fpi",
            "National Food Price Index",
            16,
            76,
            240,
            92,
            5,
            "National Food Price Index",
        ),
        _card_spec(
            p1,
            "v07_card_yoy",
            "YoY Food Inflation %",
            268,
            76,
            240,
            92,
            6,
            "YoY Inflation %",
        ),
        _card_spec(
            p1,
            "v08_card_avg_price",
            "Avg Commodity Price (KES)",
            520,
            76,
            240,
            92,
            7,
            "Avg Price (KES)",
        ),
        _card_spec(
            p1,
            "v09_card_completeness",
            "Data Completeness %",
            772,
            76,
            240,
            92,
            8,
            "Data Completeness %",
        ),
        _card_spec(
            p1,
            "v10_card_coverage",
            "Field Survey Coverage %",
            1024,
            76,
            240,
            92,
            9,
            "Survey Coverage Rate %",
        ),
        VisualSpec(
            page_name=p1,
            visual_id="v11_line_fpi_trend",
            visual_type="lineChart",
            title="238-Month National Food Price Index and Cumulative YTD Trend",
            x=16,
            y=178,
            width=756,
            height=276,
            z=10,
            query_state={
                "Category": {"projections": [col_proj("dim_date", "full_date", active=True)]},
                "Y": {
                    "projections": [
                        meas_proj("fact_prices", "National Food Price Index"),
                        meas_proj("fact_prices", "Cumulative Index YTD"),
                    ]
                },
                "Tooltips": {"projections": [meas_proj("fact_prices", "YoY Inflation %")]},
            },
        ),
        VisualSpec(
            page_name=p1,
            visual_id="v12_bar_top_counties",
            visual_type="clusteredBarChart",
            title="Counties Ranked by YoY Food Inflation %",
            x=784,
            y=178,
            width=480,
            height=276,
            z=11,
            query_state={
                "Category": {"projections": [col_proj("dim_markets", "adm2_name", active=True)]},
                "Y": {"projections": [meas_proj("fact_prices", "YoY Inflation %")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "National Food Price Index"),
                        meas_proj("fact_prices", "County Inflation Rank"),
                    ]
                },
            },
            sort=SortSpec("fact_prices", "YoY Inflation %", "Descending"),
        ),
        VisualSpec(
            page_name=p1,
            visual_id="v13_table_commodities",
            visual_type="tableEx",
            title="Commodity Price, YoY Growth, and Volatility (CV) Summary",
            x=16,
            y=464,
            width=756,
            height=242,
            z=12,
            query_state={
                "Values": {
                    "projections": [
                        col_proj("dim_commodity", "commodity_name"),
                        col_proj("dim_commodity", "unit"),
                        meas_proj("fact_prices", "Avg Price (KES)"),
                        meas_proj("fact_prices", "Prior Year Price (KES)"),
                        meas_proj("fact_prices", "Commodity YoY Inflation %"),
                        meas_proj("fact_prices", "Price Volatility CV %"),
                    ]
                }
            },
        ),
        VisualSpec(
            page_name=p1,
            visual_id="v14_table_county_alerts",
            visual_type="tableEx",
            title="County Inflation Watchlist and Ranking",
            x=784,
            y=464,
            width=480,
            height=242,
            z=13,
            query_state={
                "Values": {
                    "projections": [
                        col_proj("dim_markets", "adm2_name"),
                        col_proj("dim_markets", "county_group"),
                        meas_proj("fact_prices", "National Food Price Index"),
                        meas_proj("fact_prices", "YoY Inflation %"),
                        meas_proj("fact_prices", "County Inflation Rank"),
                    ]
                }
            },
        ),
        # Page 2: County and Commodity (8 visuals)
        _slicer_spec(
            p2,
            "v21_slicer_commodity",
            "Commodity",
            16,
            10,
            300,
            58,
            0,
            "dim_commodity",
            "commodity_name",
        ),
        _slicer_spec(
            p2,
            "v22_slicer_group",
            "County Group (ASAL vs Agri/Urban)",
            328,
            10,
            300,
            58,
            1,
            "dim_markets",
            "county_group",
        ),
        _slicer_spec(
            p2, "v23_slicer_region", "Region", 640, 10, 300, 58, 2, "dim_markets", "adm1_name"
        ),
        _slicer_spec(p2, "v24_slicer_year", "Year", 952, 10, 312, 58, 3, "dim_date", "year"),
        VisualSpec(
            page_name=p2,
            visual_id="v25_bar_affordability_gap",
            visual_type="clusteredBarChart",
            title="County Affordability Gap vs National Benchmark (KES)",
            x=16,
            y=78,
            width=620,
            height=308,
            z=4,
            query_state={
                "Category": {"projections": [col_proj("dim_markets", "adm2_name", active=True)]},
                "Y": {"projections": [meas_proj("fact_prices", "Affordability Gap (KES)")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "Avg Price (KES)"),
                        meas_proj("fact_prices", "Prior Year Price (KES)"),
                    ]
                },
            },
            sort=SortSpec("fact_prices", "Affordability Gap (KES)", "Descending"),
        ),
        VisualSpec(
            page_name=p2,
            visual_id="v26_scatter_county_risk",
            visual_type="scatterChart",
            title="County Average Price (KES) vs Price Volatility CV % by Group",
            x=648,
            y=78,
            width=616,
            height=308,
            z=5,
            query_state={
                "Category": {"projections": [col_proj("dim_markets", "adm2_name", active=True)]},
                "Series": {"projections": [col_proj("dim_markets", "county_group", active=True)]},
                "X": {"projections": [meas_proj("fact_prices", "Avg Price (KES)")]},
                "Y": {"projections": [meas_proj("fact_prices", "Price Volatility CV %")]},
                "Size": {"projections": [meas_proj("fact_prices", "Price Volatility (KES)")]},
            },
        ),
        VisualSpec(
            page_name=p2,
            visual_id="v27_col_group_comparison",
            visual_type="clusteredColumnChart",
            title="Price Volatility CV % by Commodity: ASAL vs Agricultural & Urban",
            x=16,
            y=398,
            width=520,
            height=308,
            z=6,
            query_state={
                "Category": {
                    "projections": [col_proj("dim_commodity", "commodity_name", active=True)]
                },
                "Series": {"projections": [col_proj("dim_markets", "county_group", active=True)]},
                "Y": {"projections": [meas_proj("fact_prices", "Price Volatility CV %")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "Avg Price (KES)"),
                        meas_proj("fact_prices", "Affordability Gap (KES)"),
                    ]
                },
            },
        ),
        VisualSpec(
            page_name=p2,
            visual_id="v28_table_county_drill",
            visual_type="tableEx",
            title="County and Physical Market Affordability Matrix",
            x=548,
            y=398,
            width=716,
            height=308,
            z=7,
            query_state={
                "Values": {
                    "projections": [
                        col_proj("dim_markets", "adm2_name"),
                        col_proj("dim_markets", "mkt_name"),
                        col_proj("dim_markets", "county_group"),
                        meas_proj("fact_prices", "Avg Price (KES)"),
                        meas_proj("fact_prices", "Affordability Gap (KES)"),
                        meas_proj("fact_prices", "Commodity YoY Inflation %"),
                        meas_proj("fact_prices", "Price Volatility CV %"),
                    ]
                }
            },
        ),
        # Page 3: Trends and Diagnostics (9 visuals)
        _slicer_spec(
            p3,
            "v31_slicer_commodity",
            "Select Commodity",
            16,
            10,
            280,
            66,
            0,
            "dim_commodity",
            "commodity_name",
        ),
        _slicer_spec(
            p3,
            "v32_slicer_group",
            "Select County Group",
            308,
            10,
            280,
            66,
            1,
            "dim_markets",
            "county_group",
        ),
        _card_spec(p3, "v33_card_mom", "MoM Price Change %", 600, 10, 216, 66, 2, "MoM Change %"),
        _card_spec(
            p3,
            "v34_card_rolling",
            "12m Rolling Avg (KES)",
            828,
            10,
            216,
            66,
            3,
            "12-Month Rolling Avg (KES)",
        ),
        _card_spec(
            p3,
            "v35_card_volatility_kes",
            "Price Volatility (KES)",
            1056,
            10,
            208,
            66,
            4,
            "Price Volatility (KES)",
        ),
        VisualSpec(
            page_name=p3,
            visual_id="v36_line_rolling_price",
            visual_type="lineChart",
            title="Monthly Closing Price, 12-Month Rolling Average, and Prior Year Price (KES)",
            x=16,
            y=86,
            width=740,
            height=304,
            z=5,
            query_state={
                "Category": {"projections": [col_proj("dim_date", "full_date", active=True)]},
                "Y": {
                    "projections": [
                        meas_proj("fact_prices", "Avg Price (KES)"),
                        meas_proj("fact_prices", "12-Month Rolling Avg (KES)"),
                        meas_proj("fact_prices", "Prior Year Price (KES)"),
                    ]
                },
                "Tooltips": {"projections": [meas_proj("fact_prices", "MoM Change %")]},
            },
        ),
        VisualSpec(
            page_name=p3,
            visual_id="v37_line_seasonality",
            visual_type="lineChart",
            title="Calendar Month Seasonal Index Profile (Jan-Dec, 1.000 = Annual Parity)",
            x=768,
            y=86,
            width=496,
            height=304,
            z=6,
            query_state={
                "Category": {"projections": [col_proj("dim_date", "month_name", active=True)]},
                "Series": {
                    "projections": [col_proj("dim_commodity", "commodity_name", active=True)]
                },
                "Y": {"projections": [meas_proj("fact_prices", "Seasonal Index")]},
            },
        ),
        VisualSpec(
            page_name=p3,
            visual_id="v38_bar_volatility",
            visual_type="clusteredBarChart",
            title="County Price Volatility CV % Ranking",
            x=16,
            y=402,
            width=620,
            height=304,
            z=7,
            query_state={
                "Category": {"projections": [col_proj("dim_markets", "adm2_name", active=True)]},
                "Y": {"projections": [meas_proj("fact_prices", "Price Volatility CV %")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "Price Volatility (KES)"),
                        meas_proj("fact_prices", "Commodity YoY Inflation %"),
                    ]
                },
            },
            sort=SortSpec("fact_prices", "Price Volatility CV %", "Descending"),
        ),
        VisualSpec(
            page_name=p3,
            visual_id="v39_col_season_window",
            visual_type="clusteredColumnChart",
            title="Seasonal Index by Kenyan Cropping Window and Commodity",
            x=648,
            y=402,
            width=616,
            height=304,
            z=8,
            query_state={
                "Category": {"projections": [col_proj("dim_date", "season", active=True)]},
                "Series": {
                    "projections": [col_proj("dim_commodity", "commodity_name", active=True)]
                },
                "Y": {"projections": [meas_proj("fact_prices", "Seasonal Index")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "Avg Price (KES)"),
                        meas_proj("fact_prices", "MoM Change %"),
                    ]
                },
            },
        ),
        # Page 4: Decisions and Action (9 visuals)
        _slicer_spec(
            p4,
            "v41_slicer_group",
            "Target County Group",
            16,
            10,
            280,
            66,
            0,
            "dim_markets",
            "county_group",
        ),
        _slicer_spec(
            p4,
            "v42_slicer_region",
            "Target Region",
            308,
            10,
            280,
            66,
            1,
            "dim_markets",
            "adm1_name",
        ),
        _card_spec(
            p4,
            "v43_card_coverage",
            "Field Survey Coverage %",
            600,
            10,
            216,
            66,
            2,
            "Survey Coverage Rate %",
        ),
        _card_spec(
            p4,
            "v44_card_gap",
            "Affordability Gap (KES)",
            828,
            10,
            216,
            66,
            3,
            "Affordability Gap (KES)",
        ),
        _card_spec(
            p4,
            "v45_card_completeness",
            "Data Completeness %",
            1056,
            10,
            208,
            66,
            4,
            "Data Completeness %",
        ),
        VisualSpec(
            page_name=p4,
            visual_id="v46_scatter_coverage_risk",
            visual_type="scatterChart",
            title="Monitoring Priority Quadrant: Survey Coverage % (X) vs Price Volatility CV % (Y)",
            x=16,
            y=86,
            width=580,
            height=310,
            z=5,
            query_state={
                "Category": {"projections": [col_proj("dim_markets", "adm2_name", active=True)]},
                "Series": {"projections": [col_proj("dim_markets", "county_group", active=True)]},
                "X": {"projections": [meas_proj("fact_prices", "Survey Coverage Rate %")]},
                "Y": {"projections": [meas_proj("fact_prices", "Price Volatility CV %")]},
                "Size": {"projections": [meas_proj("fact_prices", "Data Completeness %")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "YoY Inflation %"),
                        meas_proj("fact_prices", "Affordability Gap (KES)"),
                    ]
                },
            },
        ),
        VisualSpec(
            page_name=p4,
            visual_id="v47_table_priority_action",
            visual_type="tableEx",
            title="County Priority Action Matrix: Inflation, Affordability Gap, and Survey Coverage",
            x=608,
            y=86,
            width=656,
            height=310,
            z=6,
            query_state={
                "Values": {
                    "projections": [
                        col_proj("dim_markets", "adm2_name"),
                        col_proj("dim_markets", "county_group"),
                        meas_proj("fact_prices", "Data Completeness %"),
                        meas_proj("fact_prices", "Survey Coverage Rate %"),
                        meas_proj("fact_prices", "YoY Inflation %"),
                        meas_proj("fact_prices", "Affordability Gap (KES)"),
                        meas_proj("fact_prices", "Avg Price (KES)"),
                        meas_proj("fact_prices", "County Inflation Rank"),
                    ]
                }
            },
        ),
        VisualSpec(
            page_name=p4,
            visual_id="v48_bar_coverage_gap",
            visual_type="clusteredBarChart",
            title=(
                "Counties with Lowest Direct Field Survey Coverage % (Sentinel Expansion Targets)"
            ),
            x=16,
            y=408,
            width=580,
            height=298,
            z=7,
            query_state={
                "Category": {"projections": [col_proj("dim_markets", "adm2_name", active=True)]},
                "Y": {"projections": [meas_proj("fact_prices", "Survey Coverage Rate %")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "Data Completeness %"),
                        meas_proj("fact_prices", "Price Volatility CV %"),
                    ]
                },
            },
            sort=SortSpec("fact_prices", "Survey Coverage Rate %", "Ascending"),
        ),
        VisualSpec(
            page_name=p4,
            visual_id="v49_col_basket_by_region",
            visual_type="clusteredColumnChart",
            title="Average Commodity Price (KES) by Region and County Group",
            x=608,
            y=408,
            width=656,
            height=298,
            z=8,
            query_state={
                "Category": {"projections": [col_proj("dim_markets", "adm1_name", active=True)]},
                "Series": {"projections": [col_proj("dim_markets", "county_group", active=True)]},
                "Y": {"projections": [meas_proj("fact_prices", "Avg Price (KES)")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "YoY Inflation %"),
                        meas_proj("fact_prices", "National Food Price Index"),
                    ]
                },
            },
        ),
    )


def spec_to_visual_payload(spec: VisualSpec) -> dict[str, Any]:
    """Convert a VisualSpec into a schema-valid visual.json dictionary."""
    escaped_title = spec.title.replace("'", "''")
    query: dict[str, Any] = {"queryState": spec.query_state}
    if spec.sort is not None:
        query["sortDefinition"] = {
            "sort": [
                {
                    "field": {
                        "Measure": {
                            "Expression": {"SourceRef": {"Entity": spec.sort.entity}},
                            "Property": spec.sort.prop,
                        }
                    },
                    "direction": spec.sort.direction,
                }
            ],
            "isDefaultSort": False,
        }

    visual_obj: dict[str, Any] = {
        "visualType": spec.visual_type,
        "query": query,
        "visualContainerObjects": {
            "title": [
                {
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{escaped_title}'"}}},
                    }
                }
            ]
        },
    }
    if spec.objects is not None:
        visual_obj["objects"] = spec.objects

    return {
        "$schema": VISUAL_SCHEMA_URL,
        "name": spec.visual_id,
        "position": {
            "x": spec.x,
            "y": spec.y,
            "z": spec.z,
            "width": spec.width,
            "height": spec.height,
            "tabOrder": spec.z,
        },
        "visual": visual_obj,
    }


def generate_pbir_visuals(
    pages_dir: Path = DEFAULT_PAGES_DIR,
    specs: Sequence[VisualSpec] | None = None,
) -> dict[str, list[Path]]:
    """Replace stale visual directories and write schema-valid visual.json files per page."""
    resolved_specs = tuple(specs) if specs is not None else build_visual_specs()
    target_pages = {spec.page_name for spec in resolved_specs}
    for page_name in target_pages:
        visuals_root = pages_dir / page_name / "visuals"
        if visuals_root.exists():
            shutil.rmtree(visuals_root)

    written: dict[str, list[Path]] = {}
    for spec in resolved_specs:
        visual_dir = pages_dir / spec.page_name / "visuals" / spec.visual_id
        visual_dir.mkdir(parents=True, exist_ok=True)
        visual_path = visual_dir / "visual.json"
        payload = spec_to_visual_payload(spec)
        visual_path.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        written.setdefault(spec.page_name, []).append(visual_path)
    return written


def main() -> None:
    """CLI entrypoint to populate all 40 PBIR visual.json files."""
    written = generate_pbir_visuals()
    total = sum(len(paths) for paths in written.values())
    for page, paths in written.items():
        print(f"{page}: wrote {len(paths)} visuals")
    print(f"Total PBIR visuals written: {total}")


if __name__ == "__main__":
    main()
