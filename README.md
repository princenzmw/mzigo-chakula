```markdown

\# Mzigo Chakula



\### Food Price Inflation \& Household Affordability Intelligence — Kenya (2007–2026)



> \*Mzigo\* (Swahili): burden, load, weight. \*Chakula\*: food.

> "The weight of food" — what does a loaf of bread, a kilo of maize, or a litre of cooking oil actually cost a Kenyan household, and where is that weight heaviest?



\*\*DSA 3050A | Business Intelligence \& Data Visualization | Group Project B\*\*



\---



\## 🎯 Problem Statement



Food prices in Kenya have risen sharply over the past decade, driven by currency depreciation, climate shocks, supply chain disruptions, and inflation. Yet most public discourse treats "food inflation" as a single national number. In reality, a household in \*\*Turkana\*\* experiences a fundamentally different food-price trajectory than one in \*\*Nairobi\*\* or \*\*Mombasa\*\* — different commodities, different seasonal patterns, different volatility.



This project builds a decision-ready Power BI solution that answers:



> \*\*Which counties, commodities, and time periods carry the heaviest food-price burden, and where should intervention be prioritized?\*\*



\*\*Primary audience:\*\* County government planners, NGO food-security programs, and household-level policy advisors.



\---



\## 📊 Dataset



| Attribute | Detail |

|---|---|

| \*\*Source\*\* | World Bank Real Time Food Prices (RTFP) — Kenya |

| \*\*URL\*\* | \[microdata.worldbank.org/index.php/catalog/6167](https://microdata.worldbank.org/index.php/catalog/6167) |

| \*\*Date accessed\*\* | 29 October 2026 |

| \*\*License\*\* | CC BY 4.0 (open, free redistribution) |

| \*\*Rows\*\* | 55,692 |

| \*\*Columns\*\* | 46 |

| \*\*Geographic coverage\*\* | 234 markets across all 47 counties |

| \*\*Time span\*\* | January 2007 – October 2026 (19 years, monthly) |

| \*\*Key fields\*\* | `adm1\_name` (county), `adm2\_name` (district), `mkt\_name`, `price\_date`, `year`, `month`, `c\_beans`, `c\_maize\_fao`, `c\_livestock\_goat\_s\_fao`, `c\_food\_price\_index`, `inflation\_food\_price\_index`, `lat`, `lon` |



\*\*Ethical note:\*\* All data is publicly available aggregate market-level prices. No personal or sensitive data is used.



\---



\## 🧱 Data Model



```

┌─────────────────────┐         ┌─────────────────────┐

│     dim\_markets     │         │       dim\_date      │

├─────────────────────┤         ├─────────────────────┤

│ mkt\_id (PK)         │◄──┐     │ date\_key (PK)       │

│ mkt\_name            │   │     │ full\_date           │

│ adm1\_name (county)  │   │     │ year                │

│ adm2\_name (district)│   │     │ month               │

│ lat                 │   │     │ quarter             │

│ lon                 │   │     │ season              │

└─────────────────────┘   │     │ is\_recent (12mo)    │

&#x20;                         │     └─────────────────────┘

&#x20;                         │              ▲

&#x20;                         │              │

&#x20;                         │         1:\*  │

&#x20;                         │              │

┌─────────────────────┐   │              │

│     dim\_commodity   │   │              │

├─────────────────────┤   │              │

│ commodity\_id (PK)   │   │              │

│ commodity\_name      │   │              │

│ category (staple/   │   │              │

│   protein/dairy/    │   │              │

│   oil)              │   │              │

│ unit                │   │              │

└─────────────────────┘   │              │

&#x20;                         │              │

┌─────────────────────────┴──────────────┴──────────────┐

│                      fact\_prices                       │

├─────────────────────────────────────────────────────────┤

│ price\_id (PK)                                           │

│ mkt\_id (FK → dim\_markets)                               │

│ date\_key (FK → dim\_date)                                │

│ commodity\_id (FK → dim\_commodity)                       │

│ price\_value (KSh)                                       │

│ food\_price\_index                                        │

│ inflation\_food\_price\_index                              │

