# Mzigo Chakula

## Food price inflation and household affordability in Kenya from 2007 to 2026

> *Mzigo* (Swahili): burden, load, weight. *Chakula*: food.
> "The weight of food": what does a kilo of maize, a kilo of beans, or a goat actually cost a Kenyan household, and where is that weight heaviest?

DSA 3050A | Business intelligence and data visualization | Group project B

## Problem statement

Food prices in Kenya have risen over the past two decades, with sharp price differences across regions. National inflation reports usually summarize food costs as a single headline rate, which hides sharp regional differences across counties. A household in Turkana faces a different price path than one in Nairobi or Mombasa because staple availability, seasonal timing, and local market volatility differ by region.

This project builds a Power BI report that answers:

> **Which counties, commodities, and time periods carry the heaviest food-price burden, and where should intervention be prioritized?**

Primary audience: County government planners, NGO food-security programs, and household-level policy advisors.

## Dataset

| Attribute | Detail |
| --- | --- |
| Source | World Bank Real Time Food Prices (RTFP), Kenya |
| URL | https://microdata.worldbank.org/index.php/catalog/6167 |
| Date accessed | 29 October 2026 |
| License | CC BY 4.0 (open redistribution) |
| Rows | 55,692 |
| Columns | 46 |
| Geographic coverage | 233 physical markets (+ 1 national average series) across 27 counties |
| Time span | January 2007 to October 2026 (238 consecutive months; 19 years, 10 months) |
| Key fields | geo_id, adm1_name (region/province), adm2_name (county), mkt_name, price_date, year, month, lat, lon, beans, maize_fao, livestock_goat_s_fao, c_beans, c_maize_fao, c_livestock_goat_s_fao, c_food_price_index, inflation_food_price_index |

Ethical note: All data consists of publicly available aggregate market-level prices. No personal or sensitive data is used.

## Data model

```text
┌───────────────────────────┐       ┌──────────────────────────┐
│        dim_markets        │       │         dim_date         │
├───────────────────────────┤       ├──────────────────────────┤
│ mkt_id (PK)               │◄──┐   │ date_key (PK)            │
│ mkt_name                  │   │   │ full_date                │
│ adm1_name (region)        │   │   │ year                     │
│ adm2_name (county)        │   │   │ month                    │
│ subcounty_or_district     │   │   │ month_name               │
│ county_group              │   │   │ year_month               │
│ lat                       │   │   │ quarter                  │
│ lon                       │   │   │ season                   │
│ data_coverage             │   │   │ is_recent                │
│ data_coverage_recent      │   │   │ is_last_36m              │
│ raw_adm1_name (hidden)    │   │   └──────────────────────────┘
│ raw_adm2_name (hidden)    │   │                 ▲
└───────────────────────────┘   │                 │ 1:*
                                │                 │
┌───────────────────────────┐   │                 │
│       dim_commodity       │   │                 │
├───────────────────────────┤   │                 │
│ commodity_id (PK)         │   │                 │
│ commodity_name            │   │                 │
│ category (Legume Staple / │   │                 │
│   Cereal Staple /         │   │                 │
│   Livestock / Protein)    │   │                 │
│ unit (KG / Head)          │   │                 │
│ index_weight_note         │   │                 │
└───────────────────────────┘   │                 │
                                │                 │
┌───────────────────────────────┴─────────────────┴────────────┐
│                         fact_prices                          │
├──────────────────────────────────────────────────────────────┤
│ price_id (PK)                                                │
│ mkt_id (FK -> dim_markets)                                   │
│ date_key (FK -> dim_date)                                    │
│ commodity_id (FK -> dim_commodity)                           │
│ price_value (KES)                                            │
│ open_price, high_price, low_price                            │
│ raw_spot_price                                               │
│ commodity_inflation_yoy                                      │
│ food_price_index                                             │
│ inflation_food_price_index                                   │
│ trust_score                                                  │
│ price_change_mom, price_change_mom_pct                       │
│ z_score, is_outlier                                          │
└──────────────────────────────────────────────────────────────┘
```

Cardinality: All relationships are `1:*` (one market to many price records; one date to many price records; one commodity to many price records).

Filter direction: Single direction from dimension tables into `fact_prices`. No bidirectional filters.

## DAX measures

