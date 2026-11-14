# Week 2 Power Query Transformation Log and QA Summary

**Course:** DSA 3050A | Business Intelligence and Data Visualization (Group Project B)
**Project:** Mzigo Chakula (Kenya Food Price Inflation and Household Affordability, 2007 to 2026)
**Authors:** Prince Nzamuwe, Yizere Denis Derick
**Source Dataset:** `data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv` (World Bank RTFP, CC BY 4.0)

---

## 1. Architecture and Data Flow Summary

The raw CSV arrives as one wide flat file containing 55,692 market-month rows and 46 columns covering three staple commodities (`beans`, `maize_fao`, `livestock_goat_s_fao`) plus a composite market food index (`c_food_price_index`). Week 2 Power Query transforms split this wide file into four normalized star-schema tables:

1. `dim_markets` (233 rows): One row per physical Kenyan market (`mkt_id = geo_id`), normalized across 27 counties, 7 former provinces/regions, and two climate/market groupings (`Arid & Semi-Arid (ASAL)` vs. `Agricultural & Urban`).
2. `dim_date` (238 rows): One row per consecutive month from 2007-01-01 to 2026-10-01, enriched with Kenyan agricultural seasons and recency flags.
3. `dim_commodity` (3 rows): Lookup table defining standardized commodity display names, food categories, units of measure, and RTFP basket weights.
4. `fact_prices` (166,362 rows): Unpivoted commodity observations at the `(mkt_id, date_key, commodity_id)` grain with OHLC prices, raw spot surveys, YoY inflation, model trust scores, composite food index, MoM price changes, series z-scores, and outlier flags.

**Grain Design Note:** Each physical market-month appears once in `c_food_price_index`, so after unpivoting 3 commodities that index value repeats across 3 commodity rows in `fact_prices`. Week 3 DAX measures will aggregate `food_price_index` safely across market-month keys (or average per market-month) so composite index figures are never triple-counted.

---

## 2. Ten Power Query Transformations Implemented