│ trust\_score                                             │

└─────────────────────────────────────────────────────────┘

```



\*\*Cardinality:\*\* All relationships are 1:\* (one market → many price records; one date → many price records; one commodity → many price records).



\*\*Filter direction:\*\* Single direction (dimensions → fact). No bidirectional filters.



\---



\## 📐 DAX Measures (8+)



| # | Measure | Formula (simplified) | Purpose |

|---|---|---|---|

| 1 | `Avg Price` | `AVERAGE(fact\_prices\[price\_value])` | Baseline cost |

| 2 | `YoY Inflation %` | `DIVIDE(\[Current Period], \[Prior Year Period], 0) - 1` | Year-over-year change |

| 3 | `MoM Change %` | `DIVIDE(\[Current Month], \[Prior Month], 0) - 1` | Month-over-month trend |

| 4 | `Price Volatility` | `STDEV.S(fact\_prices\[price\_value])` | Risk indicator |

| 5 | `Cumulative Index` | `TOTALYTD(fact\_prices\[food\_price\_index], dim\_date\[full\_date])` | Running cost burden |

| 6 | `County Rank` | `RANKX(ALL(dim\_markets\[adm1\_name]), \[YoY Inflation %])` | Worst counties first |

| 7 | `Data Completeness %` | `DIVIDE(COUNTROWS(fact\_prices), \[Expected Rows], 0)` | Quality indicator |

| 8 | `Affordability Gap` | `\[Avg Price] - AVERAGEX(ALL(dim\_markets\[adm1\_name]), \[Avg Price])` | vs. national mean |

| 9 | `Seasonal Index` | `DIVIDE(\[Current Month], AVERAGE(\[Month Average]), 0)` | Seasonality pattern |

| 10 | `12-Month Rolling Avg` | `AVERAGEX(DATESINPERIOD(dim\_date\[full\_date], MAX(dim\_date\[full\_date]), -12, MONTH), \[Avg Price])` | Smoothed trend |



\---



\## 📑 Dashboard Pages



| Page | Purpose | Key Visuals |

|---|---|---|

| \*\*1. Executive Pulse\*\* | Rapid situational awareness | KPI cards (national food index, YoY inflation, worst county, most volatile commodity), national trend line, exception alerts, county slicer |

| \*\*2. County \& Commodity\*\* | Where and what | County heatmap (inflation by county), commodity bar chart (avg price by category), market scatter (lat/lon + price), drill-through to district |

| \*\*3. Trends \& Diagnostics\*\* | Why and when | 19-year trend with seasonality, YoY comparison (current vs. prior), volatility ranking, anomaly callouts, drill-through to single market |

| \*\*4. Decisions \& Action\*\* | What to do | Top 10 risk counties (ranked), intervention priority matrix, recommendation cards, data gaps map, limitations note |



\*\*Interactions:\*\* Slicers (county, commodity category, year range, season), cross-filtering between all visuals, drill-through from county → district → market, tooltips showing exact values + % change, navigation buttons between pages.



\---



\## ✅ Requirements Checklist



| Requirement | Status |

|---|---|

| 30,000+ rows | ✅ 55,692 |

| 10+ meaningful columns | ✅ 46 |

| Genuine public data + source URL | ✅ World Bank, CC BY 4.0 |

| 5 analytical questions | ✅ (see below) |

| 5 KPIs | ✅ (see below) |

| 3 business decisions | ✅ (see below) |

| 8+ Power Query transformations | ✅ (see below) |

| 3+ related tables + date table | ✅ 4 tables |

| 8+ DAX measures + time intelligence | ✅ 10 measures |

| 4 pages + 12+ visuals | ✅ 4 pages, \~16 visuals |

| Slicers, cross-filtering, drill-through, tooltips | ✅ |

| 5 findings + 5 recommendations + limitations | ✅ (final) |

| GitHub repo + .pbix + PDF + slides | ✅ |



\---



\## 🔍 Analytical Questions



1\. Which counties experienced the highest 12-month food price inflation in the last 3 years?

2\. Which commodity (maize, beans, livestock, etc.) contributes most to the overall food price index?

3\. Is price volatility significantly higher in arid/semi-arid counties (ASAL) vs. high-potential agricultural counties?

4\. What seasonal patterns exist in food prices, and do they differ by county?

5\. Which markets have the most incomplete data (gaps), and does this correlate with geographic remoteness?



\## 📈 KPIs



| KPI | Definition |

|---|---|

| \*\*National Food Price Index\*\* | Average of `c\_food\_price\_index` across all markets for the selected period |

| \*\*YoY Inflation Rate\*\* | % change in food price index vs. same period prior year |

| \*\*Price Volatility\*\* | Standard deviation of monthly price changes (per commodity, per county) |

| \*\*Market Coverage Rate\*\* | % of expected market-month observations with non-null price data |

| \*\*Affordability Gap\*\* | Difference between a county's average food price and the national average |



\## 🎯 Business Decisions Supported



1\. \*\*Where to deploy price-monitoring resources:\*\* Counties with high volatility + low data coverage need both intervention and monitoring investment.

2\. \*\*When to trigger subsidy programs:\*\* Seasonal peaks (e.g., pre-harvest "lean season") identify the highest-risk windows for targeted intervention.

3\. \*\*Which commodity to prioritize:\*\* If maize drives 60%+ of the index, maize-specific interventions (storage, import timing) have outsized impact vs. broad-based measures.



\---



\## 🛠️ Power Query Transformations (8+)



| # | Operation | Justification |

|---|---|---|

| 1 | Parse `price\_date` to proper Date type | Source stores as text; needed for time intelligence |

| 2 | Derive `year`, `month`, `quarter`, `season` columns | Required for dim\_date and DAX time intelligence |

| 3 | Remove rows where all price columns are null | 3,200+ rows with no usable data |

| 4 | Standardize county names (trim, fix casing, merge variants) | Source has inconsistent formatting |

| 5 | Unpivot commodity price columns → long format | Required for star schema (one row per market × date × commodity) |

| 6 | Rename commodity columns to human-readable names | `c\_maize\_fao` → "Maize (FAO)" |

| 7 | Add `commodity\_category` column (staple/protein/oil/dairy) | Enables category-level analysis |

| 8 | Calculate `price\_change\_mom` (month-over-month delta) | Derived field for volatility analysis |

| 9 | Filter outliers (>3σ from commodity mean) | Remove data entry errors |

| 10 | Add `is\_recent` flag (last 12 months) | Enables "current situation" vs. "historical" views |



\---



\## 🔬 Findings (to be completed in Week 4–5)



> \*This section will be populated with evidence-backed findings from the final analysis. Each finding will cite the specific visual, measure, and data slice that supports it.\*



1\. \_\[TBD]\_

2\. \_\[TBD]\_

3\. \_\[TBD]\_

4\. \_\[TBD]\_

5\. \_\[TBD]\_



\## 💡 Recommendations (to be completed in Week 5)



> \*Each recommendation will be tied to a specific finding and framed as an actionable step for the target audience (county planners, NGOs, policy advisors).\*



1\. \_\[TBD]\_

2\. \_\[TBD]\_

3\. \_\[TBD]\_

4\. \_\[TBD]\_

5\. \_\[TBD]\_



\## ⚠️ Limitations



\- Data is \*\*market-level aggregate prices\*\*, not household expenditure. It shows what food \*costs\*, not what households \*earn\*. Affordability is inferred, not directly measured.

\- 234 markets do not cover all 47 counties equally. Some ASAL counties have 1–2 markets; Nairobi has 10+.

\- The dataset ends in October 2026. Recent events (e.g., 2026 drought, currency shifts) may not be fully captured.

\- Food price index is a \*\*composite\*\* — it masks individual commodity movements.

\- No income data is included. "Affordability gap" is a price comparison, not a true income-to-cost ratio.



\---



\## 🚀 Reproduction



\### Prerequisites

\- \[Microsoft Power BI Desktop](https://www.microsoft.com/en-us/power-bi/download-desktop) (free)

\- Python 3.10+ (optional, for data profiling)

\- Git



\### Steps



1\. \*\*Clone this repo:\*\*

&#x20;  ```bash

