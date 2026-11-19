"""Generate themed PBIR report definition, pages, and 46 non-overlapping visuals."""

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
PALETTE_NAVY_IDLE = "#1E3A5F"
PALETTE_NAV_ACTIVE = "#0284C7"
PALETTE_NAV_HOVER = "#0369A1"
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
        "Page 1: Executive Pulse | Recent 12m Inflation & Staple Burden",
    ),
    (
        "ReportSectionCountyCommodity",
        "County and Commodity",
        "Page 2: County & Commodity | ASAL Gaps & 233 Physical Markets",
    ),
    (
        "ReportSectionTrendsDiagnostics",
        "Trends and Diagnostics",
        "Page 3: Trends & Diagnostics | 19-Year Curves & Seasonality",
    ),
    (
        "ReportSectionDecisionsAction",
        "Decisions and Action",
        "Page 4: Decisions & Action | Survey Blind Spots & Priorities",
    ),
)

TOP10_RECENT_COUNTIES: tuple[str, ...] = (
    "Tharaka Nithi",
    "Marsabit",
    "Kisumu",
    "Nakuru",
    "Samburu",
    "Mandera",
    "Wajir",
    "Turkana",
    "West Pokot",
    "Machakos",
)

DIVERGING_MAIZE_COUNTIES: tuple[str, ...] = (
    "Turkana",
    "Mandera",
    "Kisumu",
    "Wajir",
    "West Pokot",
    "Meru",
    "Tharaka Nithi",
    "Embu",
    "Kitui",
    "Lamu",
)

TOP10_MAIZE_CV_COUNTIES: tuple[str, ...] = (
    "Embu",
    "Tharaka Nithi",
    "Meru",
    "Kitui",
    "Makueni",
    "Isiolo",
    "Garissa",
    "Lamu",
    "Uasin Gishu",
    "Tana River",
)

LOW_SURVEY_COUNTIES: tuple[str, ...] = (
    "Mombasa",
    "Nairobi",
    "Turkana",
    "Baringo",
    "Isiolo",
    "Marsabit",
    "Tana River",
    "Garissa",
    "Mandera",
    "Kajiado",
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
    query_state: dict[str, dict[str, Any]] | None = None
    sort: SortSpec | None = None
    objects: dict[str, Any] | None = None
    filter_config: dict[str, Any] | None = None
    border_color: str = PALETTE_BORDER
    is_banner: bool = False
    is_page_nav: bool = False


def _lit(val: str) -> dict[str, Any]:
    """Wrap a Power BI Literal expression."""
    return {"expr": {"Literal": {"Value": val}}}


def _solid_color(hex_color: str) -> dict[str, Any]:
    """Wrap a Power BI solid fill color expression."""
    return {"solid": {"color": _lit(f"'{hex_color}'")}}


def col_proj(
    entity: str,
    prop: str,
    active: bool | None = None,
    display_name: str | None = None,
) -> dict[str, Any]:
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
    if display_name is not None:
        proj["displayName"] = display_name
    return proj


def meas_proj(
    entity: str,
    prop: str,
    display_name: str | None = None,
) -> dict[str, Any]:
    """Build a PBIR measure RoleProjection entry."""
    proj: dict[str, Any] = {
        "field": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": entity}},
                "Property": prop,
            }
        },
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
    }
    if display_name is not None:
        proj["displayName"] = display_name
    return proj


