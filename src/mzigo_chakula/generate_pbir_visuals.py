"""Generate themed PBIR report definition, pages, and 44 styled visuals."""

from __future__ import annotations

import json
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mzigo_chakula.data import PROJECT_ROOT

REPORT_ROOT = PROJECT_ROOT / "pbip" / "mzigo-chakula.Report"
REPORT_SCHEMA_URL = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/report/3.3.0/schema.json"
)
PAGE_SCHEMA_URL = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/page/2.1.0/schema.json"
)
VISUAL_SCHEMA_URL = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.14.0/schema.json"
)
THEME_FILENAME = "MzigoChakulaTheme.json"
DEFAULT_PAGES_DIR = REPORT_ROOT / "definition" / "pages"

PALETTE_NAVY = "#0F2942"
PALETTE_BLUE = "#1D4ED8"
PALETTE_TEAL = "#0F766E"
PALETTE_ORANGE = "#EA580C"
PALETTE_RED = "#B91C1C"
PALETTE_SLATE = "#475569"
PALETTE_BORDER = "#CBD5E1"
PALETTE_DIVIDER = "#E2E8F0"
PALETTE_HEADER_BG = "#F8FAFC"
PALETTE_CANVAS = "#F1F5F9"
PALETTE_SHADOW = "#64748B"

PAGE_METADATA: tuple[tuple[str, str, str], ...] = (
    (
        "ReportSectionExecutivePulse",
        "Executive Pulse",
        "Page 1: Executive Pulse | Rapid National Inflation & Staple Burden | Cross-Filtering Active",
    ),
    (
        "ReportSectionCountyCommodity",
        "County and Commodity",
        "Page 2: County & Commodity | ASAL vs. Agri/Urban Disparities & 233 Physical Markets",
    ),
    (
        "ReportSectionTrendsDiagnostics",
        "Trends and Diagnostics",
        "Page 3: Trends & Diagnostics | 2007-2026 Crop Trajectories, Seasonality & County Dispersion",
    ),
    (
        "ReportSectionDecisionsAction",
        "Decisions and Action",
        "Page 4: Decisions & Action | Survey Blind-Spot Triage & Intervention Priorities",
    ),
)


@dataclass(frozen=True)
class SortSpec:
    """Sort definition target measure and direction."""

    entity: str
    prop: str
    direction: str


@dataclass(frozen=True)
class VisualSpec:
    """Declarative specification for one styled PBIR visual container."""

    page_name: str
    visual_id: str
    visual_type: str
    title: str
    subtitle: str
    x: int
    y: int
    width: int
    height: int
    z: int
    query_state: dict[str, dict[str, Any]]
    sort: SortSpec | None = None
    objects: dict[str, Any] | None = None
    filter_config: dict[str, Any] | None = None
    border_color: str = PALETTE_BORDER
    is_banner: bool = False


def _lit(val: str) -> dict[str, Any]:
    """Wrap a Power BI Literal expression."""
    return {"expr": {"Literal": {"Value": val}}}


def _solid_color(hex_color: str) -> dict[str, Any]:
    """Wrap a Power BI solid fill color expression."""
    return {"solid": {"color": _lit(f"'{hex_color}'")}}


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


def agg_proj(entity: str, prop: str, func: int = 1) -> dict[str, Any]:
    """Build a PBIR Aggregation RoleProjection entry (1 = Average)."""
    return {
        "field": {
            "Aggregation": {
                "Expression": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": entity}},
                        "Property": prop,
                    }
                },
                "Function": func,
            }
        },
        "queryRef": f"Avg({entity}.{prop})",
        "nativeQueryRef": f"Average of {prop}",
    }


def _commodity_in_filter(filter_name: str, commodity_ids: tuple[str, ...]) -> dict[str, Any]:
    """Create a PBIR Categorical filter on dim_commodity[commodity_id]."""
    return {
        "filters": [
            {
                "name": filter_name,
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": "dim_commodity"}},
                        "Property": "commodity_id",
                    }
                },
                "type": "Categorical",
                "filter": {
                    "Version": 2,
                    "From": [{"Name": "c", "Entity": "dim_commodity", "Type": 0}],
                    "Where": [
                        {
                            "Condition": {
                                "In": {
                                    "Expressions": [
                                        {
                                            "Column": {
                                                "Expression": {"SourceRef": {"Source": "c"}},
                                                "Property": "commodity_id",
                                            }
                                        }
                                    ],
                                    "Values": [[{"Literal": {"Value": f"'{cid}'"}}] for cid in commodity_ids],
                                }
                            }
                        }
                    ],
                },
                "howCreated": "User",
                "isHiddenInViewMode": False,
            }
        ]
    }