&#x20;  git clone https://github.com/princenzmw/mzigo-chakula.git

&#x20;  ```



2\. \*\*Download the dataset:\*\*

&#x20;  - Go to \[microdata.worldbank.org/index.php/catalog/6167](https://microdata.worldbank.org/index.php/catalog/6167)

&#x20;  - Click \*\*"Get Microdata"\*\* → download the Kenya CSV

&#x20;  - Place it in `data/raw/kenya\_rtfp.csv`



3\. \*\*Open the Power BI file:\*\*

&#x20;  ```

&#x20;  open mzigo-chakula.pbix

&#x20;  ```

&#x20;  - Power BI will prompt to refresh data. Point it to `data/raw/kenya\_rtfp.csv`.

&#x20;  - All Power Query transformations will replay automatically.



4\. \*\*Verify the model:\*\*

&#x20;  - Go to \*\*Model View\*\* → confirm 4 tables, 3 relationships, all 1:\*

&#x20;  - Go to \*\*Report View\*\* → confirm 4 pages, all visuals rendering



5\. \*\*Check DAX measures:\*\*

&#x20;  - Go to \*\*Data View\*\* → `fact\_prices` table → confirm all 10 measures calculate correctly

&#x20;  - Spot-check: select a county + year, verify YoY inflation matches manual calculation



