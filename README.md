# Mzigo Chakula

### Food price inflation and household affordability intelligence in Kenya from 2007 to 2026

> *Mzigo* (Swahili): burden, load, weight. *Chakula*: food.
> "The weight of food": what does a kilo of maize, a kilo of beans, or a goat actually cost a Kenyan household, and where is that weight heaviest?

DSA 3050A | Business intelligence and data visualization | Group project B

## Problem statement

Food prices in Kenya have risen sharply over the past two decades alongside currency depreciation, drought cycles, and transport costs. National inflation reports usually summarize food costs as a single headline rate, which hides sharp regional differences across counties. A household in Turkana faces a different price trajectory than one in Nairobi or Mombasa because staple availability, seasonal timing, and local market volatility differ by region.

This project builds a decision-ready Power BI solution that answers:

> **Which counties, commodities, and time periods carry the heaviest food-price burden, and where should intervention be prioritized?**

Primary audience: County government planners, NGO food-security programs, and household-level policy advisors.

## Dataset

| Attribute | Detail |
| --- | --- |
| Source | World Bank Real Time Food Prices (RTFP), Kenya |
| URL | microdata.worldbank.org/index.php/catalog/6167 |
| Date accessed | 29 October 2026 |
| License | CC BY 4.0 (open, free redistribution) |
| Rows | 55,692 |
| Columns | 46 |
| Geographic coverage | 233 physical markets (+ 1 national average series) across 27 counties |
| Time span | January 2007 to October 2026 (19 years, monthly) |
| Key fields | adm1_name (region/province), adm2_name (county), mkt_name, price_date, year, month, c_beans, c_maize_fao, c_livestock_goat_s_fao, c_food_price_index, inflation_food_price_index, lat, lon |

Ethical note: All data is publicly available aggregate market-level prices. No personal or sensitive data is used.

## Data model

```text
┌─────────────────────┐         ┌─────────────────────┐
│     dim_markets     │         │      dim_date       │
├─────────────────────┤         ├─────────────────────┤
│ mkt_id (PK)         │◄──┐     │ date_key (PK)       │
│ mkt_name            │   │     │ full_date           │
│ adm1_name (region)  │   │     │ year                │
│ adm2_name (county)  │   │     │ month               │
│ lat                 │   │     │ quarter             │
│ lon                 │   │     │ season              │
└─────────────────────┘   │     │ is_recent (12mo)    │
                          │     └─────────────────────┘
                          │                ▲
                          │                │
                          │           1:*  │
                          │                │
┌─────────────────────┐   │                │
│    dim_commodity    │   │                │
├─────────────────────┤   │                │
│ commodity_id (PK)   │   │                │
│ commodity_name      │   │                │
│ category (staple/   │   │                │
│   legume/livestock) │   │                │
│ unit (KG / unit)    │   │                │
└─────────────────────┘   │                │
                          │                │
┌─────────────────────────┴──────────────┴──────────────┐
│                     fact_prices                       │
├───────────────────────────────────────────────────────┤
│ price_id (PK)                                         │
│ mkt_id (FK → dim_markets)                             │
│ date_key (FK → dim_date)                              │
│ commodity_id (FK → dim_commodity)                     │
│ price_value (KSh)                                     │
│ food_price_index                                      │
│ inflation_food_price_index                            │
│ trust_score                                           │
└───────────────────────────────────────────────────────┘

```

Cardinality: All relationships are 1:* (one market to many price records; one date to many price records; one commodity to many price records).

Filter direction: Single direction from dimensions to fact table. No bidirectional filters.

## DAX measures

| # | Measure | Formula (simplified) | Purpose |
| --- | --- | --- | --- |
| 1 | Avg Price | AVERAGE(fact_prices[price_value]) | Baseline cost |
| 2 | YoY Inflation % | DIVIDE([Current Period], [Prior Year Period], 0) - 1 | Year-over-year change |
| 3 | MoM Change % | DIVIDE([Current Month], [Prior Month], 0) - 1 | Month-over-month trend |
| 4 | Price Volatility | STDEV.S(fact_prices[price_value]) | Risk indicator |
| 5 | Cumulative Index | TOTALYTD(fact_prices[food_price_index], dim_date[full_date]) | Running cost burden |
| 6 | County Rank | RANKX(ALL(dim_markets[adm2_name]), [YoY Inflation %]) | Worst counties first |
| 7 | Data Completeness % | DIVIDE(COUNTROWS(fact_prices), [Expected Rows], 0) | Quality indicator |
| 8 | Affordability Gap | [Avg Price] - AVERAGEX(ALL(dim_markets[adm2_name]), [Avg Price]) | Comparison to national mean |
| 9 | Seasonal Index | DIVIDE([Current Month], AVERAGE([Month Average]), 0) | Seasonality pattern |
| 10 | 12-Month Rolling Avg | AVERAGEX(DATESINPERIOD(dim_date[full_date], MAX(dim_date[full_date]), -12, MONTH), [Avg Price]) | Smoothed trend |