| # | Measure | Formula (simplified) | Purpose |
| --- | --- | --- | --- |
| 1 | Avg Price (KES) | `AVERAGE(fact_prices[price_value])` | Baseline closing price in KES |
| 2 | National Food Price Index | `AVERAGEX(SUMMARIZE(fact_prices, fact_prices[mkt_id], fact_prices[date_key]), CALCULATE(AVERAGE(fact_prices[food_price_index])))` | Market-month deduplicated composite food index |
| 3 | Prior Year Price (KES) | `CALCULATE([Avg Price (KES)], REMOVEFILTERS(dim_date), TREATAS(EDATE(-12), dim_date[full_date]))` | Commodity price shifted back 12 months |
| 4 | YoY Inflation % | `DIVIDE(CurrentIdx - PriorYearIdx, PriorYearIdx)` using `EDATE(-12)` on `[National Food Price Index]` | Year-over-year change in composite index |
| 5 | Commodity YoY Inflation % | `DIVIDE([Avg Price (KES)] - [Prior Year Price (KES)], [Prior Year Price (KES)])` | Year-over-year change per commodity |
| 6 | MoM Change % | `DIVIDE([Avg Price (KES)] - PriorMonthPrice, PriorMonthPrice)` using `EDATE(-1)` and `TREATAS` | Month-over-month commodity trend |
| 7 | Price Volatility (KES) | `STDEV.S(fact_prices[price_value])` | Sample standard deviation of closing prices |
| 8 | Price Volatility CV % | `AVERAGEX(VALUES(fact_prices[commodity_id]), DIVIDE([Price Volatility (KES)], [Avg Price (KES)]))` | Unit-safe coefficient of variation per commodity |
| 9 | Cumulative Index YTD | `CALCULATE([National Food Price Index], REMOVEFILTERS(dim_date), dim_date[year] = AnchorYear, dim_date[full_date] <= AnchorDate)` | Year-to-date mean composite index |
| 10 | County Inflation Rank | `IF(ISINSCOPE(dim_markets[adm2_name]), RANKX(ALL(dim_markets[adm2_name]), [YoY Inflation %], , DESC, Dense))` | Highest inflation first |
| 11 | Data Completeness % | `DIVIDE(COUNTROWS(fact_prices), COUNTROWS(dim_markets) * COUNTROWS(dim_date) * COUNTROWS(dim_commodity))` | Expected cell completeness on modeled prices |
| 12 | Survey Coverage Rate % | `DIVIDE(COUNT(fact_prices[raw_spot_price]) + 0, COUNTROWS(fact_prices))` | Share of rows with direct field survey spots |
| 13 | Affordability Gap (KES) | `AVERAGEX(VALUES(fact_prices[commodity_id]), [Avg Price (KES)] - CALCULATE([Avg Price (KES)], ALL(dim_markets)))` | Unit-safe local gap vs. national mean |
| 14 | Seasonal Index | `DIVIDE([Avg Price (KES)], CALCULATE([Avg Price (KES)], ALL(dim_date[month], dim_date[month_name], dim_date[season], dim_date[quarter])))` | Ratio of month or season price to all-month mean |
| 15 | 12-Month Rolling Avg (KES) | `CALCULATE(AVERAGEX(VALUES(dim_date[full_date]), [Avg Price (KES)]), REMOVEFILTERS(dim_date), dim_date[full_date] >= EDATE(AnchorDate, -11), <= AnchorDate)` | Gap-safe trailing 12-month smoothed trend |

## Dashboard pages

| Page | Purpose | Key Visuals |
| --- | --- | --- |
| 1. Executive Pulse | National and county overview (16 visuals) | Top banner and native page navigator, 5 slicers, 5 KPI cards (Recent 12m Food Price Index, Recent 12m YoY Inflation %, 2026 YTD Mean Index, Data Completeness %, Survey Coverage Rate %), 238-month National Food Price Index trend line, Top 10 Counties by Recent 12m YoY Inflation bar chart, Recent 12m Commodity Matrix, Top 10 County Watchlist table |
| 2. County and Commodity | Geographic and commodity comparison (10 visuals) | Top banner and native page navigator, 4 slicers, Top 5 Deficit vs. Bottom 5 Surplus Maize Affordability Gap diverging bar chart, 233-market Longitude/Latitude scatter plot, ASAL vs. Agricultural/Urban CV% grouped columns, County Maize Affordability & Survey table |
| 3. Trends and Diagnostics | Seasonality, smoothing, and volatility audit (10 visuals) | Top banner and native page navigator, 4 slicers, Beans and Maize 238-month price trend lines (with 12m Rolling Avg, MoM %, and StdDev hover tooltips), Jan-to-Dec Seasonal Index lines, Top 10 Counties by Maize CV% bars, Seasonal Index by Cropping Window columns |
| 4. Decisions and Action | Stakeholder triage and monitoring matrix (10 visuals) | Top banner and native page navigator, 4 slicers, Monitoring Priority Quadrant scatter (Maize Survey % vs. Maize CV%), Maize-filtered County Priority Action Matrix table, 10 Low-Survey Counties Under 5% (All Commodities) bar chart, Regional Maize Price (KES/kg) grouped columns |

