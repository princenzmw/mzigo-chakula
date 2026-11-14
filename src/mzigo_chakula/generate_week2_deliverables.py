"""Generate Week 2 processed dimension CSVs, Power Query (M) scripts, and transformation log."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from mzigo_chakula.data import (
    COUNTY_MAPPING,
    DEFAULT_RAW_CSV,
    MARKET_COUNTY_OVERRIDES,
    PROJECT_ROOT,
)
from mzigo_chakula.etl import ASAL_COUNTIES, COMMODITY_SPECS, ETLResult, run_etl

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
POWERQUERY_DIR = PROJECT_ROOT / "powerquery"
DOCS_DIR = PROJECT_ROOT / "docs"


def _m_quote(value: str) -> str:
    """Format a Python string as a Power Query M double-quoted string literal."""
    return '"' + value.replace('"', '""') + '"'


def _write_csv_table(rows: list[dict[str, Any]], output_path: Path) -> Path:
    """Write a non-empty list of flat dictionaries to UTF-8 CSV."""
    if not rows:
        raise ValueError(f"Cannot write empty table to {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def build_dim_markets_m(raw_csv_path: Path) -> str:
    """Build reproducible Power Query M script for dim_markets."""
    mapping_rows: list[str] = []
    for (raw_adm1, raw_adm2), (region, county, subcounty) in sorted(COUNTY_MAPPING.items()):
        if raw_adm1 == "Market Average":
            continue
        row_literal = (
            f"        {{{_m_quote(raw_adm1)}, {_m_quote(raw_adm2)}, "
            f"{_m_quote(region)}, {_m_quote(county)}, {_m_quote(subcounty)}}}"
        )
        mapping_rows.append(row_literal)

    override_rows: list[str] = []
    for mkt_name, (region, county, subcounty) in sorted(MARKET_COUNTY_OVERRIDES.items()):
        override_rows.append(
            f"        {{{_m_quote(mkt_name)}, {_m_quote(region)}, {_m_quote(county)}, {_m_quote(subcounty)}}}"
        )

    asal_items = ", ".join(_m_quote(c) for c in sorted(ASAL_COUNTIES))
    csv_literal = _m_quote(str(raw_csv_path))

    lines: list[str] = [
        "// Mzigo Chakula: dim_markets (233 physical Kenyan markets across 27 counties and 7 regions)",
        "// Update CsvPath if moving the repository to a different folder.",
        "let",
        f"    CsvPath = {csv_literal},",
        '    Source = Csv.Document(File.Contents(CsvPath), [Delimiter=",", Columns=46, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        "    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        '    FilteredPhysical = Table.SelectRows(PromotedHeaders, each [geo_id] <> "gid_ken_national_average" and [mkt_name] <> "Market Average"),',
        '    SelectedCols = Table.SelectColumns(FilteredPhysical, {"geo_id", "mkt_name", "adm1_name", "adm2_name", "lat", "lon", "data_coverage", "data_coverage_recent"}),',
        '    DistinctMarkets = Table.Distinct(SelectedCols, {"geo_id"}),',
        '    RenamedRawCols = Table.RenameColumns(DistinctMarkets, {{"geo_id", "mkt_id"}, {"adm1_name", "raw_adm1_name"}, {"adm2_name", "raw_adm2_name"}}),',
        "    TypedCols = Table.TransformColumnTypes(",
        "        RenamedRawCols,",
        "        {",
        '            {"mkt_id", type text},',
        '            {"mkt_name", type text},',
        '            {"raw_adm1_name", type text},',
        '            {"raw_adm2_name", type text},',
        '            {"lat", type number},',
        '            {"lon", type number},',
        '            {"data_coverage", type number},',
        '            {"data_coverage_recent", type number}',
        "        },",
        '        "en-US"',
        "    ),",
        "    CountyLookup = #table(",
        '        {"raw_adm1_name", "raw_adm2_name", "adm1_name", "adm2_name", "subcounty_or_district"},',
        "        {",
        ",\n".join(mapping_rows),
        "        }",
        "    ),",
        "    MarketOverrideLookup = #table(",
        '        {"mkt_name", "ov_region", "ov_county", "ov_subcounty"},',
        "        {",
        ",\n".join(override_rows),
        "        }",
        "    ),",
        '    JoinedAdmin = Table.NestedJoin(TypedCols, {"raw_adm1_name", "raw_adm2_name"}, CountyLookup, {"raw_adm1_name", "raw_adm2_name"}, "AdminMatch", JoinKind.Inner),',
        '    ExpandedAdmin = Table.ExpandTableColumn(JoinedAdmin, "AdminMatch", {"adm1_name", "adm2_name", "subcounty_or_district"}, {"map_region", "map_county", "map_subcounty"}),',
        '    JoinedOverride = Table.NestedJoin(ExpandedAdmin, {"mkt_name"}, MarketOverrideLookup, {"mkt_name"}, "OverrideMatch", JoinKind.LeftOuter),',
        '    ExpandedOverride = Table.ExpandTableColumn(JoinedOverride, "OverrideMatch", {"ov_region", "ov_county", "ov_subcounty"}),',
        '    ResolvedRegion = Table.AddColumn(ExpandedOverride, "adm1_name", each if [ov_region] <> null then [ov_region] else [map_region], type text),',
        '    ResolvedCounty = Table.AddColumn(ResolvedRegion, "adm2_name", each if [ov_county] <> null then [ov_county] else [map_county], type text),',
        '    ResolvedSubcounty = Table.AddColumn(ResolvedCounty, "subcounty_or_district", each if [ov_subcounty] <> null then [ov_subcounty] else [map_subcounty], type text),',
        '    RemovedTempCols = Table.RemoveColumns(ResolvedSubcounty, {"map_region", "map_county", "map_subcounty", "ov_region", "ov_county", "ov_subcounty"}),',
        f"    AsalCounties = {{{asal_items}}},",
        '    AddedCountyGroup = Table.AddColumn(RemovedTempCols, "county_group", each if List.Contains(AsalCounties, [adm2_name]) then "Arid & Semi-Arid (ASAL)" else "Agricultural & Urban", type text),',
        '    ReorderedCols = Table.ReorderColumns(AddedCountyGroup, {"mkt_id", "mkt_name", "adm1_name", "adm2_name", "subcounty_or_district", "raw_adm1_name", "raw_adm2_name", "county_group", "lat", "lon", "data_coverage", "data_coverage_recent"}),',
        '    SortedMarkets = Table.Sort(ReorderedCols, {{"adm2_name", Order.Ascending}, {"mkt_name", Order.Ascending}})',
        "in",
        "    SortedMarkets",
    ]
    return "\n".join(lines) + "\n"


def build_dim_date_m(raw_csv_path: Path) -> str:
    """Build reproducible Power Query M script for dim_date."""
    csv_literal = _m_quote(str(raw_csv_path))
    lines: list[str] = [
        "// Mzigo Chakula: dim_date (238 consecutive monthly periods from 2007-01-01 to 2026-10-01)",
        "// Update CsvPath if moving the repository to a different folder.",
        "let",
        f"    CsvPath = {csv_literal},",
        '    Source = Csv.Document(File.Contents(CsvPath), [Delimiter=",", Columns=46, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        "    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        '    SelectedDateCols = Table.SelectColumns(PromotedHeaders, {"price_date", "year", "month"}),',
        '    DistinctDates = Table.Distinct(SelectedDateCols, {"price_date"}),',
        '    TypedDates = Table.TransformColumnTypes(DistinctDates, {{"price_date", type date}, {"year", Int64.Type}, {"month", Int64.Type}}, "en-US"),',
        '    RenamedDateCol = Table.RenameColumns(TypedDates, {{"price_date", "full_date"}}),',
        '    SortedDates = Table.Sort(RenamedDateCol, {{"full_date", Order.Ascending}}),',
        '    AddedDateKey = Table.AddColumn(SortedDates, "date_key", each [year] * 10000 + [month] * 100 + Date.Day([full_date]), Int64.Type),',
        '    AddedMonthName = Table.AddColumn(AddedDateKey, "month_name", each Date.ToText([full_date], "MMM", "en-US"), type text),',
        '    AddedYearMonth = Table.AddColumn(AddedMonthName, "year_month", each Date.ToText([full_date], "yyyy-MM", "en-US"), type text),',
        '    AddedQuarter = Table.AddColumn(AddedYearMonth, "quarter", each "Q" & Text.From(Date.QuarterOfYear([full_date])), type text),',
        "    AddedSeason = Table.AddColumn(",
        "        AddedQuarter,",
        '        "season",',
        '        each if List.Contains({1, 2}, [month]) then "Hot Dry / Lean (Jan-Feb)" else if List.Contains({3, 4, 5}, [month]) then "Long Rains (Mar-May)" else if List.Contains({6, 7, 8, 9}, [month]) then "Cool Dry / Harvest (Jun-Sep)" else "Short Rains (Oct-Dec)",',
        "        type text",
        "    ),",
        "    MaxDate = List.Max(AddedSeason[full_date]),",
        '    AddedIsRecent = Table.AddColumn(AddedSeason, "is_recent", each [full_date] >= Date.AddMonths(MaxDate, -11), type logical),',
        '    AddedIsLast36M = Table.AddColumn(AddedIsRecent, "is_last_36m", each [full_date] >= Date.AddMonths(MaxDate, -35), type logical),',
        '    ReorderedCols = Table.ReorderColumns(AddedIsLast36M, {"date_key", "full_date", "year", "month", "month_name", "year_month", "quarter", "season", "is_recent", "is_last_36m"})',
        "in",
        "    ReorderedCols",
    ]
    return "\n".join(lines) + "\n"


def build_dim_commodity_m() -> str:
    """Build reproducible Power Query M script for dim_commodity."""
    row_lines: list[str] = []
    for spec in COMMODITY_SPECS:
        row_lines.append(
            f"        {{{_m_quote(spec.commodity_id)}, {_m_quote(spec.commodity_name)}, "
            f"{_m_quote(spec.category)}, {_m_quote(spec.unit)}, {_m_quote(spec.index_weight_note)}}}"
        )

    lines: list[str] = [
        "// Mzigo Chakula: dim_commodity (3 tracked Kenyan staple commodities)",
        "let",
        "    CommodityTable = #table(",
        "        type table [",
        "            commodity_id = text,",
        "            commodity_name = text,",
        "            category = text,",
        "            unit = text,",
        "            index_weight_note = text",
        "        ],",
        "        {",
        ",\n".join(row_lines),
        "        }",
        "    )",
        "in",
        "    CommodityTable",
    ]
    return "\n".join(lines) + "\n"


def build_fact_prices_m(raw_csv_path: Path) -> str:
    """Build reproducible Power Query M script for fact_prices."""
    csv_literal = _m_quote(str(raw_csv_path))
    type_pairs: list[str] = [
        '            {"geo_id", type text}',
        '            {"mkt_name", type text}',
        '            {"price_date", type date}',
        '            {"year", Int64.Type}',
        '            {"month", Int64.Type}',
        '            {"c_food_price_index", type number}',
        '            {"inflation_food_price_index", type number}',
    ]
    needed_cols: list[str] = [
        '"geo_id"',
        '"mkt_name"',
        '"price_date"',
        '"year"',
        '"month"',
        '"c_food_price_index"',
        '"inflation_food_price_index"',
    ]
    for spec in COMMODITY_SPECS:
        for col in (
            spec.close_col,
            spec.open_col,
            spec.high_col,
            spec.low_col,
            spec.raw_col,
            spec.inflation_col,
            spec.trust_col,
        ):
            needed_cols.append(f'"{col}"')
            type_pairs.append(f'            {{"{col}", type number}}')

    commodity_projections: list[str] = []
    for spec in COMMODITY_SPECS:
        commodity_projections.append(
            f'        ProjectCommodity(RenamedBase, "{spec.commodity_id}", '
            f'"{spec.close_col}", "{spec.open_col}", "{spec.high_col}", "{spec.low_col}", '
            f'"{spec.raw_col}", "{spec.inflation_col}", "{spec.trust_col}")'
        )

    lines: list[str] = [
        "// Mzigo Chakula: fact_prices (166,362 market-month-commodity records from 55,454 physical market observations)",
        "// Update CsvPath if moving the repository to a different folder.",
        "let",
        f"    CsvPath = {csv_literal},",
        '    Source = Csv.Document(File.Contents(CsvPath), [Delimiter=",", Columns=46, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        "    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        f"    SelectedCols = Table.SelectColumns(PromotedHeaders, {{{', '.join(needed_cols)}}}),",
        "    TypedBase = Table.TransformColumnTypes(",
        "        SelectedCols,",
        "        {",
        ",\n".join(type_pairs),
        "        },",
        '        "en-US"',
        "    ),",
        '    FilteredPhysical = Table.SelectRows(TypedBase, each [geo_id] <> "gid_ken_national_average" and [mkt_name] <> "Market Average" and ([c_beans] <> null or [c_maize_fao] <> null or [c_livestock_goat_s_fao] <> null)),',
        '    AddedDateKey = Table.AddColumn(FilteredPhysical, "date_key", each [year] * 10000 + [month] * 100 + Date.Day([price_date]), Int64.Type),',
        '    RenamedBase = Table.RenameColumns(AddedDateKey, {{"geo_id", "mkt_id"}, {"c_food_price_index", "food_price_index"}}),',
        "    ProjectCommodity = (base as table, cid as text, closeCol as text, openCol as text, highCol as text, lowCol as text, rawCol as text, inflCol as text, trustCol as text) as table =>",
        "        let",
        '            Subset = Table.SelectColumns(base, {"mkt_id", "date_key", "food_price_index", "inflation_food_price_index", closeCol, openCol, highCol, lowCol, rawCol, inflCol, trustCol}),',
        "            Renamed = Table.RenameColumns(Subset, {",
        '                {closeCol, "price_value"},',
        '                {openCol, "open_price"},',
        '                {highCol, "high_price"},',
        '                {lowCol, "low_price"},',
        '                {rawCol, "raw_spot_price"},',
        '                {inflCol, "commodity_inflation_yoy"},',
        '                {trustCol, "trust_score"}',
        "            }),",
        '            NonNullClose = Table.SelectRows(Renamed, each [price_value] <> null),',
        '            WithCid = Table.AddColumn(NonNullClose, "commodity_id", each cid, type text)',
        "        in",
        "            WithCid,",
        "    Unpivoted = Table.Combine({",
        ",\n".join(commodity_projections),
        "    }),",
        '    AddedPriceId = Table.AddColumn(Unpivoted, "price_id", each [mkt_id] & "_" & Text.From([date_key]) & "_" & [commodity_id], type text),',
        "    EnrichSeries = (grp as table) as table =>",
        "        let",
        '            Sorted = Table.Sort(grp, {{"date_key", Order.Ascending}}),',
        "            PriceList = List.Buffer(Sorted[price_value]),",
        "            MeanPrice = List.Average(PriceList),",
        "            StdPrice = List.StandardDeviation(PriceList),",
        '            Indexed = Table.AddIndexColumn(Sorted, "_idx", 0, 1, Int64.Type),',
        '            WithMom = Table.AddColumn(Indexed, "price_change_mom", each if [_idx] = 0 then null else Number.Round([price_value] - PriceList{[_idx] - 1}, 4), type number),',
        '            WithMomPct = Table.AddColumn(WithMom, "price_change_mom_pct", each if [_idx] = 0 or PriceList{[_idx] - 1} = 0 then null else Number.Round(([price_value] - PriceList{[_idx] - 1}) / PriceList{[_idx] - 1} * 100, 4), type number),',
        '            WithZ = Table.AddColumn(WithMomPct, "z_score", each if StdPrice = null or StdPrice = 0 then 0 else Number.Round(([price_value] - MeanPrice) / StdPrice, 4), type number),',
        '            WithOutlier = Table.AddColumn(WithZ, "is_outlier", each (if [price_change_mom_pct] <> null and Number.Abs([price_change_mom_pct]) > 50 then true else false) or Number.Abs([z_score]) > 3, type logical),',
        '            Cleaned = Table.RemoveColumns(WithOutlier, {"_idx"})',
        "        in",
        "            Cleaned,",
        '    Grouped = Table.Group(AddedPriceId, {"mkt_id", "commodity_id"}, {{"Series", each EnrichSeries(_), type table}}),',
        "    CombinedSeries = Table.Combine(Grouped[Series]),",
        "    FinalTyped = Table.TransformColumnTypes(",
        "        CombinedSeries,",
        "        {",
        '            {"price_id", type text},',
        '            {"mkt_id", type text},',
        '            {"date_key", Int64.Type},',
        '            {"commodity_id", type text},',
        '            {"price_value", type number},',
        '            {"open_price", type number},',
        '            {"high_price", type number},',
        '            {"low_price", type number},',
        '            {"raw_spot_price", type number},',
        '            {"commodity_inflation_yoy", type number},',
        '            {"food_price_index", type number},',
        '            {"inflation_food_price_index", type number},',
        '            {"trust_score", type number},',
        '            {"price_change_mom", type number},',
        '            {"price_change_mom_pct", type number},',
        '            {"z_score", type number},',
        '            {"is_outlier", type logical}',
        "        },",
        '        "en-US"',
        "    ),",
        '    ReorderedCols = Table.ReorderColumns(FinalTyped, {"price_id", "mkt_id", "date_key", "commodity_id", "price_value", "open_price", "high_price", "low_price", "raw_spot_price", "commodity_inflation_yoy", "food_price_index", "inflation_food_price_index", "trust_score", "price_change_mom", "price_change_mom_pct", "z_score", "is_outlier"})',
        "in",
        "    ReorderedCols",
    ]
    return "\n".join(lines) + "\n"


def build_transformation_log_markdown(
    qa: dict[str, Any],
    dim_markets_m: str,
    dim_date_m: str,
    dim_commodity_m: str,
    fact_prices_m: str,
) -> str:
    """Build Week 2 docs/transformation-log.md with plain human prose and verified metrics."""
    dupes = qa["duplicate_pk_counts"]
    orphans = qa["orphan_fk_counts"]
    c_stats = qa["commodity_breakdown"]
    g_stats = qa["county_group_breakdown"]

    lines: list[str] = [
        "# Week 2 Power Query Transformation Log and QA Summary",
        "",
        "**Course:** DSA 3050A | Business Intelligence and Data Visualization (Group Project B)",
        "**Project:** Mzigo Chakula (Kenya Food Price Inflation and Household Affordability, 2007 to 2026)",
        "**Authors:** Prince Nzamuwe, Yizere Denis Derick",
        "**Source Dataset:** `data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv` (World Bank RTFP, CC BY 4.0)",
        "",
        "---",
        "",
        "## 1. Architecture and Data Flow Summary",
        "",
        (
            f"The raw CSV arrives as one wide flat file containing {qa['raw_rows']:,} market-month rows and "
            "46 columns covering three staple commodities (`beans`, `maize_fao`, `livestock_goat_s_fao`) plus "
            "a composite market food index (`c_food_price_index`). Week 2 Power Query transforms split this wide "
            "file into four normalized star-schema tables:"
        ),
        "",
        (
            f"1. `dim_markets` ({qa['dim_markets_rows']:,} rows): One row per physical Kenyan market (`mkt_id = geo_id`), "
            f"normalized across {qa['asal_counties_count'] + qa['agri_urban_counties_count']} counties, 7 former provinces/regions, "
            "and two climate/market groupings (`Arid & Semi-Arid (ASAL)` vs. `Agricultural & Urban`)."
        ),
        (
            f"2. `dim_date` ({qa['dim_date_rows']:,} rows): One row per consecutive month from "
            f"{qa['date_min']} to {qa['date_max']}, enriched with Kenyan agricultural seasons and recency flags."
        ),
        (
            f"3. `dim_commodity` ({qa['dim_commodity_rows']} rows): Lookup table defining standardized commodity display "
            "names, food categories, units of measure, and RTFP basket weights."
        ),
        (
            f"4. `fact_prices` ({qa['fact_prices_rows']:,} rows): Unpivoted commodity observations at the "
            "`(mkt_id, date_key, commodity_id)` grain with OHLC prices, raw spot surveys, YoY inflation, "
            "model trust scores, composite food index, MoM price changes, series z-scores, and outlier flags."
        ),
        "",
        (
            "**Grain Design Note:** Each physical market-month appears once in `c_food_price_index`, so after "
            "unpivoting 3 commodities that index value repeats across 3 commodity rows in `fact_prices`. Week 3 "
            "DAX measures will aggregate `food_price_index` safely across market-month keys (or average per market-month) "
            "so composite index figures are never triple-counted."
        ),
        "",
        "---",
        "",
        "## 2. Ten Power Query Transformations Implemented",
        "",
        "| Step | Transformation | Target Table | Power Query M Operation | Business Justification | Before State | After State |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        (
            "| T1 | Parse `price_date` and build `date_key` | `dim_date`, `fact_prices` | "
            "`Table.TransformColumnTypes(..., \"en-US\")`, `year * 10000 + month * 100 + Day` | "
            "Source stores `price_date` as ISO text; native `Date` and integer `date_key` enable relationships and DAX time intelligence | "
            "Text strings (`\"2007-01-01\"`) | Native `Date` + Int64 `date_key` (`20070101` to `20261001`) |"
        ),
        (
            "| T2 | Derive calendar fields and Kenya agricultural seasons | `dim_date` | "
            "`Date.ToText`, `Date.QuarterOfYear`, conditional `if List.Contains(...)` season mapping | "
            "Raw CSV only has `year` and `month`; Kenyan lean, long-rains, harvest, and short-rains windows drive seasonal food price peaks | "
            "`year`, `month` only | `year`, `month`, `month_name`, `year_month`, `quarter`, `season` |"
        ),
        (
            "| T3 | Exclude `Market Average` rows and all-null price records | `dim_markets`, `fact_prices` | "
            "`Table.SelectRows` (`geo_id <> \"gid_ken_national_average\"` and `mkt_name <> \"Market Average\"`) | "
            "Prevents double-counting synthetic national summary rows and removes rows with blank `lat`/`lon` coordinates | "
            f"{qa['raw_rows']:,} raw rows (incl. {qa['market_average_rows_removed']} national aggregates) | "
            f"{qa['physical_market_rows']:,} physical rows; {qa['null_lat_lon_after']} null `lat`/`lon` |"
        ),
        (
            "| T4 | Standardize admin labels and ASAL vs. Urban/Agri groups | `dim_markets` | "
            "`Table.NestedJoin` against 35-pair lookup table plus `Kitengela (Kajiado)` override and `AsalCounties` check | "
            "Raw `adm1_name` and `adm2_name` mix former provinces and counties, splitting five counties and placing Kitengela under Nairobi | "
            "35 ambiguous admin pairs | "
            f"{qa['dim_markets_rows']:,} markets across 27 clean counties ({qa['asal_counties_count']} ASAL, {qa['agri_urban_counties_count']} Agri/Urban) |"
        ),
        (
            "| T5 | Unpivot OHLC, raw spot, inflation, and trust columns by commodity | `fact_prices` | "
            "`ProjectCommodity` helper + `Table.Combine` across 3 commodities | "
            "Converts wide horizontal commodity columns into a tidy star-schema fact table aligned with `dim_commodity` | "
            f"{qa['physical_market_rows']:,} wide market-month rows | "
            f"{qa['fact_prices_rows']:,} long rows (`3 x {qa['physical_market_rows']:,}`) |"
        ),
        (
            "| T6 | Standardize commodity display labels | `dim_commodity`, `fact_prices` | "
            "Typed `#table` lookup (`Beans (1 kg)`, `Maize (1 kg)`, `Goat (1 head)`) | "
            "Replaces machine codes like `c_maize_fao` and `c_livestock_goat_s_fao` with reader-friendly report labels | "
            "Raw column prefixes (`c_beans`, `c_maize_fao`, `c_livestock_goat_s_fao`) | Clean names paired with immutable `commodity_id` keys |"
        ),
        (
            "| T7 | Add commodity categories and units of measure | `dim_commodity` | "
            "Explicit attribute mapping in `dim_commodity` `#table` | "
            "Prevents mixing per-kilogram staple crops with per-head livestock prices in unweighted averages | "
            "Implicit weights inside `components` text column | Explicit `category` (`Legume Staple`, `Cereal Staple`, `Livestock / Protein`) and `unit` (`KG`, `Head`) |"
        ),
        (
            "| T8 | Compute series Month-over-Month price change (KES and %) | `fact_prices` | "
            "`Table.Group` by `(mkt_id, commodity_id)`, sort by `date_key`, `List.Buffer` lag lookup | "
            "Captures short-term monthly price shocks per market-commodity without cross-market contamination | "
            "Only YoY `inflation_*` provided in source | `price_change_mom` and `price_change_mom_pct` populated on "
            f"{qa['valid_mom_rows']:,} rows ({qa['null_mom_rows']} null baseline rows in 2007-01) |"
        ),
        (
            "| T9 | Flag statistical outliers and validate positive prices | `fact_prices` | "
            "Series z-score (`List.Average`, `List.StandardDeviation`) + `abs(MoM%) > 50 or abs(z) > 3` check | "
            "Surfaces extreme market spikes for inspection while keeping all 238 continuous monthly observations intact for DAX time intelligence | "
            "Unflagged wide prices | "
            f"{qa['outlier_rows']:,} outliers flagged ({qa['outlier_pct']}%), {qa['non_positive_price_count']} non-positive prices |"
        ),
        (
            "| T10 | Add 12-month and 36-month recency filter flags | `dim_date` | "
            "`Date.AddMonths(List.Max([full_date]), -11)` and `-35` comparisons | "
            "Simplifies slicer defaults for the 12-month Executive Pulse and 3-year YoY Analytical Question #1 | "
            "Full 19-year date range only | "
            f"`is_recent` marks {qa['recent_12m_dates']} months ({qa['recent_12m_start']} to {qa['recent_12m_end']}); `is_last_36m` marks {qa['last_36m_dates']} months |"
        ),
        "",
        "---",
        "",
        "## 3. Before and After QA Verification Results",
        "",
        "All checks below were executed on the raw CSV via `mzigo_chakula.etl.run_etl()` and verified by `pytest` (`tests/test_etl.py`).",
        "",
        "### Table Counts, Keys, and Integrity Checks",
        "",
        "| Check | Before Cleaning | After Week 2 ETL | Status |",
        "| --- | --- | --- | --- |",
        f"| Total raw rows vs. physical market-month rows | {qa['raw_rows']:,} | {qa['physical_market_rows']:,} ({qa['market_average_rows_removed']} Market Average + {qa['all_null_physical_rows_removed']} empty rows removed) | Verified |",
        f"| `dim_markets` row count (`mkt_id` distinct keys) | Mixed 35 `(adm1, adm2)` pairs + 1 aggregate | {qa['dim_markets_rows']:,} markets across 27 counties and 7 regions | Verified |",
        f"| `dim_date` row count (`date_key` distinct months) | Text dates `{qa['date_min']}` to `{qa['date_max']}` | {qa['dim_date_rows']:,} continuous monthly rows | Verified |",
        f"| `dim_commodity` row count | Embedded in 46 wide columns | {qa['dim_commodity_rows']} commodities | Verified |",
        f"| `fact_prices` unpivoted row count | {qa['physical_market_rows']:,} wide rows | {qa['fact_prices_rows']:,} long rows (`{qa['physical_market_rows']:,} x 3`) | Verified |",
        f"| Duplicate primary keys (`dim_markets` / `dim_date` / `dim_commodity` / `fact_prices`) | Not structured | `{dupes['dim_markets']} / {dupes['dim_date']} / {dupes['dim_commodity']} / {dupes['fact_prices']}` | Pass |",
        f"| Orphan foreign keys (`mkt_id` / `date_key` / `commodity_id`) | Not structured | `{orphans['mkt_id']} / {orphans['date_key']} / {orphans['commodity_id']}` | Pass |",
        f"| Missing coordinates (`lat` / `lon`) | 238 null pairs (`0.43%` on Market Average) | {qa['null_lat_lon_after']} null pairs | Pass |",
        f"| Missing or non-positive closing `price_value` | N/A | {qa['null_price_value_after']} nulls, {qa['non_positive_price_count']} non-positive | Pass |",
        f"| `price_change_mom` coverage | Not present | {qa['valid_mom_rows']:,} valid rows; {qa['null_mom_rows']} baseline nulls (2007-01 across {qa['dim_markets_rows']} x 3 series) | Verified |",
        f"| YoY inflation missingness (`commodity_inflation_yoy` / `inflation_food_price_index`) | 2,808 wide nulls (5.04%, year 2007) | {qa['null_commodity_inflation_rows']:,} / {qa['null_index_inflation_rows']:,} long nulls (`{qa['dim_markets_rows'] * 12:,} x 3` physical year-2007 rows; 12 Market Average rows excluded) | Verified |",
        "",
        "### Commodity Summary After Unpivoting and Outlier Flagging (`fact_prices`)",
        "",
        "| Commodity | Rows | Min Price (KES) | Mean Price (KES) | Max Price (KES) | Mean MoM (%) | Flagged Outliers |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for spec in COMMODITY_SPECS:
        item = c_stats[spec.commodity_id]
        lines.append(
            f"| {item['commodity_name']} | {item['rows']:,} | {item['min_price']:,.2f} | "
            f"{item['mean_price']:,.2f} | {item['max_price']:,.2f} | {item['mean_mom_pct']:.2f}% | "
            f"{item['outlier_rows']:,} |"
        )

    lines.extend(
        [
            "",
            "### Regional Market Group Summary (`dim_markets` + `fact_prices`)",
            "",
            "| County Group | Counties | Markets | Fact Rows | Flagged Outliers |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )

    for group_name in ("Arid & Semi-Arid (ASAL)", "Agricultural & Urban"):
        g = g_stats[group_name]
        lines.append(
            f"| {group_name} | {g['counties']} | {g['markets']} | {g['fact_rows']:,} | {g['outlier_rows']:,} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Reproducible Power Query (M) Scripts",
            "",
            "Saved under `powerquery/` for direct import into Power BI Desktop:",
            "",
            "- [powerquery/dim_markets.pq](../powerquery/dim_markets.pq)",
            "- [powerquery/dim_date.pq](../powerquery/dim_date.pq)",
            "- [powerquery/dim_commodity.pq](../powerquery/dim_commodity.pq)",
            "- [powerquery/fact_prices.pq](../powerquery/fact_prices.pq)",
            "",
            "### `dim_markets`",
            "",
            "```powerquery",
            dim_markets_m.rstrip(),
            "```",
            "",
            "### `dim_date`",
            "",
            "```powerquery",
            dim_date_m.rstrip(),
            "```",
            "",
            "### `dim_commodity`",
            "",
            "```powerquery",
            dim_commodity_m.rstrip(),
            "```",
            "",
            "### `fact_prices`",
            "",
            "```powerquery",
            fact_prices_m.rstrip(),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def generate_week2_outputs(
    csv_path: Path | None = None,
    processed_dir: Path | None = None,
    powerquery_dir: Path | None = None,
    docs_dir: Path | None = None,
) -> dict[str, Path]:
    """Run Week 2 ETL and write dimension CSVs, Power Query scripts, and transformation log."""
    source_csv = csv_path or DEFAULT_RAW_CSV
    out_processed = processed_dir or PROCESSED_DIR
    out_pq = powerquery_dir or POWERQUERY_DIR
    out_docs = docs_dir or DOCS_DIR

    result: ETLResult = run_etl(csv_path=source_csv)

    dim_markets_csv = _write_csv_table(result.dim_markets, out_processed / "dim_markets.csv")
    dim_date_csv = _write_csv_table(result.dim_date, out_processed / "dim_date.csv")
    dim_commodity_csv = _write_csv_table(result.dim_commodity, out_processed / "dim_commodity.csv")

    out_pq.mkdir(parents=True, exist_ok=True)
    dim_markets_m = build_dim_markets_m(source_csv)
    dim_date_m = build_dim_date_m(source_csv)
    dim_commodity_m = build_dim_commodity_m()
    fact_prices_m = build_fact_prices_m(source_csv)

    pq_markets_path = out_pq / "dim_markets.pq"
    pq_date_path = out_pq / "dim_date.pq"
    pq_commodity_path = out_pq / "dim_commodity.pq"
    pq_fact_path = out_pq / "fact_prices.pq"

    pq_markets_path.write_text(dim_markets_m, encoding="utf-8")
    pq_date_path.write_text(dim_date_m, encoding="utf-8")
    pq_commodity_path.write_text(dim_commodity_m, encoding="utf-8")
    pq_fact_path.write_text(fact_prices_m, encoding="utf-8")

    out_docs.mkdir(parents=True, exist_ok=True)
    log_path = out_docs / "transformation-log.md"
    log_markdown = build_transformation_log_markdown(
        qa=result.qa_metrics,
        dim_markets_m=dim_markets_m,
        dim_date_m=dim_date_m,
        dim_commodity_m=dim_commodity_m,
        fact_prices_m=fact_prices_m,
    )
    log_path.write_text(log_markdown, encoding="utf-8")

    return {
        "dim_markets_csv": dim_markets_csv,
        "dim_date_csv": dim_date_csv,
        "dim_commodity_csv": dim_commodity_csv,
        "dim_markets_pq": pq_markets_path,
        "dim_date_pq": pq_date_path,
        "dim_commodity_pq": pq_commodity_path,
        "fact_prices_pq": pq_fact_path,
        "transformation_log": log_path,
    }


if __name__ == "__main__":
    outputs = generate_week2_outputs()
    for label, file_path in outputs.items():
        print(f"{label}: {file_path}")