def agg_proj(
    entity: str,
    prop: str,
    func: int = 1,
    display_name: str | None = None,
) -> dict[str, Any]:
    """Build a PBIR Aggregation RoleProjection entry (1 = Average)."""
    proj: dict[str, Any] = {
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
    if display_name is not None:
        proj["displayName"] = display_name
    return proj


def _in_filter(
    filter_name: str,
    entity: str,
    prop: str,
    literal_values: Sequence[str],
) -> dict[str, Any]:
    """Build a PBIR Categorical In filter for one entity column."""
    alias = "f"
    return {
        "filters": [
            {
                "name": filter_name,
                "field": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": entity}},
                        "Property": prop,
                    }
                },
                "type": "Categorical",
                "filter": {
                    "Version": 2,
                    "From": [{"Name": alias, "Entity": entity, "Type": 0}],
                    "Where": [
                        {
                            "Condition": {
                                "In": {
                                    "Expressions": [
                                        {
                                            "Column": {
                                                "Expression": {"SourceRef": {"Source": alias}},
                                                "Property": prop,
                                            }
                                        }
                                    ],
                                    "Values": [[{"Literal": {"Value": val}}] for val in literal_values],
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


def _categorical_in_filter(
    filter_name: str,
    entity: str,
    prop: str,
    values: tuple[str, ...],
) -> dict[str, Any]:
    """Create a PBIR Categorical In filter for string values."""
    return _in_filter(filter_name, entity, prop, [f"'{val}'" for val in values])


def _bool_filter(
    filter_name: str,
    entity: str,
    prop: str,
    value: bool,
) -> dict[str, Any]:
    """Create a PBIR Categorical In filter for a Boolean column."""
    return _in_filter(filter_name, entity, prop, ["true" if value else "false"])


def _combine_filters(*filter_dicts: dict[str, Any]) -> dict[str, Any]:
    """Merge multiple PBIR filter dictionaries into one filterConfig payload."""
    merged: list[dict[str, Any]] = []
    for fdict in filter_dicts:
        merged.extend(fdict.get("filters", []))
    return {"filters": merged}


def _clean_chart_objects(
    *,
    data_labels: bool = False,
    hide_legend: bool = False,
    hide_legend_title: bool = True,
    hide_x_title: bool = True,
    hide_y_title: bool = False,
    category_font_size: str | None = None,
) -> dict[str, Any]:
    """Return consistent axis, legend, and data-label settings for cartesian charts."""
    objects: dict[str, Any] = {}
    if hide_legend:
        objects["legend"] = [{"properties": {"show": _lit("false")}}]
    elif hide_legend_title:
        objects["legend"] = [{"properties": {"show": _lit("true"), "showTitle": _lit("false")}}]

    cat_props: dict[str, Any] = {}
    if hide_x_title:
        cat_props["showAxisTitle"] = _lit("false")
    if category_font_size is not None:
        cat_props["fontSize"] = _lit(f"{category_font_size}D")
    if cat_props:
        objects["categoryAxis"] = [{"properties": cat_props}]

    if hide_y_title:
        objects["valueAxis"] = [{"properties": {"showAxisTitle": _lit("false")}}]

    if data_labels:
        objects["labels"] = [{"properties": {"show": _lit("true")}}]
    return objects


def _clean_table_objects() -> dict[str, Any]:
    """Suppress mixed-unit grand totals and tighten row padding so 10 rows fit cleanly."""
    return {
        "total": [{"properties": {"totals": _lit("false")}}],
        "grid": [{"properties": {"rowPadding": _lit("1D")}}],
    }


def _scatter_objects(*, bubble_size: str = "-18D", hide_legend_title: bool = True) -> dict[str, Any]:
    """Configure crisp, non-blobby circular markers and concise legends on scatter plots."""
    objects: dict[str, Any] = {
        "bubbles": [{"properties": {"bubbleSize": _lit(bubble_size)}}],
    }
    if hide_legend_title:
        objects["legend"] = [{"properties": {"show": _lit("true"), "showTitle": _lit("false")}}]
    return objects


def _banner_spec(page_name: str, subtitle: str) -> VisualSpec:
    """Create the left navy title banner sitting flush beside the top pageNavigator."""
    return VisualSpec(
        page_name=page_name,
        visual_id="v00_header_banner",
        visual_type="card",
        title="MZIGO CHAKULA | Kenya Food Price & Affordability",
        subtitle=subtitle,
        x=16,
        y=8,
        width=624,
        height=52,
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


def _page_nav_spec(page_name: str) -> VisualSpec:
    """Create the native horizontal pageNavigator button strip inside the top navy bar."""
    return VisualSpec(
        page_name=page_name,
        visual_id="v00_page_nav",
        visual_type="pageNavigator",
        title="",
        subtitle="",
        x=640,
        y=8,
        width=624,
        height=52,
        z=1,
        query_state=None,
        objects={
            "layout": [
                {
                    "properties": {
                        "orientation": _lit("2D"),
                        "cellPadding": _lit("6L"),
                    }
                }
            ],
            "shape": [
                {
                    "selector": {"id": "default"},
                    "properties": {
                        "tileShape": _lit("'rectangleRounded'"),
                        "rectangleRoundedCurve": _lit("18L"),
                    },
                }
            ],
            "pages": [
                {
                    "properties": {
                        "showHiddenPages": _lit("false"),
                        "showTooltipPages": _lit("false"),
                    }
                }
            ],
            "fill": [
                {
                    "selector": {"id": "default"},
                    "properties": {
                        "show": _lit("true"),
                        "fillColor": _solid_color(PALETTE_NAVY_IDLE),
                        "transparency": _lit("0D"),
                    },
                },
                {
                    "selector": {"id": "hover"},
                    "properties": {
                        "show": _lit("true"),
                        "fillColor": _solid_color(PALETTE_NAV_HOVER),
                        "transparency": _lit("0D"),
                    },
                },
                {
                    "selector": {"id": "press"},
                    "properties": {
                        "show": _lit("true"),
                        "fillColor": _solid_color(PALETTE_NAV_ACTIVE),
                        "transparency": _lit("0D"),
                    },
                },
                {
                    "selector": {"id": "selected"},
                    "properties": {
                        "show": _lit("true"),
                        "fillColor": _solid_color(PALETTE_NAV_ACTIVE),
                        "transparency": _lit("0D"),
                    },
                },
            ],
            "text": [
                {
                    "selector": {"id": "default"},
                    "properties": {
                        "show": _lit("true"),
                        "fontColor": _solid_color("#E2E8F0"),
                        "fontSize": _lit("8.5D"),
                        "bold": _lit("true"),
                        "fontFamily": _lit("'Segoe UI Semibold'"),
                    },
                },
                {
                    "selector": {"id": "selected"},
                    "properties": {
                        "show": _lit("true"),
                        "fontColor": _solid_color("#FFFFFF"),
                        "fontSize": _lit("8.5D"),
                        "bold": _lit("true"),
                        "fontFamily": _lit("'Segoe UI Semibold'"),
                    },
                },
            ],
            "outline": [
                {
                    "selector": {"id": "default"},
                    "properties": {
                        "show": _lit("true"),
                        "lineColor": _solid_color("#334155"),
                        "weight": _lit("1D"),
                        "transparency": _lit("0D"),
                    },
                },
                {
                    "selector": {"id": "selected"},
                    "properties": {
                        "show": _lit("true"),
                        "lineColor": _solid_color("#38BDF8"),
                        "weight": _lit("1D"),
                        "transparency": _lit("0D"),
                    },
                },
            ],
        },
        border_color=PALETTE_NAVY,
        is_page_nav=True,
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
    filter_config: dict[str, Any] | None = None,
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
                        "fontSize": _lit("18D"),
                        "color": _solid_color(PALETTE_NAVY),
                        "labelDisplayUnits": _lit("1D"),
                    }
                }
            ],
            "categoryLabels": [{"properties": {"show": _lit("false")}}],
        },
        filter_config=filter_config,
        border_color=accent,
    )


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
            "callout": {"fontSize": 18, "fontFace": "Segoe UI Bold", "color": PALETTE_NAVY},
            "title": {"fontSize": 10, "fontFace": "Segoe UI Semibold", "color": PALETTE_NAVY},
            "header": {"fontSize": 9, "fontFace": "Segoe UI Semibold", "color": PALETTE_NAVY},
            "label": {"fontSize": 8, "fontFace": "Segoe UI", "color": "#334155"},
        },
        "visualStyles": {
            "tableEx": {
                "*": {
                    "grid": [{"rowPadding": 1}],
                    "columnHeaders": [
                        {
                            "backColor": {"solid": {"color": PALETTE_NAVY}},
                            "fontColor": {"solid": {"color": "#FFFFFF"}},
                            "bold": True,
                            "fontSize": 8,
                        }
                    ],
                    "values": [
                        {
                            "backColorPrimary": {"solid": {"color": "#FFFFFF"}},
                            "backColorSecondary": {"solid": {"color": "#F8FAFC"}},
                            "fontColorPrimary": {"solid": {"color": "#0F172A"}},
                            "fontColorSecondary": {"solid": {"color": "#0F172A"}},
                            "fontSize": 8,
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
    """Return all 46 non-overlapping styled PBIR visual specifications across the 4 pages."""
    p1, _, p1_sub = PAGE_METADATA[0]
    p2, _, p2_sub = PAGE_METADATA[1]
    p3, _, p3_sub = PAGE_METADATA[2]
    p4, _, p4_sub = PAGE_METADATA[3]

    return (
        # Page 1: Executive Pulse (banner + nav + 14 visuals = 16)
        _banner_spec(p1, p1_sub),
        _page_nav_spec(p1),
        _slicer_spec(p1, "v01_slicer_year", "Year", "2007 to 2026", 16, 64, 236, 54, 2, "dim_date", "year"),
        _slicer_spec(
            p1,
            "v02_slicer_group",
            "County Group",
            "ASAL vs Agri/Urban",
            262,
            64,
            246,
            54,
            3,
            "dim_markets",
            "county_group",
        ),
        _slicer_spec(
            p1,
            "v03_slicer_commodity",
            "Commodity",
            "3 tracked staples",
            518,
            64,
            246,
            54,
            4,
            "dim_commodity",
            "commodity_name",
        ),
        _slicer_spec(
            p1,
            "v04_slicer_season",
            "Cropping Season",
            "4 rainfall regimes",
            774,
            64,
            246,
            54,
            5,
            "dim_date",
            "season",
        ),
        _slicer_spec(
            p1,
            "v05_slicer_region",
            "Region",
            "7 Kenya regions",
            1030,
            64,
            234,
            54,
            6,
            "dim_markets",
            "adm1_name",
        ),
        _card_spec(
            p1,
            "v06_card_fpi",
            "Recent 12m Food Price Index",
            "Latest 12m (19y mean: 1.20)",
            16,
            124,
            240,
            74,
            7,
            "National Food Price Index",
            PALETTE_BLUE,
            filter_config=_bool_filter("f_v06_recent", "dim_date", "is_recent", True),
        ),
        _card_spec(
            p1,
            "v07_card_yoy",
            "Recent 12m YoY Inflation %",
            "Nov 2025 to Oct 2026 vs prior",
            268,
            124,
            240,
            74,
            8,
            "YoY Inflation %",
            PALETTE_ORANGE,
            filter_config=_bool_filter("f_v07_recent", "dim_date", "is_recent", True),
        ),
        _card_spec(
            p1,
            "v08_card_ytd",
            "2026 YTD Cumulative Index",
            "Jan to Oct 2026 running mean",
            520,
            124,
            240,
            74,
            9,
            "Cumulative Index YTD",
            PALETTE_TEAL,
        ),
        _card_spec(
            p1,
            "v09_card_completeness",
            "Data Completeness %",
            "166,362 rows across 233 mkts",
            772,
            124,
            240,
            74,
            10,
            "Data Completeness %",
            PALETTE_RED,
        ),
        _card_spec(
            p1,
            "v10_card_coverage",
            "Field Survey Coverage %",
            "Direct raw enumerator logs",
            1024,
            124,
            240,
            74,
            11,
            "Survey Coverage Rate %",
            PALETTE_SLATE,
        ),
        VisualSpec(
            page_name=p1,
            visual_id="v11_line_fpi_trend",
            visual_type="lineChart",
            title="National Food Price Index Trend (2007 to 2026)",
            subtitle="Grain-safe composite index across 238 months | 19-year baseline: 1.20",
            x=16,
            y=204,
            width=744,
            height=274,
            z=12,
            query_state={
                "Category": {"projections": [col_proj("dim_date", "full_date", active=True)]},
                "Y": {
                    "projections": [
                        meas_proj("fact_prices", "National Food Price Index"),
                    ]
                },
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "Cumulative Index YTD"),
                        meas_proj("fact_prices", "YoY Inflation %"),
                    ]
                },
            },
            objects=_clean_chart_objects(hide_legend=True),
        ),
        VisualSpec(
            page_name=p1,
            visual_id="v12_bar_top_counties",
            visual_type="barChart",
            title="Top 10 Counties by Recent 12m YoY Inflation %",
            subtitle="Nov 2025 to Oct 2026 | Teal: Agri/Urban, Orange: ASAL",
            x=772,
            y=204,
            width=492,
            height=274,
            z=13,
            query_state={
                "Category": {
                    "projections": [col_proj("dim_markets", "adm2_name", active=True, display_name="County")]
                },
                "Series": {
                    "projections": [col_proj("dim_markets", "county_group", active=True, display_name="Group")]
                },
                "Y": {"projections": [meas_proj("fact_prices", "YoY Inflation %", display_name="12m YoY %")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "National Food Price Index"),
                        meas_proj("fact_prices", "County Inflation Rank"),
                    ]
                },
            },
            sort=SortSpec("fact_prices", "YoY Inflation %", "Descending"),
            objects=_clean_chart_objects(
                data_labels=True,
                hide_legend=True,
                hide_y_title=True,
                category_font_size="8",
            ),
            filter_config=_combine_filters(
                _bool_filter("f_v12_recent", "dim_date", "is_recent", True),
                _categorical_in_filter("f_v12_top10", "dim_markets", "adm2_name", TOP10_RECENT_COUNTIES),
            ),
        ),
        VisualSpec(
            page_name=p1,
            visual_id="v13_table_commodities",
            visual_type="tableEx",
            title="Commodity Price, Recent 12m YoY & Volatility Matrix",
            subtitle="Latest 12m (Nov 2025 to Oct 2026): Maize eased -10.51% while Goats rose +7.77%",
            x=16,
            y=486,
            width=744,
            height=224,
            z=14,
            query_state={
                "Values": {
                    "projections": [
                        col_proj("dim_commodity", "commodity_name", display_name="Commodity"),
                        col_proj("dim_commodity", "unit", display_name="Unit"),
                        meas_proj("fact_prices", "Avg Price (KES)", display_name="12m Avg (KES)"),
                        meas_proj("fact_prices", "Prior Year Price (KES)", display_name="Prior 12m (KES)"),
                        meas_proj("fact_prices", "Commodity YoY Inflation %", display_name="12m YoY %"),
                        meas_proj("fact_prices", "Price Volatility CV %", display_name="12m CV %"),
                    ]
                }
            },
            objects=_clean_table_objects(),
            filter_config=_bool_filter("f_v13_recent", "dim_date", "is_recent", True),
        ),
        VisualSpec(
            page_name=p1,
            visual_id="v14_table_county_alerts",
            visual_type="tableEx",
            title="Top 10 County Inflation Watchlist (Recent 12m)",
            subtitle="Dense rank across covered Kenyan counties (Nov 2025 to Oct 2026)",
            x=772,
            y=486,
            width=492,
            height=224,
            z=15,
            query_state={
                "Values": {
                    "projections": [
                        meas_proj("fact_prices", "County Inflation Rank", display_name="Rank"),
                        col_proj("dim_markets", "adm2_name", display_name="County"),
                        meas_proj("fact_prices", "National Food Price Index", display_name="Index"),
                        meas_proj("fact_prices", "YoY Inflation %", display_name="12m YoY %"),
                    ]
                }
            },
            sort=SortSpec("fact_prices", "YoY Inflation %", "Descending"),
            objects=_clean_table_objects(),
            filter_config=_combine_filters(
                _bool_filter("f_v14_recent", "dim_date", "is_recent", True),
                _categorical_in_filter("f_v14_top10", "dim_markets", "adm2_name", TOP10_RECENT_COUNTIES),
            ),
        ),
        # Page 2: County and Commodity (banner + nav + 8 visuals = 10)
        _banner_spec(p2, p2_sub),
        _page_nav_spec(p2),
        _slicer_spec(
            p2,
            "v21_slicer_commodity",
            "Commodity",
            "3 tracked staples",
            16,
            64,
            300,
            54,
            2,
            "dim_commodity",
            "commodity_name",
        ),
        _slicer_spec(
            p2,
            "v22_slicer_group",
            "County Group",
            "ASAL vs Agri/Urban",
            328,
            64,
            300,
            54,
            3,
            "dim_markets",
            "county_group",
        ),
        _slicer_spec(
            p2,
            "v23_slicer_region",
            "Region",
            "7 Kenya regions",
            640,
            64,
            300,
            54,
            4,
            "dim_markets",
            "adm1_name",
        ),
        _slicer_spec(
            p2,
            "v24_slicer_year",
            "Year",
            "2007 to 2026",
            952,
            64,
            312,
            54,
            5,
            "dim_date",
            "year",
        ),
        VisualSpec(
            page_name=p2,
            visual_id="v25_bar_affordability_gap",
            visual_type="barChart",
            title="Maize Affordability Gap: Top 5 Deficit vs Bottom 5 Surplus",
            subtitle="KES/kg vs national mean (56.02) | Teal: Agri/Urban, Orange: ASAL",
            x=16,
            y=124,
            width=618,
            height=298,
            z=6,
            query_state={
                "Category": {
                    "projections": [col_proj("dim_markets", "adm2_name", active=True, display_name="County")]
                },
                "Series": {
                    "projections": [col_proj("dim_markets", "county_group", active=True, display_name="Group")]
                },
                "Y": {
                    "projections": [meas_proj("fact_prices", "Affordability Gap (KES)", display_name="Gap (KES)")]
                },
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "Avg Price (KES)"),
                        meas_proj("fact_prices", "Prior Year Price (KES)"),
                    ]
                },
            },
            sort=SortSpec("fact_prices", "Affordability Gap (KES)", "Descending"),
            objects=_clean_chart_objects(
                data_labels=True,
                hide_legend=True,
                hide_y_title=True,
                category_font_size="8",
            ),
            filter_config=_combine_filters(
                _categorical_in_filter("f_v25_maize", "dim_commodity", "commodity_id", ("maize_fao",)),
                _categorical_in_filter("f_v25_div", "dim_markets", "adm2_name", DIVERGING_MAIZE_COUNTIES),
            ),
        ),
        VisualSpec(
            page_name=p2,
            visual_id="v26_scatter_county_risk",
            visual_type="scatterChart",
            title="Geographic Distribution of 233 Physical Kenyan Markets",
            subtitle="Plotted from verified coordinates | Teal: 31 Agri/Urban, Orange: 202 ASAL",
            x=646,
            y=124,
            width=618,
            height=298,
            z=7,
            query_state={
                "Category": {
                    "projections": [col_proj("dim_markets", "mkt_name", active=True, display_name="Market")]
                },
                "Series": {
                    "projections": [col_proj("dim_markets", "county_group", active=True, display_name="Group")]
                },
                "X": {"projections": [agg_proj("dim_markets", "lon", func=1, display_name="Longitude (E)")]},
                "Y": {"projections": [agg_proj("dim_markets", "lat", func=1, display_name="Latitude (N)")]},
                "Tooltips": {
                    "projections": [
                        col_proj("dim_markets", "adm2_name", display_name="County"),
                        meas_proj("fact_prices", "Affordability Gap (KES)", display_name="Gap (KES)"),
                        meas_proj("fact_prices", "Price Volatility CV %", display_name="CV %"),
                    ]
                },
            },
            objects=_scatter_objects(bubble_size="-22D"),
        ),
        VisualSpec(
            page_name=p2,
            visual_id="v27_col_group_comparison",
            visual_type="clusteredColumnChart",
            title="Price Volatility Comparison (CV %): ASAL vs Agri & Urban",
            subtitle="Coefficient of variation across Beans, Goat, and Maize",
            x=16,
            y=430,
            width=516,
            height=280,
            z=8,
            query_state={
                "Category": {
                    "projections": [
                        col_proj("dim_commodity", "commodity_name", active=True, display_name="Commodity")
                    ]
                },
                "Series": {
                    "projections": [col_proj("dim_markets", "county_group", active=True, display_name="Group")]
                },
                "Y": {
                    "projections": [meas_proj("fact_prices", "Price Volatility CV %", display_name="CV %")]
                },
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "Avg Price (KES)"),
                        meas_proj("fact_prices", "Affordability Gap (KES)"),
                    ]
                },
            },
            objects=_clean_chart_objects(data_labels=True),
        ),
        VisualSpec(
            page_name=p2,
            visual_id="v28_table_county_drill",
            visual_type="tableEx",
            title="County Maize Affordability, Volatility & Survey Breakdown",
            subtitle="Filtered to Maize (1 kg) | Sorted by Affordability Gap descending",
            x=544,
            y=430,
            width=720,
            height=280,
            z=9,
            query_state={
                "Values": {
                    "projections": [
                        col_proj("dim_markets", "adm2_name", display_name="County"),
                        col_proj("dim_markets", "county_group", display_name="Group"),
                        meas_proj("fact_prices", "Avg Price (KES)", display_name="Avg (KES/kg)"),
                        meas_proj("fact_prices", "Affordability Gap (KES)", display_name="Gap (KES)"),
                        meas_proj("fact_prices", "Price Volatility CV %", display_name="CV %"),
                        meas_proj("fact_prices", "Survey Coverage Rate %", display_name="Survey %"),
                    ]
                }
            },
            sort=SortSpec("fact_prices", "Affordability Gap (KES)", "Descending"),
            objects=_clean_table_objects(),
            filter_config=_categorical_in_filter("f_v28_maize", "dim_commodity", "commodity_id", ("maize_fao",)),
        ),
        # Page 3: Trends and Diagnostics (banner + nav + 8 visuals = 10)
        _banner_spec(p3, p3_sub),
        _page_nav_spec(p3),
        _slicer_spec(
            p3,
            "v31_slicer_commodity",
            "Commodity",
            "3 tracked staples",
            16,
            64,
            300,
            54,
            2,
            "dim_commodity",
            "commodity_name",
        ),
        _slicer_spec(
            p3,
            "v32_slicer_group",
            "County Group",
            "ASAL vs Agri/Urban",
            328,
            64,
            300,
            54,
            3,
            "dim_markets",
            "county_group",
        ),
        _slicer_spec(
            p3,
            "v33_slicer_region",
            "Region",
            "7 Kenya regions",
            640,
            64,
            300,
            54,
            4,
            "dim_markets",
            "adm1_name",
        ),
        _slicer_spec(
            p3,
            "v34_slicer_season",
            "Cropping Season",
            "4 rainfall regimes",
            952,
            64,
            312,
            54,
            5,
            "dim_date",
            "season",
        ),
        VisualSpec(
            page_name=p3,
            visual_id="v36_line_rolling_price",
            visual_type="lineChart",
            title="Beans & Maize Retail Prices (KES/kg, 2007 to 2026)",
            subtitle="Filtered to 1 kg staples | Hover for 12m Rolling Avg, MoM % & StdDev",
            x=16,
            y=124,
            width=732,
            height=292,
            z=6,
            query_state={
                "Category": {"projections": [col_proj("dim_date", "full_date", active=True)]},
                "Series": {
                    "projections": [
                        col_proj("dim_commodity", "commodity_name", active=True, display_name="Commodity")
                    ]
                },
                "Y": {"projections": [meas_proj("fact_prices", "Avg Price (KES)")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "12-Month Rolling Avg (KES)"),
                        meas_proj("fact_prices", "MoM Change %"),
                        meas_proj("fact_prices", "Price Volatility (KES)"),
                    ]
                },
            },
            objects=_clean_chart_objects(),
            filter_config=_categorical_in_filter(
                "f_v36_staples", "dim_commodity", "commodity_id", ("beans", "maize_fao")
            ),
        ),
        VisualSpec(
            page_name=p3,
            visual_id="v37_line_seasonality",
            visual_type="lineChart",
            title="Monthly Seasonal Index Cycle (Jan to Dec, Parity = 1.000)",
            subtitle="Crop staples peak Jun-Sep; live goats peak Dec-Feb",
            x=760,
            y=124,
            width=504,
            height=292,
            z=7,
            query_state={
                "Category": {"projections": [col_proj("dim_date", "month_name", active=True)]},
                "Series": {
                    "projections": [
                        col_proj("dim_commodity", "commodity_name", active=True, display_name="Commodity")
                    ]
                },
                "Y": {"projections": [meas_proj("fact_prices", "Seasonal Index")]},
            },
            objects=_clean_chart_objects(),
        ),
        VisualSpec(
            page_name=p3,
            visual_id="v38_bar_volatility",
            visual_type="barChart",
            title="Top 10 Counties by Maize Price Volatility (CV %)",
            subtitle="Filtered to Maize (1 kg) | Teal: Agri/Urban, Orange: ASAL",
            x=16,
            y=424,
            width=618,
            height=286,
            z=8,
            query_state={
                "Category": {
                    "projections": [col_proj("dim_markets", "adm2_name", active=True, display_name="County")]
                },
                "Series": {
                    "projections": [col_proj("dim_markets", "county_group", active=True, display_name="Group")]
                },
                "Y": {
                    "projections": [meas_proj("fact_prices", "Price Volatility CV %", display_name="CV %")]
                },
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "Price Volatility (KES)"),
                        meas_proj("fact_prices", "Commodity YoY Inflation %"),
                    ]
                },
            },
            sort=SortSpec("fact_prices", "Price Volatility CV %", "Descending"),
            objects=_clean_chart_objects(
                data_labels=True,
                hide_legend=True,
                hide_y_title=True,
                category_font_size="8",
            ),
            filter_config=_combine_filters(
                _categorical_in_filter("f_v38_maize_cv", "dim_commodity", "commodity_id", ("maize_fao",)),
                _categorical_in_filter("f_v38_top10_cv", "dim_markets", "adm2_name", TOP10_MAIZE_CV_COUNTIES),
            ),
        ),
        VisualSpec(
            page_name=p3,
            visual_id="v39_col_season_window",
            visual_type="clusteredColumnChart",
            title="Seasonal Index by Kenyan Cropping Window & Commodity",
            subtitle="Includes gap-safe EDATE MoM % and Avg Price tooltips",
            x=646,
            y=424,
            width=618,
            height=286,
            z=9,
            query_state={
                "Category": {"projections": [col_proj("dim_date", "season", active=True)]},
                "Series": {
                    "projections": [
                        col_proj("dim_commodity", "commodity_name", active=True, display_name="Commodity")
                    ]
                },
                "Y": {"projections": [meas_proj("fact_prices", "Seasonal Index")]},
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "Avg Price (KES)"),
                        meas_proj("fact_prices", "MoM Change %"),
                        meas_proj("fact_prices", "Price Volatility (KES)"),
                    ]
                },
            },
            objects=_clean_chart_objects(data_labels=True),
        ),
        # Page 4: Decisions and Action (banner + nav + 8 visuals = 10)
        _banner_spec(p4, p4_sub),
        _page_nav_spec(p4),
        _slicer_spec(
            p4,
            "v41_slicer_group",
            "County Group",
            "ASAL vs Agri/Urban",
            16,
            64,
            300,
            54,
            2,
            "dim_markets",
            "county_group",
        ),
        _slicer_spec(
            p4,
            "v42_slicer_region",
            "Region",
            "7 Kenya regions",
            328,
            64,
            300,
            54,
            3,
            "dim_markets",
            "adm1_name",
        ),
        _slicer_spec(
            p4,
            "v43_slicer_commodity",
            "Commodity",
            "3 tracked staples",
            640,
            64,
            300,
            54,
            4,
            "dim_commodity",
            "commodity_name",
        ),
        _slicer_spec(
            p4,
            "v44_slicer_year",
            "Year",
            "2007 to 2026",
            952,
            64,
            312,
            54,
            5,
            "dim_date",
            "year",
        ),
        VisualSpec(
            page_name=p4,
            visual_id="v46_scatter_coverage_risk",
            visual_type="scatterChart",
            title="Monitoring Priority Quadrant: Survey % vs Maize CV %",
            subtitle="Filtered to Maize (1 kg) | Top-left flags urgent enumerator blind spots",
            x=16,
            y=124,
            width=574,
            height=292,
            z=6,
            query_state={
                "Category": {
                    "projections": [col_proj("dim_markets", "adm2_name", active=True, display_name="County")]
                },
                "Series": {
                    "projections": [col_proj("dim_markets", "county_group", active=True, display_name="Group")]
                },
                "X": {
                    "projections": [meas_proj("fact_prices", "Survey Coverage Rate %", display_name="Survey %")]
                },
                "Y": {
                    "projections": [meas_proj("fact_prices", "Price Volatility CV %", display_name="Maize CV %")]
                },
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "YoY Inflation %"),
                        meas_proj("fact_prices", "Affordability Gap (KES)"),
                        meas_proj("fact_prices", "Data Completeness %"),
                    ]
                },
            },
            objects=_scatter_objects(bubble_size="-14D"),
            filter_config=_categorical_in_filter(
                "f_v46_maize_quad", "dim_commodity", "commodity_id", ("maize_fao",)
            ),
        ),
        VisualSpec(
            page_name=p4,
            visual_id="v47_table_priority_action",
            visual_type="tableEx",
            title="County Priority Action Matrix: Survey Rate, CV & Maize Gap",
            subtitle="Filtered to Maize (1 kg) | Sorted by Affordability Gap descending",
            x=602,
            y=124,
            width=662,
            height=292,
            z=7,
            query_state={
                "Values": {
                    "projections": [
                        col_proj("dim_markets", "adm2_name", display_name="County"),
                        col_proj("dim_markets", "county_group", display_name="Group"),
                        meas_proj("fact_prices", "Survey Coverage Rate %", display_name="Survey %"),
                        meas_proj("fact_prices", "Price Volatility CV %", display_name="Maize CV %"),
                        meas_proj("fact_prices", "Affordability Gap (KES)", display_name="Gap (KES)"),
                        meas_proj("fact_prices", "Avg Price (KES)", display_name="Avg (KES)"),
                    ]
                }
            },
            sort=SortSpec("fact_prices", "Affordability Gap (KES)", "Descending"),
            objects=_clean_table_objects(),
            filter_config=_categorical_in_filter(
                "f_v47_maize_tbl", "dim_commodity", "commodity_id", ("maize_fao",)
            ),
        ),
        VisualSpec(
            page_name=p4,
            visual_id="v48_bar_coverage_gap",
            visual_type="barChart",
            title="10 Low-Survey Counties Under 5% (Sentinel Expansion)",
            subtitle="Teal: Agri/Urban, Orange: ASAL | Plus 7 zero-survey counties (0.00%)",
            x=16,
            y=424,
            width=574,
            height=286,
            z=8,
            query_state={
                "Category": {
                    "projections": [col_proj("dim_markets", "adm2_name", active=True, display_name="County")]
                },
                "Series": {
                    "projections": [col_proj("dim_markets", "county_group", active=True, display_name="Group")]
                },
                "Y": {
                    "projections": [meas_proj("fact_prices", "Survey Coverage Rate %", display_name="Survey %")]
                },
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "Data Completeness %"),
                        meas_proj("fact_prices", "Price Volatility CV %"),
                    ]
                },
            },
            sort=SortSpec("fact_prices", "Survey Coverage Rate %", "Ascending"),
            objects=_clean_chart_objects(
                data_labels=True,
                hide_legend=True,
                hide_y_title=True,
                category_font_size="8",
            ),
            filter_config=_categorical_in_filter(
                "f_v48_low_survey", "dim_markets", "adm2_name", LOW_SURVEY_COUNTIES
            ),
        ),
        VisualSpec(
            page_name=p4,
            visual_id="v49_col_basket_by_region",
            visual_type="clusteredColumnChart",
            title="Average Maize Price (KES/kg) by Region & County Group",
            subtitle="Filtered to Maize (1 kg) | Unit-safe comparison across 7 regions",
            x=602,
            y=424,
            width=662,
            height=286,
            z=9,
            query_state={
                "Category": {
                    "projections": [col_proj("dim_markets", "adm1_name", active=True, display_name="Region")]
                },
                "Series": {
                    "projections": [col_proj("dim_markets", "county_group", active=True, display_name="Group")]
                },
                "Y": {
                    "projections": [meas_proj("fact_prices", "Avg Price (KES)", display_name="Avg Maize (KES/kg)")]
                },
                "Tooltips": {
                    "projections": [
                        meas_proj("fact_prices", "YoY Inflation %"),
                        meas_proj("fact_prices", "National Food Price Index"),
                    ]
                },
            },
            objects=_clean_chart_objects(data_labels=True),
            filter_config=_categorical_in_filter(
                "f_v49_maize_reg", "dim_commodity", "commodity_id", ("maize_fao",)
            ),
        ),
    )


