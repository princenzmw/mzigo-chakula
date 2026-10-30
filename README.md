# Mzigo Chakula

### Food price inflation and household affordability intelligence in Kenya from 2007 to 2026

> *Mzigo* (Swahili): burden, load, weight. *Chakula*: food.
> "The weight of food" — what does a loaf of bread, a kilo of maize, or a litre of cooking oil actually cost a Kenyan household, and where is that weight heaviest?

DSA 3050A | Business intelligence and data visualization | Group project B

## Problem statement

Food prices in Kenya have risen sharply over the past decade, driven by currency depreciation, climate shocks, supply chain disruptions, and inflation. Yet most public discourse treats food inflation as a single national number. In reality, a household in Turkana experiences a fundamentally different food-price trajectory than one in Nairobi or Mombasa, involving different commodities, different seasonal patterns, and different volatility.

This project builds a decision-ready Power BI solution that answers:

> **Which counties, commodities, and time periods carry the heaviest food-price burden, and where should intervention be prioritized?**

Primary audience: County government planners, NGO food-security programs, and household-level policy advisors.

## Dataset

| Attribute | Detail |
| --- | --- |
| Source | World Bank Real Time Food Prices (RTFP) — Kenya |
| URL | microdata.worldbank.org/index.php/catalog/6167 |
| Date accessed | 29 October 2026 |
| License | CC BY 4.0 (open, free redistribution) |
| Rows | 55,692 |
| Columns | 46 |
| Geographic coverage | 234 markets across all 47 counties |
| Time span | January 2007 to October 2026 (19 years, monthly) |
| Key fields | adm1_name (county), adm2_name (district), mkt_name, price_date, year, month, c_beans, c_maize_fao, c_livestock_goat_s_fao, c_food_price_index, inflation_food_price_index, lat, lon |

Ethical note: All data is publicly available aggregate market-level prices. No personal or sensitive data is used.

## Data model

```text
┌─────────────────────┐         ┌─────────────────────┐
│     dim_markets     │         │      dim_date       │
├─────────────────────┤         ├─────────────────────┤
│ mkt_id (PK)         │◄──┐     │ date_key (PK)       │
│ mkt_name            │   │     │ full_date           │
│ adm1_name (county)  │   │     │ year                │
│ adm2_name (district)│   │     │ month               │
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
│   protein/dairy/    │   │                │
│   oil)              │   │                │
│ unit                │   │                │
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
| 6 | County Rank | RANKX(ALL(dim_markets[adm1_name]), [YoY Inflation %]) | Worst counties first |
| 7 | Data Completeness % | DIVIDE(COUNTROWS(fact_prices), [Expected Rows], 0) | Quality indicator |
| 8 | Affordability Gap | [Avg Price] - AVERAGEX(ALL(dim_markets[adm1_name]), [Avg Price]) | Comparison to national mean |
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
| 3 | Remove rows where all price columns are null | Removes rows with no usable data |
| 4 | Standardize county names | Source has inconsistent formatting |
| 5 | Unpivot commodity price columns to long format | Required for star schema |
| 6 | Rename commodity columns to human-readable names | c_maize_fao to Maize (FAO) |
| 7 | Add commodity_category column | Enables category-level analysis |
| 8 | Calculate price_change_mom | Derived field for volatility analysis |
| 9 | Filter outliers | Remove data entry errors |
| 10 | Add is_recent flag | Enables current situation versus historical views |

## Findings

> This section will be populated with evidence-backed findings from the final analysis. Each finding will cite the specific visual, measure, and data slice that supports it.

1. [TBD]
2. [TBD]
3. [TBD]
4. [TBD]
5. [TBD]

## Recommendations

> Each recommendation will be tied to a specific finding and framed as an actionable step for the target audience.

1. [TBD]
2. [TBD]
3. [TBD]
4. [TBD]
5. [TBD]

## Limitations

* Data consists of market-level aggregate prices, not household expenditure. It shows what food costs, not what households earn. Affordability is inferred rather than directly measured.
* The 234 markets do not cover all 47 counties equally. Some arid counties have few markets while Nairobi has many.
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
* Place it in data/raw/kenya_rtfp.csv


3. Open the Power BI file:
```text
open mzigo-chakula.pbix

```


* Power BI will prompt to refresh data. Point it to data/raw/kenya_rtfp.csv.
* All Power Query transformations will replay automatically.


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
| Prince Nzamuwe | Lead Analyst | Data acquisition, Power Query, DAX, model design |
| [Name] | [Role] | [Contributions] |
| [Name] | [Role] | [Contributions] |

## References

* World Bank. (2026). Real Time Food Prices (RTFP) — Kenya. Microdata Library. Retrieved 29 October 2026.
* KNBS. (2025). Consumer Price Index — Kenya. National Bureau of Statistics.
* CBK. (2026). Monetary Policy Statement. Central Bank of Kenya.

## License

This project is licensed under the MIT License.

The underlying data is licensed by the World Bank under CC BY 4.0. Attribution: Data sourced from the World Bank Real Time Food Prices project.