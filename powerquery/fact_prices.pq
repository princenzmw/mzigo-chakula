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