| Step | Transformation | Target Table | Power Query M Operation | Business Justification | Before State | After State |
| --- | --- | --- | --- | --- | --- | --- |
| T1 | Parse `price_date` and build `date_key` | `dim_date`, `fact_prices` | `Table.TransformColumnTypes(..., "en-US")`, `year * 10000 + month * 100 + Day` | Source stores `price_date` as ISO text; native `Date` and integer `date_key` enable relationships and DAX time intelligence | Text strings (`"2007-01-01"`) | Native `Date` + Int64 `date_key` (`20070101` to `20261001`) |
| T2 | Derive calendar fields and Kenya agricultural seasons | `dim_date` | `Date.ToText`, `Date.QuarterOfYear`, conditional `if List.Contains(...)` season mapping | Raw CSV only has `year` and `month`; Kenyan lean, long-rains, harvest, and short-rains windows drive seasonal food price peaks | `year`, `month` only | `year`, `month`, `month_name`, `year_month`, `quarter`, `season` |
| T3 | Exclude `Market Average` rows and all-null price records | `dim_markets`, `fact_prices` | `Table.SelectRows` (`geo_id <> "gid_ken_national_average"` and `mkt_name <> "Market Average"`) | Prevents double-counting synthetic national summary rows and removes rows with blank `lat`/`lon` coordinates | 55,692 raw rows (incl. 238 national aggregates) | 55,454 physical rows; 0 null `lat`/`lon` |
| T4 | Standardize admin labels and ASAL vs. Urban/Agri groups | `dim_markets` | `Table.NestedJoin` against 35-pair lookup table plus `Kitengela (Kajiado)` override and `AsalCounties` check | Raw `adm1_name` and `adm2_name` mix former provinces and counties, splitting five counties and placing Kitengela under Nairobi | 35 ambiguous admin pairs | 233 markets across 27 clean counties (16 ASAL, 11 Agri/Urban) |
| T5 | Unpivot OHLC, raw spot, inflation, and trust columns by commodity | `fact_prices` | `ProjectCommodity` helper + `Table.Combine` across 3 commodities | Converts wide horizontal commodity columns into a tidy star-schema fact table aligned with `dim_commodity` | 55,454 wide market-month rows | 166,362 long rows (`3 x 55,454`) |
| T6 | Standardize commodity display labels | `dim_commodity`, `fact_prices` | Typed `#table` lookup (`Beans (1 kg)`, `Maize (1 kg)`, `Goat (1 head)`) | Replaces machine codes like `c_maize_fao` and `c_livestock_goat_s_fao` with reader-friendly report labels | Raw column prefixes (`c_beans`, `c_maize_fao`, `c_livestock_goat_s_fao`) | Clean names paired with immutable `commodity_id` keys |
| T7 | Add commodity categories and units of measure | `dim_commodity` | Explicit attribute mapping in `dim_commodity` `#table` | Prevents mixing per-kilogram staple crops with per-head livestock prices in unweighted averages | Implicit weights inside `components` text column | Explicit `category` (`Legume Staple`, `Cereal Staple`, `Livestock / Protein`) and `unit` (`KG`, `Head`) |
| T8 | Compute series Month-over-Month price change (KES and %) | `fact_prices` | `Table.Group` by `(mkt_id, commodity_id)`, sort by `date_key`, `List.Buffer` lag lookup | Captures short-term monthly price shocks per market-commodity without cross-market contamination | Only YoY `inflation_*` provided in source | `price_change_mom` and `price_change_mom_pct` populated on 165,663 rows (699 null baseline rows in 2007-01) |
| T9 | Flag statistical outliers and validate positive prices | `fact_prices` | Series z-score (`List.Average`, `List.StandardDeviation`) + `abs(MoM%) > 50 or abs(z) > 3` check | Surfaces extreme market spikes for inspection while keeping all 238 continuous monthly observations intact for DAX time intelligence | Unflagged wide prices | 1,866 outliers flagged (1.12%), 0 non-positive prices |
| T10 | Add 12-month and 36-month recency filter flags | `dim_date` | `Date.AddMonths(List.Max([full_date]), -11)` and `-35` comparisons | Simplifies slicer defaults for the 12-month Executive Pulse and 3-year YoY Analytical Question #1 | Full 19-year date range only | `is_recent` marks 12 months (2025-11-01 to 2026-10-01); `is_last_36m` marks 36 months |

---

## 3. Before and After QA Verification Results

All checks below were executed on the raw CSV via `mzigo_chakula.etl.run_etl()` and verified by `pytest` (`tests/test_etl.py`).

### Table Counts, Keys, and Integrity Checks

| Check | Before Cleaning | After Week 2 ETL | Status |
| --- | --- | --- | --- |
| Total raw rows vs. physical market-month rows | 55,692 | 55,454 (238 Market Average + 0 empty rows removed) | Verified |
| `dim_markets` row count (`mkt_id` distinct keys) | Mixed 35 `(adm1, adm2)` pairs + 1 aggregate | 233 markets across 27 counties and 7 regions | Verified |
| `dim_date` row count (`date_key` distinct months) | Text dates `2007-01-01` to `2026-10-01` | 238 continuous monthly rows | Verified |
| `dim_commodity` row count | Embedded in 46 wide columns | 3 commodities | Verified |
| `fact_prices` unpivoted row count | 55,454 wide rows | 166,362 long rows (`55,454 x 3`) | Verified |
| Duplicate primary keys (`dim_markets` / `dim_date` / `dim_commodity` / `fact_prices`) | Not structured | `0 / 0 / 0 / 0` | Pass |
| Orphan foreign keys (`mkt_id` / `date_key` / `commodity_id`) | Not structured | `0 / 0 / 0` | Pass |
| Missing coordinates (`lat` / `lon`) | 238 null pairs (`0.43%` on Market Average) | 0 null pairs | Pass |
| Missing or non-positive closing `price_value` | N/A | 0 nulls, 0 non-positive | Pass |
| `price_change_mom` coverage | Not present | 165,663 valid rows; 699 baseline nulls (2007-01 across 233 x 3 series) | Verified |
| YoY inflation missingness (`commodity_inflation_yoy` / `inflation_food_price_index`) | 2,808 wide nulls (5.04%, year 2007) | 8,388 / 8,388 long nulls (`2,796 x 3` physical year-2007 rows; 12 Market Average rows excluded) | Verified |