Interactions: Dropdown slicers filter across single-direction `1:*` relationships (Page 1 includes `Commodity`, `County Group`, `Region`, `Cropping Season`, `Year`; Pages 2 and 4 include `Commodity`, `County Group`, `Region`, `Year`; Page 3 includes `Commodity`, `County Group`, `Region`, `Cropping Season`). Cross-filtering links charts and tables, hover tooltips show exact figures, and top header navigation buttons switch pages (hold `Ctrl + Click` in Power BI Desktop authoring view; single-click works in Power BI Service, or use bottom page tabs in Desktop).

## Requirements checklist

| Requirement | Status |
| --- | --- |
| 30,000+ rows | 55,692 |
| 10+ meaningful columns | 46 |
| Public data + source URL | World Bank, CC BY 4.0 |
| 5 analytical questions | Included |
| 5 KPIs | Included |
| 3 business decisions | Included |
| 8+ Power Query transformations | 10 transformations (4 M scripts) |
| 3+ related tables + date table | 4 tables |
| 8+ DAX measures + time intelligence | 15 measures |
| 4 pages + 12+ visuals | 4 pages, 46 PBIR visuals (16 + 10 + 10 + 10) |
| Slicers, cross-filtering, tooltips, navigation | Included |
| 5 findings + 5 recommendations + limitations | Included |
| GitHub repo + PBIP + PDF + slides | Included |

## Analytical questions

1. Which Kenyan counties experienced the highest 12-month food price inflation over the last three years (2024 to 2026)?
2. Which commodity contributes most to movements in the overall food price index?
3. Is monthly price volatility higher in arid and semi-arid (ASAL) counties than in agricultural and urban counties?
4. What seasonal price cycles repeat across the year, and how do peak months differ between staple crops and livestock?
5. How uneven is market coverage across counties, and where are raw field survey gaps largest?

## Key performance indicators

| KPI | Definition |
| --- | --- |
| National Food Price Index | Market-month deduplicated mean of `c_food_price_index` across active filters |
| YoY Inflation Rate | Percentage change in the composite food price index versus the same period 12 months earlier |
| Price Volatility (KES) / CV % | Sample standard deviation (KES) and unit-safe coefficient of variation (%) of monthly closing prices per commodity |
| Data Completeness % / Survey Coverage Rate % | 100.00% expected grid completeness on modeled closing prices versus 4.49% backed by raw field spot observations |
| Affordability Gap (KES) | Unit-safe difference per commodity between a county's average closing price and the national commodity mean |

## Business decisions supported

1. Where to deploy price-monitoring resources: Counties with high maize volatility and low survey coverage need field monitoring investment.
2. When to trigger subsidy programs: Seasonal peaks identify the highest-risk windows for targeted food-security transfers.
3. Which commodity to prioritize: Decouple maize and bean alerts from the composite index because goat prices account for 99.99% of composite index variance.

## Power Query transformations