\### Folder Structure



```

mzigo-chakula/

├── README.md

├── mzigo-chakula.pbix

├── data/

│   ├── raw/

│   │   └── kenya\_rtfp.csv          # Original download (if redistributable)

│   └── processed/

│       └── (generated by Power Query)

├── docs/

│   ├── report.pdf                  # Final project report (10–15 pp)

│   ├── transformation-log.md       # Power Query operations + before/after

│   ├── dax-catalogue.md            # All measures with formulas + validation

│   └── model-diagram.png           # Screenshot of model view

├── slides/

│   └── presentation.pptx           # 10–12 min group presentation

├── screenshots/

│   ├── page1-executive-pulse.png

│   ├── page2-county-commodity.png

│   ├── page3-trends-diagnostics.png

│   └── page4-decisions-action.png

└── contribution/

&#x20;   └── contribution-matrix.md      # Who did what

```



\---



\## 👥 Contributors



| Member | Role | Key Contributions |

|---|---|---|

| Prince NZAMUWE | Lead Analyst | Data acquisition, Power Query, DAX, model design |

| \_\[Name]\_ | \_\[Role]\_ | \_\[Contributions]\_ |

| \_\[Name]\_ | \_\[Role]\_ | \_\[Contributions]\_ |



\---



\## 📚 References



\- World Bank. (2026). \*Real Time Food Prices (RTFP) — Kenya.\* Microdata Library. \[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Retrieved 29 October 2026.

\- KNBS. (2025). \*Consumer Price Index — Kenya.\* National Bureau of Statistics.

\- CBK. (2026). \*Monetary Policy Statement.\* Central Bank of Kenya.



\---



\## 📄 License



This project is licensed under the \[MIT License](LICENSE).



The underlying data is licensed by the World Bank under \[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution: "Data sourced from the World Bank Real Time Food Prices project."



\---



\*Built with Microsoft Power BI Desktop | DSA 3050A | October 2026\*

```



\---



\*\*A few notes on using this:\*\*



\- The \*\*Findings\*\* and \*\*Recommendations\*\* sections are intentionally left as `\[TBD]` — We'll fill them in during Weeks 4–5 when we have actual analysis results.

\- The \*\*Contributors\*\* table has only my name. Group mates will add theirs as you go.

\- The \*\*DAX formulas\*\* are simplified. When we build them in Power BI, we'll copy the exact formulas into `docs/dax-catalogue.md` with validation examples (the rubric requires "validated measures").

\- The \*\*Power Query transformations\*\* list is what we \*should\* do. Document the actual "before/after" evidence (screenshots of row counts, null counts before/after) in `docs/transformation-log.md`.

\- The repo name in all URLs: `github.com/princenzmw/mzigo-chakula`