## Dashboard pages

| Page | Purpose | Key Visuals |
| --- | --- | --- |
| 1. Executive Pulse | Rapid situational awareness | KPI cards (national food index, YoY inflation, worst county, most volatile commodity), national trend line, exception alerts, county slicer |
| 2. County and Commodity | Where and what | County heatmap (inflation by county), commodity bar chart (avg price by category), market scatter (lat/lon + price), drill-through to district |
| 3. Trends and Diagnostics | Why and when | 19-year trend with seasonality, YoY comparison (current versus prior), volatility ranking, anomaly callouts, drill-through to single market |
| 4. Decisions and Action | What to do | Top 10 risk counties (ranked), intervention priority matrix, recommendation cards, data gaps map, limitations note |

Interactions: Slicers (county, commodity category, year range, season), cross-filtering between all visuals, drill-through from county to district to market, tooltips showing exact values and percentage change, navigation buttons between pages.

## Requirements checklist

| Requirement | Status |
| --- | --- |
| 30,000+ rows | 55,692 |
| 10+ meaningful columns | 46 |
| Genuine public data + source URL | World Bank, CC BY 4.0 |
| 5 analytical questions | Included |
| 5 KPIs | Included |
| 3 business decisions | Included |
| 8+ Power Query transformations | Included |
| 3+ related tables + date table | 4 tables |
| 8+ DAX measures + time intelligence | 10 measures |
| 4 pages + 12+ visuals | 4 pages, ~16 visuals |
| Slicers, cross-filtering, drill-through, tooltips | Included |
| 5 findings + 5 recommendations + limitations | Included |
| GitHub repo + .pbix + PDF + slides | Included |

## Analytical questions

1. Which counties experienced the highest 12-month food price inflation in the last 3 years?
2. Which commodity contributes most to the overall food price index?
3. Is price volatility significantly higher in arid and semi-arid counties compared to high-potential agricultural counties?
4. What seasonal patterns exist in food prices, and do they differ by county?
5. Which markets have the most incomplete data, and does this correlate with geographic remoteness?

## Key performance indicators

| KPI | Definition |
| --- | --- |
| National Food Price Index | Average of c_food_price_index across all markets for the selected period |
| YoY Inflation Rate | Percentage change in food price index versus same period prior year |
| Price Volatility | Standard deviation of monthly price changes per commodity and per county |
| Market Coverage Rate | Percentage of expected market-month observations with non-null price data |
| Affordability Gap | Difference between a county's average food price and the national average |

## Business decisions supported

1. Where to deploy price-monitoring resources: Counties with high volatility and low data coverage need both intervention and monitoring investment.
2. When to trigger subsidy programs: Seasonal peaks identify the highest-risk windows for targeted intervention.
3. Which commodity to prioritize: If maize drives the majority of the index, maize-specific interventions have outsized impact compared to broad-based measures.

## Power query transformations

| # | Operation | Justification |
| --- | --- | --- |
| 1 | Parse price_date to proper Date type | Source stores as text; needed for time intelligence |
| 2 | Derive year, month, quarter, and season columns | Required for dim_date and DAX time intelligence |
| 3 | Remove rows where all price columns are null or mkt_name is "Market Average" | Removes empty rows and excludes pre-aggregated national rows from market-level fact records |
| 4 | Map adm1_name (region) and standardize adm2_name (county) names | Source mixes former provinces and counties across adm1_name and adm2_name (35 unique pairs across 233 markets + Market Average) |
| 5 | Unpivot commodity price columns to long format | Required for star schema |
| 6 | Rename commodity columns to human-readable names | c_maize_fao to Maize (FAO) |
| 7 | Add commodity_category column | Enables category-level analysis |
| 8 | Calculate price_change_mom | Derived field for volatility analysis |
| 9 | Filter outliers | Remove data entry errors |
| 10 | Add is_recent flag | Enables current situation versus historical views |

## Findings