| # | Operation | Justification |
| --- | --- | --- |
| 1 | Parse `price_date` to proper Date type and build `date_key` | Source stores dates as text; typed Date and integer keys enable time intelligence |
| 2 | Derive `year`, `month`, `month_name`, `year_month`, `quarter`, and `season` | Builds Kenyan agricultural season windows for `dim_date` |
| 3 | Remove `Market Average` aggregate rows and all-null price rows | Excludes pre-aggregated national rows with missing coordinates from physical market analysis |
| 4 | Map `adm1_name` (region) and standardize `adm2_name` (county) labels plus `county_group` | Source mixes provinces and counties across 35 unique admin pairs across 233 physical markets, plus 1 Market Average aggregate pair |
| 5 | Unpivot commodity OHLC, spot, inflation, and trust columns to long format | Builds normalized `fact_prices` star-schema grain (`166,362` rows) |
| 6 | Map raw codes to `Beans (1 kg)`, `Maize (1 kg)`, and `Goat (1 head)` | Replaces machine column names with consistent display labels |
| 7 | Add `category` and `unit` columns to `dim_commodity` | Separates per-kilogram grains and legumes from per-head livestock |
| 8 | Calculate `price_change_mom` and `price_change_mom_pct` per `(mkt_id, commodity_id)` | Tracks short-term monthly price changes without cross-series leakage |
| 9 | Flag statistical outliers (`is_outlier`) | Flags extreme spikes (`|MoM%| > 50` or `|z| > 3` on `1,866` rows / `1.12%`) while keeping all 238 monthly periods continuous |
| 10 | Add `is_recent` and `is_last_36m` flags on `dim_date` | Supports 12-month and 36-month period slicing alongside full history |

## Findings

1. **Finding 1 (Q1): Regional YoY Food Price Resurgence:** While annual index averages show the decline from the 2023 livestock price peak (2023 mean 3.465 vs. 1.744 in 2025), 12-month National Food Price Index inflation (2025-11-01 to 2026-10-01) rose 7.56%. Tharaka Nithi (+25.13%), Marsabit (+19.85%), and Kisumu (+18.43%) recorded the largest county increases (Page 1 Top 10 YoY Bar Chart, [YoY Inflation %]).
2. **Finding 2 (Q2): Composite Index Co-Moves With Goats Over Staples:** Although the source components label assigns Goat (1 head) weight 0, monthly closing prices for Goat (1 head) explain 99.99% of c_food_price_index variance across 55,454 physical market-months (r = 0.99996), versus 47.83% for Beans and 19.34% for Maize. Over the latest 12 months, Maize fell 10.51% (to 80.13 KES/kg) while Goats rose +7.77% (to 5,438.29 KES/head) (Page 1 Commodity Matrix, [Commodity YoY Inflation %]).
3. **Finding 3 (Q3): Structural ASAL Maize Price Premium and Dispersion:** ASAL markets (202 markets in 16 counties) show higher CV on the Food Index (83.70% vs. 77.28%), Maize (40.21% vs. 38.52%), and Goats (85.64% vs. 78.82%), higher outlier rates (1.14% vs. 1.03%), and +9.75 KES/kg higher maize prices than Agricultural & Urban markets (31 markets), while Beans CV is slightly lower in ASAL (30.82% vs. 31.89%). Relative to the national mean (56.02 KES/kg), Turkana (+15.26 KES/kg) and Mandera (+10.65 KES/kg) carry the largest maize premiums, compared to Lamu (-17.51 KES/kg) (Page 2 Gap Bar Chart & Grouped Bars, [Affordability Gap (KES)]).
4. **Finding 4 (Q4): Inverse Crop vs. Livestock Seasonal Price Cycles:** Staple crops and livestock follow inverse annual cycles across 238 months. Maize (1.023) and Beans (1.013) reach seasonal highs during Cool Dry / Harvest (Jun-Sep) as prior-season stocks tighten before main harvests and hit annual lows during Hot Dry / Lean (Jan-Feb) (0.972 and 0.970), when Goat prices peak at 1.060 before falling to 0.968 in Jun-Sep (Page 3 Seasonal Cycle, [Seasonal Index]).
5. **Finding 5 (Q5): Uneven County Coverage and High-Risk Field Survey Gaps:** Modeled OHLC series populate 100.00% of the 233 x 238 x 3 grid (166,362 rows), yet raw field surveys cover 4.49% of records and omit Western Province (27 of 47 counties covered). Five counties rely on one market, while Samburu (20 markets, 0.00% survey coverage), Kisumu (0.00% coverage, +18.43% YoY on Page 1), and Garissa (21 markets, 3.85% all-commodity coverage on the sub-5% bar chart) fall in the blind-spot quadrant (Page 4 Priority Quadrant & Low-Survey Bar Chart, [Survey Coverage Rate %]).

## Recommendations