def _banner_spec(page_name: str, subtitle: str) -> VisualSpec:
    """Create the top navy header banner card for a report page."""
    return VisualSpec(
        page_name=page_name,
        visual_id="v00_header_banner",
        visual_type="card",
        title="MZIGO CHAKULA | KENYA FOOD PRICE & AFFORDABILITY INTELLIGENCE (2007-2026)",
        subtitle=subtitle,
        x=16,
        y=6,
        width=1248,
        height=38,
        z=0,
        query_state={"Values": {"projections": [meas_proj("fact_prices", "Data Completeness %")]}},
        objects={
            "labels": [
                {
                    "properties": {
                        "color": _solid_color(PALETTE_NAVY),
                        "fontSize": _lit("8D"),
                    }
                }
            ],
            "categoryLabels": [{"properties": {"show": _lit("false")}}],
        },
        border_color=PALETTE_NAVY,
        is_banner=True,
    )


def _slicer_spec(
    page_name: str,
    visual_id: str,
    title: str,
    subtitle: str,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
    entity: str,
    column: str,
) -> VisualSpec:
    """Create a styled Dropdown slicer specification bound to a single dimension column."""
    return VisualSpec(
        page_name=page_name,
        visual_id=visual_id,
        visual_type="slicer",
        title=title,
        subtitle=subtitle,
        x=x,
        y=y,
        width=width,
        height=height,
        z=z,
        query_state={"Values": {"projections": [col_proj(entity, column, active=True)]}},
        objects={
            "data": [{"properties": {"mode": _lit("'Dropdown'")}}],
            "header": [{"properties": {"show": _lit("false")}}],
        },
    )


def _card_spec(
    page_name: str,
    visual_id: str,
    title: str,
    subtitle: str,
    x: int,
    y: int,
    width: int,
    height: int,
    z: int,
    measure: str,
    accent: str = PALETTE_BLUE,
    entity: str = "fact_prices",
) -> VisualSpec:
    """Create an executive KPI card visual specification bound to a single measure."""
    return VisualSpec(
        page_name=page_name,
        visual_id=visual_id,
        visual_type="card",
        title=title,
        subtitle=subtitle,
        x=x,
        y=y,
        width=width,
        height=height,
        z=z,
        query_state={"Values": {"projections": [meas_proj(entity, measure)]}},
        objects={
            "labels": [
                {
                    "properties": {
                        "fontSize": _lit("19D"),
                        "color": _solid_color(PALETTE_NAVY),
                        "labelDisplayUnits": _lit("1D"),
                    }
                }
            ],
            "categoryLabels": [{"properties": {"show": _lit("false")}}],
        },
        border_color=accent,
    )


def _data_labels_on() -> dict[str, Any]:
    """Enable clean data labels directly on bar and column marks."""
    return {"labels": [{"properties": {"show": _lit("true")}}]}


