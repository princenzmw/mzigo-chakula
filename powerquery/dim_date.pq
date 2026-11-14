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