### Commodity Summary After Unpivoting and Outlier Flagging (`fact_prices`)

| Commodity | Rows | Min Price (KES) | Mean Price (KES) | Max Price (KES) | Mean MoM (%) | Flagged Outliers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Beans (1 kg) | 55,454 | 34.00 | 105.69 | 241.19 | 0.59% | 97 |
| Maize (1 kg) | 55,454 | 9.00 | 56.02 | 136.98 | 0.68% | 3 |
| Goat (1 head) | 55,454 | 480.69 | 3,456.14 | 28,380.59 | 1.08% | 1,766 |

### Regional Market Group Summary (`dim_markets` + `fact_prices`)

| County Group | Counties | Markets | Fact Rows | Flagged Outliers |
| --- | ---: | ---: | ---: | ---: |
| Arid & Semi-Arid (ASAL) | 16 | 202 | 144,228 | 1,638 |
| Agricultural & Urban | 11 | 31 | 22,134 | 228 |

---

## 4. Reproducible Power Query (M) Scripts

Saved under `powerquery/` for direct import into Power BI Desktop:

- [powerquery/dim_markets.pq](../powerquery/dim_markets.pq)
- [powerquery/dim_date.pq](../powerquery/dim_date.pq)
- [powerquery/dim_commodity.pq](../powerquery/dim_commodity.pq)
- [powerquery/fact_prices.pq](../powerquery/fact_prices.pq)

### `dim_markets`