def build_theme_payload() -> dict[str, Any]:
    """Return custom Power BI theme matching the 300 DPI editorial palette."""
    return {
        "name": "MzigoChakulaTheme",
        "dataColors": [
            PALETTE_TEAL,
            PALETTE_ORANGE,
            PALETTE_BLUE,
            PALETTE_NAVY,
            PALETTE_RED,
            "#D97706",
            "#4338CA",
            "#0369A1",
            "#15803D",
            "#7C2D12",
        ],
        "foreground": "#0F172A",
        "foregroundNeutralSecondary": "#475569",
        "foregroundNeutralTertiary": "#94A3B8",
        "background": "#FFFFFF",
        "backgroundLight": "#F8FAFC",
        "backgroundNeutral": "#E2E8F0",
        "tableAccent": PALETTE_TEAL,
        "good": PALETTE_TEAL,
        "neutral": "#D97706",
        "bad": PALETTE_RED,
        "maximum": PALETTE_BLUE,
        "center": "#D97706",
        "minimum": "#E0F2FE",
        "null": "#94A3B8",
        "hyperlink": PALETTE_BLUE,
        "visitedHyperlink": PALETTE_TEAL,
        "textClasses": {
            "callout": {"fontSize": 20, "fontFace": "Segoe UI Bold", "color": PALETTE_NAVY},
            "title": {"fontSize": 11, "fontFace": "Segoe UI Semibold", "color": PALETTE_NAVY},
            "header": {"fontSize": 10, "fontFace": "Segoe UI Semibold", "color": PALETTE_NAVY},
            "label": {"fontSize": 9, "fontFace": "Segoe UI", "color": "#334155"},
        },
        "visualStyles": {
            "tableEx": {
                "*": {
                    "columnHeaders": [
                        {
                            "backColor": {"solid": {"color": PALETTE_NAVY}},
                            "fontColor": {"solid": {"color": "#FFFFFF"}},
                            "bold": True,
                            "fontSize": 9,
                        }
                    ],
                    "values": [
                        {
                            "backColorPrimary": {"solid": {"color": "#FFFFFF"}},
                            "backColorSecondary": {"solid": {"color": "#F8FAFC"}},
                            "fontColorPrimary": {"solid": {"color": "#0F172A"}},
                            "fontColorSecondary": {"solid": {"color": "#0F172A"}},
                            "fontSize": 9,
                        }
                    ],
                }
            }
        },
    }


def build_report_payload() -> dict[str, Any]:
    """Return PBIR definition/report.json registering CY24SU10 base and custom theme."""
    return {
        "$schema": REPORT_SCHEMA_URL,
        "themeCollection": {
            "baseTheme": {
                "name": "CY24SU10",
                "reportVersionAtImport": {"visual": "1.8.91", "report": "2.0.91", "page": "1.3.91"},
                "type": "SharedResources",
            },
            "customTheme": {
                "name": THEME_FILENAME,
                "reportVersionAtImport": {"visual": "2.14.0", "report": "3.3.0", "page": "2.1.0"},
                "type": "RegisteredResources",
            },
        },
        "resourcePackages": [
            {
                "name": "SharedResources",
                "type": "SharedResources",
                "items": [
                    {
                        "name": "CY24SU10",
                        "path": "BaseThemes/CY24SU10.json",
                        "type": "BaseTheme",
                    }
                ],
            },
            {
                "name": "RegisteredResources",
                "type": "RegisteredResources",
                "items": [
                    {
                        "name": THEME_FILENAME,
                        "path": THEME_FILENAME,
                        "type": "CustomTheme",
                    }
                ],
            },
        ],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultFilterActionIsDataFilter": True,
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": False,
            "useDefaultAggregateDisplayName": True,
        },
    }