1. **Finding 1 (Q1): Regional YoY Food Price Resurgence:** While multi-year index averages reflect the steep decline from the 2023 livestock price spike (mean 3.465 vs. 1.744 in 2025), recent 12-month National Food Price Index inflation (2025-11-01 to 2026-10-01) rebounded to +7.56%. Tharaka Nithi (+25.13%), Marsabit (+19.85%), and Kisumu (+18.43%) posted the sharpest local increases (Page 1 Top 10 YoY Bar Chart, [YoY Inflation %]).
2. **Finding 2 (Q2): Composite Index Co-Moves With Goats Over Staples:** Although the source components label assigns Goat (1 head) weight 0, live goat close prices explain 99.99% of c_food_price_index variance across 55,454 physical market-months (r = 0.99996), versus 47.83% for Beans and 19.34% for Maize. In the latest 12 months, Maize fell -10.51% (80.13 KES/kg) while Goats rose +7.77% (5,438.29 KES/head) (Page 1 Commodity Matrix, [Commodity YoY Inflation %]).
3. **Finding 3 (Q3): Structural ASAL Maize Price Premium and Dispersion:** ASAL markets (202 markets in 16 counties) exhibit higher Food Index CV (83.70% vs. 77.28%), higher Maize CV (40.21% vs. 38.52%), higher Goat CV (85.64% vs. 78.82%), higher outlier rates (1.14% vs. 1.03%), and +9.75 KES/kg higher maize prices than Agricultural & Urban markets (31 markets). Turkana (+15.26 KES/kg) and Mandera (+10.65 KES/kg) carry the heaviest chronic maize premiums against Lamu (-17.51 KES/kg) (Page 2 Gap Bar Chart & Grouped Bars, [Affordability Gap (KES)]).
4. **Finding 4 (Q4): Inverse Crop vs. Livestock Seasonal Price Cycles:** Dry grains and livestock follow opposite annual cycles across 238 months. Maize (1.023) and Beans (1.013) reach seasonal highs during Cool Dry / Harvest (Jun-Sep) pre-harvest depletion and trough during Hot Dry / Lean (Jan-Feb) (0.972 and 0.970), when Goat prices peak at 1.060 before troughing at 0.968 (Page 3 Seasonal Cycle, [Seasonal Index]).
5. **Finding 5 (Q5): Uneven County Coverage and High-Risk Field Survey Gaps:** Modelled OHLC series populate 100.00% of the 233 x 238 x 3 grid (166,362 rows), yet actual field surveys cover only 4.49% of records and omit Western Province completely (27 of 47 counties covered). Five counties rely on one market, while Samburu (20 markets, 0.00% survey coverage), Kisumu (0.00% coverage, +18.43% YoY), and Garissa (21 markets, 3.85% coverage) occupy the monitoring blind-spot quadrant (Page 4 Priority Matrix, [Survey Coverage Rate %]).

## Recommendations

1. **Recommendation 1: Decouple Grain Price Tracking From the Composite Index:** County food-security dashboards should alert on commodity-specific [Commodity YoY Inflation %] and [Avg Price (KES)] for Maize (1 kg) and Beans (1 kg) alongside [National Food Price Index], because raw index shifts reflect 99.99% co-movement with Goat (1 head) prices.
2. **Recommendation 2: Deploy Emergency Price Audits to Zero-Survey High-Risk Counties:** Assign county agricultural enumerators first to Samburu (20 markets, 0.00% raw survey coverage), Kisumu (0.00% coverage, +18.43% YoY surge), and large northern ASAL clusters (Turkana at 1.96%, Marsabit at 3.00%, and Garissa at 3.85% coverage) to raise [Survey Coverage Rate %] above 10% across blind-spot corridors.
3. **Recommendation 3: Pre-Position Grain Buffers Ahead of June-to-September Peaks:** Trigger county maize and bean strategic reserve releases in May before the Cool Dry / Harvest (Jun-Sep) seasonal price peak (1.023 maize index, 1.013 beans index), and schedule livestock offtake or pastoral support for Jan-Feb (1.060 goat peak).
4. **Recommendation 4: Target ASAL Transport Subsidies Using Affordability Gaps:** Direct staple grain logistics support toward chronic net-deficit markets with the largest positive [Affordability Gap (KES)], specifically Turkana (+15.26 KES/kg), Mandera (+10.65 KES/kg), and Kisumu (+9.89 KES/kg), paired with market linkages from surplus hubs like Lamu (-17.51 KES/kg) and Kitui (-15.59 KES/kg).
5. **Recommendation 5: Expand Market Instrumentation Into Western Kenya Counties:** Partner with KNBS and county trade offices to onboard physical market monitoring sites across Western Province and single-market counties (Embu, Lamu, Machakos, Nyeri, Uasin Gishu) so future RTFP releases reflect all 47 Kenyan counties.