```powerquery
// Mzigo Chakula: dim_markets (233 physical Kenyan markets across 27 counties and 7 regions)
// Update CsvPath if moving the repository to a different folder.
let
    CsvPath = "D:\COURSES\FS2026\DSA3050A TT17 BusIntDViz\Projects\mzigo-chakula\data\raw\KEN_RTFP_mkt_2007_2026-10-05.csv",
    Source = Csv.Document(File.Contents(CsvPath), [Delimiter=",", Columns=46, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    FilteredPhysical = Table.SelectRows(PromotedHeaders, each [geo_id] <> "gid_ken_national_average" and [mkt_name] <> "Market Average"),
    SelectedCols = Table.SelectColumns(FilteredPhysical, {"geo_id", "mkt_name", "adm1_name", "adm2_name", "lat", "lon", "data_coverage", "data_coverage_recent"}),
    DistinctMarkets = Table.Distinct(SelectedCols, {"geo_id"}),
    RenamedRawCols = Table.RenameColumns(DistinctMarkets, {{"geo_id", "mkt_id"}, {"adm1_name", "raw_adm1_name"}, {"adm2_name", "raw_adm2_name"}}),
    TypedCols = Table.TransformColumnTypes(
        RenamedRawCols,
        {
            {"mkt_id", type text},
            {"mkt_name", type text},
            {"raw_adm1_name", type text},
            {"raw_adm2_name", type text},
            {"lat", type number},
            {"lon", type number},
            {"data_coverage", type number},
            {"data_coverage_recent", type number}
        },
        "en-US"
    ),
    CountyLookup = #table(
        {"raw_adm1_name", "raw_adm2_name", "adm1_name", "adm2_name", "subcounty_or_district"},
        {
        {"Central", "Nyeri", "Central", "Nyeri", "Nyeri"},
        {"Coast", "Kilifi", "Coast", "Kilifi", "Kilifi"},
        {"Coast", "Kwale", "Coast", "Kwale", "Kwale"},
        {"Coast", "Mombasa", "Coast", "Mombasa", "Mombasa"},
        {"Coast", "Taita Taveta", "Coast", "Taita Taveta", "Taita Taveta"},
        {"Coast", "Tana River", "Coast", "Tana River", "Tana River"},
        {"Eastern", "Isiolo", "Eastern", "Isiolo", "Isiolo"},
        {"Eastern", "Kitui", "Eastern", "Kitui", "Kitui"},
        {"Eastern", "Machakos", "Eastern", "Machakos", "Machakos"},
        {"Eastern", "Makueni", "Eastern", "Makueni", "Makueni"},
        {"Eastern", "Marsabit", "Eastern", "Marsabit", "Marsabit"},
        {"Eastern", "Meru North", "Eastern", "Meru", "Meru North"},
        {"Eastern", "Meru South", "Eastern", "Tharaka Nithi", "Meru South"},
        {"Eastern", "Moyale", "Eastern", "Marsabit", "Moyale"},
        {"Embu", "Mbeere North", "Eastern", "Embu", "Mbeere North"},
        {"Hola (Tana River)", "Hola (Tana River)", "Coast", "Tana River", "Hola"},
        {"Kajiado", "Ongata Rongai", "Rift Valley", "Kajiado", "Ongata Rongai"},
        {"Kwale", "Matuga", "Coast", "Kwale", "Matuga"},
        {"Lamu", "Lamu West", "Coast", "Lamu", "Lamu West"},
        {"Meru", "North Imenti", "Eastern", "Meru", "North Imenti"},
        {"Nairobi", "Nairobi", "Nairobi", "Nairobi", "Nairobi"},
        {"North Eastern", "Garissa", "North Eastern", "Garissa", "Garissa"},
        {"North Eastern", "Ijara", "North Eastern", "Garissa", "Ijara"},
        {"North Eastern", "Mandera", "North Eastern", "Mandera", "Mandera"},
        {"North Eastern", "Wajir", "North Eastern", "Wajir", "Wajir"},
        {"Nyanza", "Kisumu", "Nyanza", "Kisumu", "Kisumu"},
        {"Rift Valley", "Baringo", "Rift Valley", "Baringo", "Baringo"},
        {"Rift Valley", "Kajiado", "Rift Valley", "Kajiado", "Kajiado"},
        {"Rift Valley", "Nakuru", "Rift Valley", "Nakuru", "Nakuru"},
        {"Rift Valley", "Samburu", "Rift Valley", "Samburu", "Samburu"},
        {"Rift Valley", "Turkana", "Rift Valley", "Turkana", "Turkana"},
        {"Rift Valley", "Uasin Gishu", "Rift Valley", "Uasin Gishu", "Uasin Gishu"},
        {"Rift Valley", "West Pokot", "Rift Valley", "West Pokot", "West Pokot"},
        {"Taita Taveta", "Voi", "Coast", "Taita Taveta", "Voi"},
        {"Tharaka Nithi", "Chuka/Igambang'Ombe", "Eastern", "Tharaka Nithi", "Chuka/Igambang'Ombe"}
        }
    ),
    MarketOverrideLookup = #table(
        {"mkt_name", "ov_region", "ov_county", "ov_subcounty"},
        {
        {"Kitengela (Kajiado)", "Rift Valley", "Kajiado", "Kitengela"}
        }
    ),
    JoinedAdmin = Table.NestedJoin(TypedCols, {"raw_adm1_name", "raw_adm2_name"}, CountyLookup, {"raw_adm1_name", "raw_adm2_name"}, "AdminMatch", JoinKind.Inner),
    ExpandedAdmin = Table.ExpandTableColumn(JoinedAdmin, "AdminMatch", {"adm1_name", "adm2_name", "subcounty_or_district"}, {"map_region", "map_county", "map_subcounty"}),
    JoinedOverride = Table.NestedJoin(ExpandedAdmin, {"mkt_name"}, MarketOverrideLookup, {"mkt_name"}, "OverrideMatch", JoinKind.LeftOuter),
    ExpandedOverride = Table.ExpandTableColumn(JoinedOverride, "OverrideMatch", {"ov_region", "ov_county", "ov_subcounty"}),
    ResolvedRegion = Table.AddColumn(ExpandedOverride, "adm1_name", each if [ov_region] <> null then [ov_region] else [map_region], type text),
    ResolvedCounty = Table.AddColumn(ResolvedRegion, "adm2_name", each if [ov_county] <> null then [ov_county] else [map_county], type text),
    ResolvedSubcounty = Table.AddColumn(ResolvedCounty, "subcounty_or_district", each if [ov_subcounty] <> null then [ov_subcounty] else [map_subcounty], type text),
    RemovedTempCols = Table.RemoveColumns(ResolvedSubcounty, {"map_region", "map_county", "map_subcounty", "ov_region", "ov_county", "ov_subcounty"}),
    AsalCounties = {"Baringo", "Garissa", "Isiolo", "Kajiado", "Kilifi", "Kitui", "Kwale", "Laikipia", "Makueni", "Mandera", "Marsabit", "Samburu", "Taita Taveta", "Tana River", "Turkana", "Wajir", "West Pokot"},
    AddedCountyGroup = Table.AddColumn(RemovedTempCols, "county_group", each if List.Contains(AsalCounties, [adm2_name]) then "Arid & Semi-Arid (ASAL)" else "Agricultural & Urban", type text),
    ReorderedCols = Table.ReorderColumns(AddedCountyGroup, {"mkt_id", "mkt_name", "adm1_name", "adm2_name", "subcounty_or_district", "raw_adm1_name", "raw_adm2_name", "county_group", "lat", "lon", "data_coverage", "data_coverage_recent"}),
    SortedMarkets = Table.Sort(ReorderedCols, {{"adm2_name", Order.Ascending}, {"mkt_name", Order.Ascending}})
in
    SortedMarkets
```

