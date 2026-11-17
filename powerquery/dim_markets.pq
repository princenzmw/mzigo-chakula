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