def build_visual_specs() -> tuple[VisualSpec, ...]:
    """Return all 44 styled PBIR visual specifications across the 4 report pages."""
    p1, _, p1_sub = PAGE_METADATA[0]
    p2, _, p2_sub = PAGE_METADATA[1]
    p3, _, p3_sub = PAGE_METADATA[2]
    p4, _, p4_sub = PAGE_METADATA[3]

    return (
        # Page 1: Executive Pulse (banner + 14 visuals)
        _banner_spec(p1, p1_sub),
        _slicer_spec(p1, "v01_slicer_year", "Year", "2007 to 2026", 16, 50, 236, 52, 1, "dim_date", "year"),
        _slicer_spec(
            p1,
            "v02_slicer_group",
            "County Group",
            "ASAL vs Agri/Urban",
            262,
            50,
            246,
            52,
            2,
            "dim_markets",
            "county_group",
        ),
        _slicer_spec(
            p1,
            "v03_slicer_commodity",
            "Commodity",
            "3 tracked staples",
            518,
            50,
            246,
            52,
            3,
            "dim_commodity",
            "commodity_name",
        ),
        _slicer_spec(
            p1,
            "v04_slicer_season",
            "Cropping Season",
            "4 rainfall regimes",
            774,
            50,
            246,
            52,
            4,
            "dim_date",
            "season",
        ),
        _slicer_spec(
            p1,
            "v05_slicer_region",
            "Region",
            "7 Kenya regions",
            1030,
            50,
            234,
            52,
            5,
            "dim_markets",
            "adm1_name",
        ),
        _card_spec(
            p1,
            "v06_card_fpi",
            "National Food Price Index",
            "Grain-safe (mkt, month) mean",
            16,
            108,
            240,
            84,
            6,
            "National Food Price Index",
            PALETTE_BLUE,
        ),
        _card_spec(
            p1,
            "v07_card_yoy",
            "YoY Food Inflation %",
            "Gap-safe EDATE -12m change",
            268,
            108,
            240,
            84,
            7,
            "YoY Inflation %",
            PALETTE_ORANGE,
        ),
        _card_spec(
            p1,
            "v08_card_avg_price",
            "Avg Commodity Price (KES)",
            "Filter by Commodity above",
            520,
            108,
            240,
            84,
            8,
            "Avg Price (KES)",
            PALETTE_TEAL,
        ),
        _card_spec(
            p1,
            "v09_card_completeness",
            "Data Completeness %",
            "Populated model grid share",
            772,
            108,
            240,
            84,
            9,
            "Data Completeness %",
            PALETTE_RED,
        ),
        _card_spec(
            p1,
            "v10_card_coverage",
            "Field Survey Coverage %",
            "Direct raw enumerator logs",
            1024,
            108,
            240,
            84,
            10,
            "Survey Coverage Rate %",
            PALETTE_SLATE,
        ),
        VisualSpec(
            page_name=p1,
            visual_id="v11_line_fpi_trend",
            visual_type="lineChart",
            title="National Food Price Index Trend (2007-2026)",
            subtitle="Grain-safe composite index alongside YTD running mean",
            x=16,
            y=200,
            width=756,
            height=256,
            z=11,
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
            visual_type="barChart",
            title="Counties Ranked by YoY Food Inflation %",
            subtitle="Teal: Agricultural & Urban | Orange: ASAL counties",
            x=784,
            y=200,
            width=480,
            height=256,
            z=12,
            query_state={
                "Category": {"projections": [col_proj("dim_markets", "adm2_name", active=True)]},
                "Series": {"projections": [col_proj("dim_markets", "county_group", active=True)]},
                "Y": {"projections": [meas_proj("fact_prices", "YoY Inflation %")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "National Food Price Index"),
                        meas_proj("fact_prices", "County Inflation Rank"),
                    ]
                },
            },
            sort=SortSpec("fact_prices", "YoY Inflation %", "Descending"),
            objects=_data_labels_on(),
        ),
        VisualSpec(
            page_name=p1,
            visual_id="v13_table_commodities",
            visual_type="tableEx",
            title="Commodity Price, YoY Growth & Volatility Matrix",
            subtitle="Unit-safe statistics across 55,454 physical market-months",
            x=16,
            y=464,
            width=756,
            height=246,
            z=13,
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
            title="County Inflation Watchlist & Rank",
            subtitle="Dense descending rank across covered Kenyan counties",
            x=784,
            y=464,
            width=480,
            height=246,
            z=14,
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
        # Page 2: County and Commodity (banner + 8 visuals)
        _banner_spec(p2, p2_sub),
        _slicer_spec(
            p2,
            "v21_slicer_commodity",
            "Commodity",
            "3 tracked staples",
            16,
            50,
            300,
            52,
            1,
            "dim_commodity",
            "commodity_name",
        ),
        _slicer_spec(
            p2,
            "v22_slicer_group",
            "County Group",
            "ASAL vs Agri/Urban",
            328,
            50,
            300,
            52,
            2,
            "dim_markets",
            "county_group",
        ),
        _slicer_spec(
            p2, "v23_slicer_region", "Region", "7 Kenya regions", 640, 50, 300, 52, 3, "dim_markets", "adm1_name"
        ),
        _slicer_spec(p2, "v24_slicer_year", "Year", "2007 to 2026", 952, 50, 312, 52, 4, "dim_date", "year"),
        VisualSpec(
            page_name=p2,
            visual_id="v25_bar_affordability_gap",
            visual_type="barChart",
            title="Maize Affordability Gap vs National Mean (KES/kg)",
            subtitle="Visual filtered to Maize (1 kg) | Teal: Agri/Urban, Orange: ASAL",
            x=16,
            y=116,
            width=620,
            height=288,
            z=5,
            query_state={
                "Category": {"projections": [col_proj("dim_markets", "adm2_name", active=True)]},
                "Series": {"projections": [col_proj("dim_markets", "county_group", active=True)]},
                "Y": {"projections": [meas_proj("fact_prices", "Affordability Gap (KES)")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "Avg Price (KES)"),
                        meas_proj("fact_prices", "Prior Year Price (KES)"),
                    ]
                },
            },
            sort=SortSpec("fact_prices", "Affordability Gap (KES)", "Descending"),
            objects=_data_labels_on(),
            filter_config=_commodity_in_filter("f_v25_maize", ("maize_fao",)),
        ),
        VisualSpec(
            page_name=p2,
            visual_id="v26_scatter_county_risk",
            visual_type="scatterChart",
            title="Geographic Distribution of 233 Physical Kenyan Markets (Lon vs Lat)",
            subtitle="Plotted from market coordinates | Teal: 31 Agri/Urban, Orange: 202 ASAL",
            x=648,
            y=116,
            width=616,
            height=288,
            z=6,
            query_state={
                "Category": {"projections": [col_proj("dim_markets", "mkt_name", active=True)]},
                "Series": {"projections": [col_proj("dim_markets", "county_group", active=True)]},
                "X": {"projections": [agg_proj("dim_markets", "lon", func=1)]},
                "Y": {"projections": [agg_proj("dim_markets", "lat", func=1)]},
                "Size": {"projections": [meas_proj("fact_prices", "Price Volatility CV %")]},
                "Tooltips": {
                    "projections": [
                        col_proj("dim_markets", "adm2_name"),
                        meas_proj("fact_prices", "Affordability Gap (KES)"),
                    ]
                },
            },
        ),
        VisualSpec(
            page_name=p2,
            visual_id="v27_col_group_comparison",
            visual_type="clusteredColumnChart",
            title="Price Volatility Comparison (CV %): ASAL vs Agri & Urban",
            subtitle="Coefficient of variation across Beans, Goat, and Maize",
            x=16,
            y=412,
            width=520,
            height=298,
            z=7,
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
            objects=_data_labels_on(),
        ),
        VisualSpec(
            page_name=p2,
            visual_id="v28_table_county_drill",
            visual_type="tableEx",
            title="County and Physical Market Affordability Matrix",
            subtitle="Mean price, gap vs benchmark, YoY growth, and CV % by market",
            x=548,
            y=412,
            width=716,
            height=298,
            z=8,
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
        # Page 3: Trends and Diagnostics (banner + 9 visuals)
        _banner_spec(p3, p3_sub),
        _slicer_spec(
            p3,
            "v31_slicer_commodity",
            "Select Commodity",
            "3 tracked staples",
            16,
            50,
            280,
            58,
            1,
            "dim_commodity",
            "commodity_name",
        ),
        _slicer_spec(
            p3,
            "v32_slicer_group",
            "Select County Group",
            "ASAL vs Agri/Urban",
            308,
            50,
            280,
            58,
            2,
            "dim_markets",
            "county_group",
        ),
        _card_spec(
            p3,
            "v33_card_mom",
            "MoM Price Change %",
            "Gap-safe prior month delta",
            600,
            50,
            216,
            58,
            3,
            "MoM Change %",
            PALETTE_ORANGE,
        ),
        _card_spec(
            p3,
            "v34_card_rolling",
            "12m Rolling Avg (KES)",
            "Trailing 12-month smoothed",
            828,
            50,
            216,
            58,
            4,
            "12-Month Rolling Avg (KES)",
            PALETTE_BLUE,
        ),
        _card_spec(
            p3,
            "v35_card_volatility_kes",
            "Price Volatility (KES)",
            "Sample StdDev (STDEV.S)",
            1056,
            50,
            208,
            58,
            5,
            "Price Volatility (KES)",
            PALETTE_TEAL,
        ),
        VisualSpec(
            page_name=p3,
            visual_id="v36_line_rolling_price",
            visual_type="lineChart",
            title="Beans & Maize Retail Prices (KES/kg, 2007-2026)",
            subtitle="Filtered to 1 kg staples (Beans & Maize); hover for 12m Rolling Avg & MoM %",
            x=16,
            y=116,
            width=740,
            height=288,
            z=6,
            query_state={
                "Category": {"projections": [col_proj("dim_date", "full_date", active=True)]},
                "Series": {"projections": [col_proj("dim_commodity", "commodity_name", active=True)]},
                "Y": {"projections": [meas_proj("fact_prices", "Avg Price (KES)")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "12-Month Rolling Avg (KES)"),
                        meas_proj("fact_prices", "MoM Change %"),
                    ]
                },
            },
            filter_config=_commodity_in_filter("f_v36_staples", ("beans", "maize_fao")),
        ),
        VisualSpec(
            page_name=p3,
            visual_id="v37_line_seasonality",
            visual_type="lineChart",
            title="Monthly Seasonal Index Cycle (Jan-Dec, Parity = 1.000)",
            subtitle="Crop staples peak Jun-Sep; live goats peak Dec-Feb",
            x=768,
            y=116,
            width=496,
            height=288,
            z=7,
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
            visual_type="barChart",
            title="Counties by Maize Price Volatility (CV % = StdDev / Mean)",
            subtitle="Filtered to Maize (1 kg) | Teal: Agri/Urban, Orange: ASAL",
            x=16,
            y=412,
            width=620,
            height=298,
            z=8,
            query_state={
                "Category": {"projections": [col_proj("dim_markets", "adm2_name", active=True)]},
                "Series": {"projections": [col_proj("dim_markets", "county_group", active=True)]},
                "Y": {"projections": [meas_proj("fact_prices", "Price Volatility CV %")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "Price Volatility (KES)"),
                        meas_proj("fact_prices", "Commodity YoY Inflation %"),
                    ]
                },
            },
            sort=SortSpec("fact_prices", "Price Volatility CV %", "Descending"),
            objects=_data_labels_on(),
            filter_config=_commodity_in_filter("f_v38_maize_cv", ("maize_fao",)),
        ),
        VisualSpec(
            page_name=p3,
            visual_id="v39_col_season_window",
            visual_type="clusteredColumnChart",
            title="Seasonal Index by Kenyan Cropping Window & Commodity",
            subtitle="Includes gap-safe MoM Change % & Avg Price tooltips",
            x=648,
            y=412,
            width=616,
            height=298,
            z=9,
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
            objects=_data_labels_on(),
        ),
        # Page 4: Decisions and Action (banner + 9 visuals)
        _banner_spec(p4, p4_sub),
        _slicer_spec(
            p4,
            "v41_slicer_group",
            "Target County Group",
            "ASAL vs Agri/Urban",
            16,
            50,
            280,
            58,
            1,
            "dim_markets",
            "county_group",
        ),
        _slicer_spec(
            p4, "v42_slicer_region", "Target Region", "7 Kenya regions", 308, 50, 280, 58, 2, "dim_markets", "adm1_name"
        ),
        _card_spec(
            p4,
            "v43_card_coverage",
            "Field Survey Coverage %",
            "Raw enumerator share",
            600,
            50,
            216,
            58,
            3,
            "Survey Coverage Rate %",
            PALETTE_RED,
        ),
        _card_spec(
            p4,
            "v44_card_gap",
            "Affordability Gap (KES)",
            "Local vs national mean",
            828,
            50,
            216,
            58,
            4,
            "Affordability Gap (KES)",
            PALETTE_ORANGE,
        ),
        _card_spec(
            p4,
            "v45_card_completeness",
            "Data Completeness %",
            "Model coverage rate",
            1056,
            50,
            208,
            58,
            5,
            "Data Completeness %",
            PALETTE_TEAL,
        ),
        VisualSpec(
            page_name=p4,
            visual_id="v46_scatter_coverage_risk",
            visual_type="scatterChart",
            title="Monitoring Priority Quadrant: Survey % (X) vs Maize Volatility CV % (Y)",
            subtitle="Filtered to Maize (1 kg) | Top-left flags urgent enumerator blind spots",
            x=16,
            y=116,
            width=580,
            height=288,
            z=6,
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
            filter_config=_commodity_in_filter("f_v46_maize_quad", ("maize_fao",)),
        ),
        VisualSpec(
            page_name=p4,
            visual_id="v47_table_priority_action",
            visual_type="tableEx",
            title="County Priority Action Matrix: Inflation, Gap & Survey Rate",
            subtitle="Combines index rank, price gap, and direct field check share",
            x=608,
            y=116,
            width=656,
            height=288,
            z=7,
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
            visual_type="barChart",
            title="Counties by Direct Field Survey Coverage % (Sentinel Expansion)",
            subtitle="Lowest coverage targets prioritized for enumerator deployment",
            x=16,
            y=412,
            width=580,
            height=298,
            z=8,
            query_state={
                "Category": {"projections": [col_proj("dim_markets", "adm2_name", active=True)]},
                "Series": {"projections": [col_proj("dim_markets", "county_group", active=True)]},
                "Y": {"projections": [meas_proj("fact_prices", "Survey Coverage Rate %")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "Data Completeness %"),
                        meas_proj("fact_prices", "Price Volatility CV %"),
                    ]
                },
            },
            sort=SortSpec("fact_prices", "Survey Coverage Rate %", "Ascending"),
            objects=_data_labels_on(),
        ),
        VisualSpec(
            page_name=p4,
            visual_id="v49_col_basket_by_region",
            visual_type="clusteredColumnChart",
            title="Average Commodity Price (KES) by Region & County Group",
            subtitle="Regional cost disparities across 7 covered Kenyan provinces",
            x=608,
            y=412,
            width=656,
            height=298,
            z=9,
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
            objects=_data_labels_on(),
        ),
    )