1. **Recommendation 1: Decouple Grain Price Tracking From the Composite Index:** County food-security dashboards should alert on commodity-specific [Commodity YoY Inflation %] and [Avg Price (KES)] for Maize (1 kg) and Beans (1 kg) alongside [National Food Price Index], because raw index shifts reflect 99.99% co-movement with Goat (1 head) prices.
2. **Recommendation 2: Deploy Field Price Audits to Zero-Survey High-Risk Counties:** Assign county agricultural enumerators first to Samburu (20 markets, 0.00% raw survey coverage), Kisumu (0.00% coverage, +18.43% YoY), and large northern ASAL clusters (Turkana at 1.96%, Marsabit at 3.00%, and Garissa at 3.85%) to raise [Survey Coverage Rate %] above the 5% blind-spot threshold.
3. **Recommendation 3: Pre-Position Grain Buffers Ahead of June-to-September Peaks:** Trigger county maize and bean strategic reserve releases in May before the Cool Dry / Harvest (Jun-Sep) seasonal price peak (1.023 maize index, 1.013 beans index), and schedule livestock offtake or pastoral support for Jan-Feb (1.060 goat peak).
4. **Recommendation 4: Target Staple Grain Logistics Using Affordability Gaps:** Direct maize transport and price-stabilization support toward chronic high-price counties with the largest positive [Affordability Gap (KES)], including Turkana (+15.26 KES/kg), Mandera (+10.65 KES/kg), and Kisumu (+9.89 KES/kg), and build trade links with nearby lower-price agricultural markets such as Kitui (-15.59 KES/kg).
5. **Recommendation 5: Expand Market Coverage to Unmonitored Counties:** Partner with the Kenya National Bureau of Statistics (KNBS) and county trade offices to add physical monitoring sites across the 20 unrepresented counties (including Western Province) and single-market counties (Embu, Lamu, Machakos, Nyeri, Uasin Gishu) so future World Bank RTFP releases cover all 47 Kenyan counties.

## Dashboard preview

All four report pages (300 DPI) and the star schema diagram are saved in the repository:

* Star Schema Model: [docs/model-diagram.png](docs/model-diagram.png)
* Page 1 Executive Pulse: [screenshots/page1-executive-pulse.png](screenshots/page1-executive-pulse.png)
* Page 2 County and Commodity: [screenshots/page2-county-commodity.png](screenshots/page2-county-commodity.png)
* Page 3 Trends and Diagnostics: [screenshots/page3-trends-diagnostics.png](screenshots/page3-trends-diagnostics.png)
* Page 4 Decisions and Action: [screenshots/page4-decisions-action.png](screenshots/page4-decisions-action.png)

## Limitations

* Data consists of market-level retail prices without household income or expenditure surveys; affordability gaps measure cross-county price differences rather than income-to-cost ratios.
* The 233 physical markets cover 27 of Kenya's 47 counties unevenly. Turkana has 57 monitored markets, Garissa has 21, Samburu has 20, and Marsabit has 19, while five counties have 1 market each and Western Province has no markets in this release.
* The dataset ends in October 2026; analyses covering later months require refreshing the source CSV.
* The food price index is a composite measure that moves closely with goat prices (`r = 0.99996`), masking individual staple crop trends unless filtered by commodity.

## Reproduction

### Prerequisites

* Microsoft Power BI Desktop (free)
* Python 3.12+ managed with `uv` (optional, for validation and report generation)
* Git

### Steps

1. Clone this repository:
```bash
git clone https://github.com/princenzmw/mzigo-chakula.git
```

2. Verify or place the raw World Bank RTFP CSV (tracked under `data/raw/` for reproduction, or downloadable from `https://microdata.worldbank.org/index.php/catalog/6167`):
* Save as `data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv`.

3. Open the Power BI Project (`pbip/mzigo-chakula.pbip`) in Microsoft Power BI Desktop:
```powershell
start pbip/mzigo-chakula.pbip
```
* The semantic model loads all Power Query M partitions, star-schema relationships, and 15 DAX measures from `pbip/mzigo-chakula.SemanticModel/`.
* Optionally run validation tests with `uv sync` and `uv run pytest -v`, or regenerate reports via `uv run python -m mzigo_chakula.generate_week5_deliverables`.