### `dim_date`

```powerquery
// Mzigo Chakula: dim_date (238 consecutive monthly periods from 2007-01-01 to 2026-10-01)
// Update CsvPath if moving the repository to a different folder.
let
    CsvPath = "D:\COURSES\FS2026\DSA3050A TT17 BusIntDViz\Projects\mzigo-chakula\data\raw\KEN_RTFP_mkt_2007_2026-10-05.csv",
    Source = Csv.Document(File.Contents(CsvPath), [Delimiter=",", Columns=46, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    SelectedDateCols = Table.SelectColumns(PromotedHeaders, {"price_date", "year", "month"}),
    DistinctDates = Table.Distinct(SelectedDateCols, {"price_date"}),
    TypedDates = Table.TransformColumnTypes(DistinctDates, {{"price_date", type date}, {"year", Int64.Type}, {"month", Int64.Type}}, "en-US"),
    RenamedDateCol = Table.RenameColumns(TypedDates, {{"price_date", "full_date"}}),
    SortedDates = Table.Sort(RenamedDateCol, {{"full_date", Order.Ascending}}),
    AddedDateKey = Table.AddColumn(SortedDates, "date_key", each [year] * 10000 + [month] * 100 + Date.Day([full_date]), Int64.Type),
    AddedMonthName = Table.AddColumn(AddedDateKey, "month_name", each Date.ToText([full_date], "MMM", "en-US"), type text),
    AddedYearMonth = Table.AddColumn(AddedMonthName, "year_month", each Date.ToText([full_date], "yyyy-MM", "en-US"), type text),
    AddedQuarter = Table.AddColumn(AddedYearMonth, "quarter", each "Q" & Text.From(Date.QuarterOfYear([full_date])), type text),
    AddedSeason = Table.AddColumn(
        AddedQuarter,
        "season",
        each if List.Contains({1, 2}, [month]) then "Hot Dry / Lean (Jan-Feb)" else if List.Contains({3, 4, 5}, [month]) then "Long Rains (Mar-May)" else if List.Contains({6, 7, 8, 9}, [month]) then "Cool Dry / Harvest (Jun-Sep)" else "Short Rains (Oct-Dec)",
        type text
    ),
    MaxDate = List.Max(AddedSeason[full_date]),
    AddedIsRecent = Table.AddColumn(AddedSeason, "is_recent", each [full_date] >= Date.AddMonths(MaxDate, -11), type logical),
    AddedIsLast36M = Table.AddColumn(AddedIsRecent, "is_last_36m", each [full_date] >= Date.AddMonths(MaxDate, -35), type logical),
    ReorderedCols = Table.ReorderColumns(AddedIsLast36M, {"date_key", "full_date", "year", "month", "month_name", "year_month", "quarter", "season", "is_recent", "is_last_36m"})
in
    ReorderedCols
```

### `dim_commodity`