def _container_objects(spec: VisualSpec) -> dict[str, Any]:
    """Build executive visualContainerObjects styling for cards, charts, slicers, and nav."""
    if spec.is_page_nav:
        return {
            "background": [
                {
                    "properties": {
                        "show": _lit("true"),
                        "color": _solid_color(PALETTE_NAVY),
                        "transparency": _lit("0D"),
                    }
                }
            ],
            "border": [
                {
                    "properties": {
                        "show": _lit("true"),
                        "color": _solid_color(PALETTE_NAVY),
                        "radius": _lit("0D"),
                        "width": _lit("1D"),
                    }
                }
            ],
            "dropShadow": [{"properties": {"show": _lit("false")}}],
            "title": [{"properties": {"show": _lit("false")}}],
            "subTitle": [{"properties": {"show": _lit("false")}}],
            "divider": [{"properties": {"show": _lit("false")}}],
            "visualHeader": [{"properties": {"show": _lit("false")}}],
            "padding": [
                {
                    "properties": {
                        "top": _lit("8D"),
                        "bottom": _lit("8D"),
                        "left": _lit("6D"),
                        "right": _lit("10D"),
                    }
                }
            ],
        }

    escaped_title = spec.title.replace("'", "''")
    escaped_sub = spec.subtitle.replace("'", "''")

    if spec.is_banner:
        return {
            "background": [
                {
                    "properties": {
                        "show": _lit("true"),
                        "color": _solid_color(PALETTE_NAVY),
                        "transparency": _lit("0D"),
                    }
                }
            ],
            "border": [
                {
                    "properties": {
                        "show": _lit("true"),
                        "color": _solid_color(PALETTE_NAVY),
                        "radius": _lit("0D"),
                        "width": _lit("1D"),
                    }
                }
            ],
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
                        "fontColor": _solid_color("#BAE6FD"),
                        "fontSize": _lit("8.5D"),
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
                        "top": _lit("4D"),
                        "bottom": _lit("4D"),
                        "left": _lit("12D"),
                        "right": _lit("6D"),
                    }
                }
            ],
        }

    is_slicer = spec.visual_type == "slicer"
    return {
        "background": [
            {
                "properties": {
                    "show": _lit("true"),
                    "color": _solid_color("#FFFFFF"),
                    "transparency": _lit("0D"),
                }
            }
        ],
        "border": [
            {
                "properties": {
                    "show": _lit("true"),
                    "color": _solid_color(spec.border_color),
                    "radius": _lit("8D"),
                    "width": _lit("1D"),
                }
            }
        ],
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
                    "fontSize": _lit("8.5D" if is_slicer else "10D"),
                    "bold": _lit("true"),
                    "fontFamily": _lit("'Segoe UI Semibold'"),
                    "titleWrap": _lit("false" if is_slicer else "true"),
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
                    "titleWrap": _lit("false" if is_slicer else "true"),
                }
            }
        ],
        "divider": [
            {
                "properties": {
                    "show": _lit("false" if is_slicer else "true"),
                    "color": _solid_color(PALETTE_DIVIDER),
                    "width": _lit("1D"),
                }
            }
        ],
        "padding": [
            {
                "properties": {
                    "top": _lit("2D" if is_slicer else "5D"),
                    "bottom": _lit("2D" if is_slicer else "5D"),
                    "left": _lit("6D"),
                    "right": _lit("6D"),
                }
            }
        ],
    }


def spec_to_visual_payload(spec: VisualSpec) -> dict[str, Any]:
    """Convert a VisualSpec into a schema-valid visual.json dictionary."""
    visual_obj: dict[str, Any] = {
        "visualType": spec.visual_type,
        "visualContainerObjects": _container_objects(spec),
    }
    if spec.query_state is not None:
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
        visual_obj["query"] = query

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
    """Write theme, report.json, styled page.json files, and all 46 visual.json files."""
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
    """CLI entrypoint to generate custom theme, page styling, and 46 PBIR visuals."""
    written = generate_pbir_visuals()
    total = sum(len(paths) for paths in written.values())
    for page, paths in written.items():
        print(f"{page}: wrote {len(paths)} visuals")
    print(f"Total PBIR visuals written: {total}")


if __name__ == "__main__":
    main()