4. Verify the model and visuals:
* Open Model View to confirm all four tables and single-direction relationships.
* Open Report View to confirm that pages and visuals render cleanly.
* Hold `Ctrl + Click` on any top header navigation pill to switch pages inside Power BI Desktop (single-click works directly in Power BI Service, or click the bottom page tabs in Desktop).

5. Check DAX measures:
* Open Report View or DAX Query View to confirm that measure outputs match `docs/dax-catalogue.md`.

### Folder structure

```text
mzigo-chakula/
├── README.md
├── pyproject.toml
├── uv.lock
├── pbip/
│   ├── mzigo-chakula.pbip               (local .pbix exports under pbip/ stay untracked)
│   ├── mzigo-chakula.Report/            (PBIR 4-page layout, 46 visuals, theme)
│   └── mzigo-chakula.SemanticModel/     (TMDL tables, relationships, 15 DAX measures)
├── powerquery/
│   ├── dim_commodity.pq
│   ├── dim_date.pq
│   ├── dim_markets.pq
│   └── fact_prices.pq
├── src/mzigo_chakula/
│   ├── __init__.py
│   ├── data.py
│   ├── etl.py
│   ├── dax_validator.py
│   ├── generate_pbir_visuals.py
│   ├── generate_week1_docs.py
│   ├── generate_week2_deliverables.py
│   ├── generate_week3_deliverables.py
│   ├── generate_week4_deliverables.py
│   └── generate_week5_deliverables.py
├── tests/
│   ├── conftest.py
│   ├── test_data.py
│   ├── test_etl.py
│   ├── test_dax_validator.py
│   ├── test_generate_week1_docs.py
│   ├── test_week4_deliverables.py
│   └── test_week5_deliverables.py
├── data/
│   ├── raw/
│   │   └── KEN_RTFP_mkt_2007_2026-10-05.csv
│   └── processed/
│       ├── dim_commodity.csv
│       ├── dim_date.csv
│       └── dim_markets.csv
├── docs/
│   ├── proposal.md
│   ├── proposal.pdf
│   ├── dataset-dictionary.csv
│   ├── data-quality-profile.md
│   ├── transformation-log.md
│   ├── dax-catalogue.md
│   ├── model-diagram.png
│   ├── usability-and-insights.md
│   ├── report.md
│   └── report.pdf
├── screenshots/
│   ├── week1-initial-import.png
│   ├── week2-powerquery-cleaning.png
│   ├── week3-powerbi-model-view.png
│   ├── week3-dax-validation.png
│   ├── page1-executive-pulse.png
│   ├── page2-county-commodity.png
│   ├── page3-trends-diagnostics.png
│   └── page4-decisions-action.png
├── output/
│   ├── week2-powerquery-cleaning.png
│   ├── week3-powerbi-model-view.png
│   ├── week3-dax-validation.png
│   ├── page1-executive-pulse.png
│   ├── page2-county-commodity.png
│   ├── page3-trends-diagnostics.png
│   └── page4-decisions-action.png
├── slides/
│   └── presentation.pptx
└── contribution/
    └── contribution-matrix.md
```

## Contributors

Two-member group (`Prince Nzamuwe` and `Yizere Denis Derick`). Yizere Denis Derick notified the course lecturer of a medical situation during execution; his contributions are documented below and in [contribution/contribution-matrix.md](contribution/contribution-matrix.md).

| Member | Role | Key Contributions |
| --- | --- | --- |
| Prince Nzamuwe | Lead Analyst & BI Architect | Dataset audit, 4 Power Query M scripts, star schema model, 15 DAX measures, Python test suite, 4-page 46-visual Power BI report, 12-page PDF report, 12-slide presentation |
| Yizere Denis Derick | Group Contributor | Problem framing alignment, stakeholder and operational decision specification, analytical question review, deliverable checklist verification |

## References

* Data source: World Bank. (2026). Real Time Food Prices (RTFP), Kenya. Microdata Library (`https://microdata.worldbank.org/index.php/catalog/6167`). Retrieved 29 October 2026.
* Contextual Kenya policy references: Kenya National Bureau of Statistics (KNBS) Consumer Price Index; Central Bank of Kenya (CBK) Monetary Policy Statement.

## License

This project is licensed under the MIT License.

The underlying data is licensed by the World Bank under CC BY 4.0. Attribution: Data sourced from the World Bank Real Time Food Prices project.