```powerquery
// Mzigo Chakula: dim_commodity (3 tracked Kenyan staple commodities)
let
    CommodityTable = #table(
        type table [
            commodity_id = text,
            commodity_name = text,
            category = text,
            unit = text,
            index_weight_note = text
        ],
        {
        {"beans", "Beans (1 kg)", "Legume Staple", "KG", "RTFP basket item: beans (1 KG, Index Weight = 1)"},
        {"maize_fao", "Maize (1 kg)", "Cereal Staple", "KG", "RTFP basket item: maize_fao (1 Kg, Index Weight = 1)"},
        {"livestock_goat_s_fao", "Goat (1 head)", "Livestock / Protein", "Head", "RTFP basket item: livestock_goat_s_fao (1 unit, Index Weight = 0)"}
        }
    )
in
    CommodityTable
```

### `fact_prices`

```powerquery
// Mzigo Chakula: fact_prices (166,362 market-month-commodity records from 55,454 physical market observations)
// Update CsvPath if moving the repository to a different folder.
let
    CsvPath = "D:\COURSES\FS2026\DSA3050A TT17 BusIntDViz\Projects\mzigo-chakula\data\raw\KEN_RTFP_mkt_2007_2026-10-05.csv",
    Source = Csv.Document(File.Contents(CsvPath), [Delimiter=",", Columns=46, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    SelectedCols = Table.SelectColumns(PromotedHeaders, {"geo_id", "mkt_name", "price_date", "year", "month", "c_food_price_index", "inflation_food_price_index", "c_beans", "o_beans", "h_beans", "l_beans", "beans", "inflation_beans", "trust_beans", "c_maize_fao", "o_maize_fao", "h_maize_fao", "l_maize_fao", "maize_fao", "inflation_maize_fao", "trust_maize_fao", "c_livestock_goat_s_fao", "o_livestock_goat_s_fao", "h_livestock_goat_s_fao", "l_livestock_goat_s_fao", "livestock_goat_s_fao", "inflation_livestock_goat_s_fao", "trust_livestock_goat_s_fao"}),
    TypedBase = Table.TransformColumnTypes(
        SelectedCols,
        {
            {"geo_id", type text},
            {"mkt_name", type text},
            {"price_date", type date},
            {"year", Int64.Type},
            {"month", Int64.Type},
            {"c_food_price_index", type number},
            {"inflation_food_price_index", type number},
            {"c_beans", type number},
            {"o_beans", type number},
            {"h_beans", type number},
            {"l_beans", type number},
            {"beans", type number},
            {"inflation_beans", type number},
            {"trust_beans", type number},
            {"c_maize_fao", type number},
            {"o_maize_fao", type number},
            {"h_maize_fao", type number},
            {"l_maize_fao", type number},
            {"maize_fao", type number},
            {"inflation_maize_fao", type number},
            {"trust_maize_fao", type number},
            {"c_livestock_goat_s_fao", type number},
            {"o_livestock_goat_s_fao", type number},
            {"h_livestock_goat_s_fao", type number},
            {"l_livestock_goat_s_fao", type number},
            {"livestock_goat_s_fao", type number},
            {"inflation_livestock_goat_s_fao", type number},
            {"trust_livestock_goat_s_fao", type number}
        },
        "en-US"
    ),
    FilteredPhysical = Table.SelectRows(TypedBase, each [geo_id] <> "gid_ken_national_average" and [mkt_name] <> "Market Average" and ([c_beans] <> null or [c_maize_fao] <> null or [c_livestock_goat_s_fao] <> null)),
    AddedDateKey = Table.AddColumn(FilteredPhysical, "date_key", each [year] * 10000 + [month] * 100 + Date.Day([price_date]), Int64.Type),
    RenamedBase = Table.RenameColumns(AddedDateKey, {{"geo_id", "mkt_id"}, {"c_food_price_index", "food_price_index"}}),
    ProjectCommodity = (base as table, cid as text, closeCol as text, openCol as text, highCol as text, lowCol as text, rawCol as text, inflCol as text, trustCol as text) as table =>
        let
            Subset = Table.SelectColumns(base, {"mkt_id", "date_key", "food_price_index", "inflation_food_price_index", closeCol, openCol, highCol, lowCol, rawCol, inflCol, trustCol}),
            Renamed = Table.RenameColumns(Subset, {
                {closeCol, "price_value"},
                {openCol, "open_price"},
                {highCol, "high_price"},
                {lowCol, "low_price"},
                {rawCol, "raw_spot_price"},
                {inflCol, "commodity_inflation_yoy"},
                {trustCol, "trust_score"}
            }),
            NonNullClose = Table.SelectRows(Renamed, each [price_value] <> null),
            WithCid = Table.AddColumn(NonNullClose, "commodity_id", each cid, type text)
        in
            WithCid,
    Unpivoted = Table.Combine({
        ProjectCommodity(RenamedBase, "beans", "c_beans", "o_beans", "h_beans", "l_beans", "beans", "inflation_beans", "trust_beans"),
        ProjectCommodity(RenamedBase, "maize_fao", "c_maize_fao", "o_maize_fao", "h_maize_fao", "l_maize_fao", "maize_fao", "inflation_maize_fao", "trust_maize_fao"),
        ProjectCommodity(RenamedBase, "livestock_goat_s_fao", "c_livestock_goat_s_fao", "o_livestock_goat_s_fao", "h_livestock_goat_s_fao", "l_livestock_goat_s_fao", "livestock_goat_s_fao", "inflation_livestock_goat_s_fao", "trust_livestock_goat_s_fao")
    }),
    AddedPriceId = Table.AddColumn(Unpivoted, "price_id", each [mkt_id] & "_" & Text.From([date_key]) & "_" & [commodity_id], type text),
    EnrichSeries = (grp as table) as table =>
        let
            Sorted = Table.Sort(grp, {{"date_key", Order.Ascending}}),
            PriceList = List.Buffer(Sorted[price_value]),
            MeanPrice = List.Average(PriceList),
            StdPrice = List.StandardDeviation(PriceList),
            Indexed = Table.AddIndexColumn(Sorted, "_idx", 0, 1, Int64.Type),
            WithMom = Table.AddColumn(Indexed, "price_change_mom", each if [_idx] = 0 then null else Number.Round([price_value] - PriceList{[_idx] - 1}, 4), type number),
            WithMomPct = Table.AddColumn(WithMom, "price_change_mom_pct", each if [_idx] = 0 or PriceList{[_idx] - 1} = 0 then null else Number.Round(([price_value] - PriceList{[_idx] - 1}) / PriceList{[_idx] - 1} * 100, 4), type number),
            WithZ = Table.AddColumn(WithMomPct, "z_score", each if StdPrice = null or StdPrice = 0 then 0 else Number.Round(([price_value] - MeanPrice) / StdPrice, 4), type number),
            WithOutlier = Table.AddColumn(WithZ, "is_outlier", each (if [price_change_mom_pct] <> null and Number.Abs([price_change_mom_pct]) > 50 then true else false) or Number.Abs([z_score]) > 3, type logical),
            Cleaned = Table.RemoveColumns(WithOutlier, {"_idx"})
        in
            Cleaned,
    Grouped = Table.Group(AddedPriceId, {"mkt_id", "commodity_id"}, {{"Series", each EnrichSeries(_), type table}}),
    CombinedSeries = Table.Combine(Grouped[Series]),
    FinalTyped = Table.TransformColumnTypes(
        CombinedSeries,
        {
            {"price_id", type text},
            {"mkt_id", type text},
            {"date_key", Int64.Type},
            {"commodity_id", type text},
            {"price_value", type number},
            {"open_price", type number},
            {"high_price", type number},
            {"low_price", type number},
            {"raw_spot_price", type number},
            {"commodity_inflation_yoy", type number},
            {"food_price_index", type number},
            {"inflation_food_price_index", type number},
            {"trust_score", type number},
            {"price_change_mom", type number},
            {"price_change_mom_pct", type number},
            {"z_score", type number},
            {"is_outlier", type logical}
        },
        "en-US"
    ),
    ReorderedCols = Table.ReorderColumns(FinalTyped, {"price_id", "mkt_id", "date_key", "commodity_id", "price_value", "open_price", "high_price", "low_price", "raw_spot_price", "commodity_inflation_yoy", "food_price_index", "inflation_food_price_index", "trust_score", "price_change_mom", "price_change_mom_pct", "z_score", "is_outlier"})
in
    ReorderedCols
```