def _container_objects(spec: VisualSpec) -> dict[str, Any]:
    """Build executive visualContainerObjects styling for cards, charts, slicers, and banners."""
    escaped_title = spec.title.replace("'", "''")
    escaped_sub = spec.subtitle.replace("'", "''")

    if spec.is_banner:
        return {
            "background": [{"properties": {"show": _lit("true"), "color": _solid_color(PALETTE_NAVY), "transparency": _lit("0D")}}],
            "border": [{"properties": {"show": _lit("true"), "color": _solid_color(PALETTE_NAVY), "radius": _lit("6D"), "width": _lit("1D")}}],
            "dropShadow": [{"properties": {"show": _lit("false")}}],
            "title": [
                {
                    "properties": {
                        "show": _lit("true"),
                        "text": _lit(f"'{escaped_title}'"),
                        "fontColor": _solid_color("#FFFFFF"),
                        "background": _solid_color(PALETTE_NAVY),
                        "fontSize": _lit("11D"),
                        "bold": _lit("true"),
                        "fontFamily": _lit("'Segoe UI Semibold'"),
                        "titleWrap": _lit("false"),
                    }
                }
            ],
            "subTitle": [
                {
                    "properties": {
                        "show": _lit("true"),
                        "text": _lit(f"'{escaped_sub}'"),
                        "fontColor": _solid_color("#93C5FD"),
                        "fontSize": _lit("8D"),
                        "fontFamily": _lit("'Segoe UI'"),
                        "titleWrap": _lit("false"),
                    }
                }
            ],
            "divider": [{"properties": {"show": _lit("false")}}],
            "visualHeader": [{"properties": {"show": _lit("false")}}],
            "padding": [
                {
                    "properties": {
                        "top": _lit("2D"),
                        "bottom": _lit("2D"),
                        "left": _lit("10D"),
                        "right": _lit("10D"),
                    }
                }
            ],
        }

    is_slicer = spec.visual_type == "slicer"
    return {
        "background": [{"properties": {"show": _lit("true"), "color": _solid_color("#FFFFFF"), "transparency": _lit("0D")}}],
        "border": [{"properties": {"show": _lit("true"), "color": _solid_color(spec.border_color), "radius": _lit("8D"), "width": _lit("1D")}}],
        "dropShadow": [
            {
                "properties": {
                    "show": _lit("true"),
                    "color": _solid_color(PALETTE_SHADOW),
                    "position": _lit("'Outer'"),
                    "preset": _lit("'BottomRight'"),
                    "transparency": _lit("85D"),
                }
            }
        ],
        "title": [
            {
                "properties": {
                    "show": _lit("true"),
                    "text": _lit(f"'{escaped_title}'"),
                    "fontColor": _solid_color(PALETTE_NAVY),
                    "background": _solid_color(PALETTE_HEADER_BG),
                    "fontSize": _lit("9D" if is_slicer else "10D"),
                    "bold": _lit("true"),
                    "fontFamily": _lit("'Segoe UI Semibold'"),
                    "titleWrap": _lit("true"),
                }
            }
        ],
        "subTitle": [
            {
                "properties": {
                    "show": _lit("false" if is_slicer else "true"),
                    "text": _lit(f"'{escaped_sub}'"),
                    "fontColor": _solid_color(PALETTE_SLATE),
                    "fontSize": _lit("8D"),
                    "fontFamily": _lit("'Segoe UI'"),
                    "titleWrap": _lit("true"),
                }
            }
        ],
        "divider": [{"properties": {"show": _lit("false" if is_slicer else "true"), "color": _solid_color(PALETTE_DIVIDER), "width": _lit("1D")}}],
        "padding": [
            {
                "properties": {
                    "top": _lit("3D" if is_slicer else "6D"),
                    "bottom": _lit("3D" if is_slicer else "6D"),
                    "left": _lit("6D"),
                    "right": _lit("6D"),
                }
            }
        ],
    }