## Dashboard preview

All four report pages (300 DPI) and the star schema diagram are saved in the repository:

* Star Schema Model: [docs/model-diagram.png](docs/model-diagram.png)
* Page 1 Executive Pulse: [screenshots/page1-executive-pulse.png](screenshots/page1-executive-pulse.png)
* Page 2 County and Commodity: [screenshots/page2-county-commodity.png](screenshots/page2-county-commodity.png)
* Page 3 Trends and Diagnostics: [screenshots/page3-trends-diagnostics.png](screenshots/page3-trends-diagnostics.png)
* Page 4 Decisions and Action: [screenshots/page4-decisions-action.png](screenshots/page4-decisions-action.png)

## Limitations

* Data consists of market-level retail prices without household income or expenditure surveys. Affordability is inferred from regional price levels and cross-county price gaps.
* The 233 physical markets cover 27 of Kenya's 47 counties unevenly. Turkana has 57 monitored markets, Garissa has 21, Samburu has 20, and Marsabit has 19, while five counties have 1 market each and Western Province has no markets in this release.
* The dataset ends in October 2026. Recent events may not be fully captured.
* Food price index is a composite measure that masks individual commodity movements.
* No income data is included. Affordability gap is a price comparison rather than a true income-to-cost ratio.

## Reproduction

### Prerequisites

* Microsoft Power BI Desktop (free)
* Python 3.10+ (optional, for data profiling)
* Git

### Steps

1. Clone this repo:
```bash
git clone https://github.com/princenzmw/mzigo-chakula.git

```


2. Download the dataset:
* Go to microdata.worldbank.org/index.php/catalog/6167
* Click Get Microdata to download the Kenya CSV
* Place it in data/raw/KEN_RTFP_mkt_2007_2026-10-05.csv


3. Open the Power BI Project (`pbip/mzigo-chakula.pbip`) in Microsoft Power BI Desktop:
```bash
start pbip/mzigo-chakula.pbip
```
* The semantic model loads all Power Query M partitions, star-schema relationships, and 15 DAX measures from `pbip/mzigo-chakula.SemanticModel/`.
* Optionally run full Python validation and regenerate documentation via `uv sync` and `uv run pytest -v`.


4. Verify the model:
* Go to Model View to confirm tables and relationships.
* Go to Report View to confirm pages and visuals rendering.


5. Check DAX measures:
* Go to Data View to confirm measures calculate correctly.



### Folder structure

```text
mzigo-chakula/
├── README.md
├── mzigo-chakula.pbix
├── data/
│   ├── raw/
│   │   └── KEN_RTFP_mkt_2007_2026-10-05.csv
│   └── processed/
│       └── (generated by Power Query)
├── docs/
│   ├── proposal.md
│   ├── proposal.pdf
│   ├── dataset-dictionary.csv
│   ├── data-quality-profile.md
│   ├── report.pdf
│   ├── transformation-log.md
│   ├── dax-catalogue.md
│   └── model-diagram.png
├── slides/
│   └── presentation.pptx
├── screenshots/
│   ├── page1-executive-pulse.png
│   ├── page2-county-commodity.png
│   ├── page3-trends-diagnostics.png
│   └── page4-decisions-action.png
└── contribution/
    └── contribution-matrix.md

```

## Contributors

| Member | Role | Key Contributions |
| --- | --- | --- |
| Prince Nzamuwe | Lead Analyst & Architect | Data profiling, Power Query ETL, star schema, DAX measures, Power BI report |
| Yizere Denis Derick | Group Contributor | Problem framing, stakeholder alignment, requirement review |

## References

* World Bank. (2026). Real Time Food Prices (RTFP), Kenya. Microdata Library. Retrieved 29 October 2026.
* KNBS. (2025). Consumer Price Index, Kenya. National Bureau of Statistics.
* CBK. (2026). Monetary Policy Statement. Central Bank of Kenya.

## License

This project is licensed under the MIT License.

The underlying data is licensed by the World Bank under CC BY 4.0. Attribution: Data sourced from the World Bank Real Time Food Prices project.