def spec_to_visual_payload(spec: VisualSpec) -> dict[str, Any]:
    """Convert a VisualSpec into a schema-valid visual.json dictionary."""
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
        "visualContainerObjects": _container_objects(spec),
    }
    if spec.objects is not None:
        visual_obj["objects"] = spec.objects

    payload: dict[str, Any] = {
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
    if spec.filter_config is not None:
        payload["filterConfig"] = spec.filter_config
    return payload


def build_page_payload(page_id: str, display_name: str) -> dict[str, Any]:
    """Return a styled page.json payload with light slate canvas and outspace."""
    return {
        "$schema": PAGE_SCHEMA_URL,
        "name": page_id,
        "displayName": display_name,
        "displayOption": "FitToPage",
        "height": 720,
        "width": 1280,
        "objects": {
            "background": [
                {
                    "properties": {
                        "color": _solid_color(PALETTE_CANVAS),
                        "transparency": _lit("0D"),
                    }
                }
            ],
            "outspace": [{"properties": {"color": _solid_color(PALETTE_DIVIDER)}}],
        },
    }


def generate_pbir_visuals(
    pages_dir: Path = DEFAULT_PAGES_DIR,
    specs: Sequence[VisualSpec] | None = None,
    report_root: Path | None = None,
) -> dict[str, list[Path]]:
    """Write theme, report.json, styled page.json files, and all 44 visual.json files."""
    resolved_report_root = report_root or pages_dir.parent.parent
    theme_dir = resolved_report_root / "StaticResources" / "RegisteredResources"
    theme_dir.mkdir(parents=True, exist_ok=True)
    (theme_dir / THEME_FILENAME).write_text(
        json.dumps(build_theme_payload(), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    def_dir = pages_dir.parent
    def_dir.mkdir(parents=True, exist_ok=True)
    (def_dir / "report.json").write_text(
        json.dumps(build_report_payload(), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    pages_dir.mkdir(parents=True, exist_ok=True)
    for page_id, display_name, _ in PAGE_METADATA:
        page_dir = pages_dir / page_id
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "page.json").write_text(
            json.dumps(build_page_payload(page_id, display_name), indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

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
    """CLI entrypoint to generate custom theme, page styling, and 44 PBIR visuals."""
    written = generate_pbir_visuals()
    total = sum(len(paths) for paths in written.values())
    for page, paths in written.items():
        print(f"{page}: wrote {len(paths)} visuals")
    print(f"Total PBIR visuals written: {total}")


if __name__ == "__main__":
    main()
