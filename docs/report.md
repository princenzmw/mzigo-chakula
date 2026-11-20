# Mzigo Chakula: Kenya Food Price Inflation and Household Affordability (2007 to 2026)

**Course:** DSA 3050A | Business Intelligence and Data Visualization (Group Project B)
**Authors:** Prince Nzamuwe, Yizere Denis Derick
**Date:** 17 November 2026
**Full Report:** [docs/report.pdf](docs/report.pdf) (12-page technical report)

## Executive Summary

This report summarizes a Microsoft Power BI and Python analysis of 55,692 raw monthly market rows (55,454 physical market-months expanded to 166,362 commodity observations) across 233 Kenyan markets, 27 counties, and 238 consecutive months (`2007-01-01` to `2026-10-01`). Over the latest 12 months (`2025-11-01` to `2026-10-01`), the National Food Price Index (deduplicated at the market-month grain) rose 7.56% year over year to 1.88 against a 238-month mean of 1.20, led by Tharaka Nithi (+25.13%), Marsabit (+19.85%), and Kisumu (+18.43%).

## Five Evidence-Backed Findings

- **Finding 1 (Q1): Regional YoY Food Price Resurgence:** While annual index averages show the decline from the 2023 livestock price peak (2023 mean 3.465 vs. 1.744 in 2025), 12-month National Food Price Index inflation (2025-11-01 to 2026-10-01) rose 7.56%. Tharaka Nithi (+25.13%), Marsabit (+19.85%), and Kisumu (+18.43%) recorded the largest county increases (Page 1 Top 10 YoY Bar Chart, [YoY Inflation %]).
- **Finding 2 (Q2): Composite Index Co-Moves With Goats Over Staples:** Although the source components label assigns Goat (1 head) weight 0, monthly closing prices for Goat (1 head) explain 99.99% of c_food_price_index variance across 55,454 physical market-months (r = 0.99996), versus 47.83% for Beans and 19.34% for Maize. Over the latest 12 months, Maize fell 10.51% (to 80.13 KES/kg) while Goats rose 7.77% (to 5,438.29 KES/head) (Page 1 Commodity Matrix, [Commodity YoY Inflation %]).
- **Finding 3 (Q3): Structural ASAL Maize Price Premium and Dispersion:** ASAL markets (202 markets in 16 counties) show higher CV on the Food Index (83.70% vs. 77.28%), Maize (40.21% vs. 38.52%), and Goats (85.64% vs. 78.82%), higher outlier rates (1.14% vs. 1.03%), and +9.75 KES/kg higher maize prices than Agricultural & Urban markets (31 markets), while Beans CV is slightly lower in ASAL (30.82% vs. 31.89%). Relative to the national mean (56.02 KES/kg), Turkana (+15.26 KES/kg) and Mandera (+10.65 KES/kg) carry the largest maize premiums, compared to Lamu (-17.51 KES/kg) (Page 2 Gap Bar Chart & Grouped Bars, [Affordability Gap (KES)]).
- **Finding 4 (Q4): Inverse Crop vs. Livestock Seasonal Price Cycles:** Staple crops and livestock follow inverse annual cycles across 238 months. Maize (1.023) and Beans (1.013) reach seasonal highs during Cool Dry / Harvest (Jun-Sep) as prior-season stocks tighten before main harvests and hit annual lows during Hot Dry / Lean (Jan-Feb) (0.972 and 0.970), when Goat prices peak at 1.060 before falling to 0.968 in Jun-Sep (Page 3 Seasonal Cycle, [Seasonal Index]).
- **Finding 5 (Q5): Uneven County Coverage and High-Risk Field Survey Gaps:** Modeled OHLC series populate 100.00% of the 233 x 238 x 3 grid (166,362 rows), yet raw field surveys cover 4.49% of records and omit Western Province (27 of 47 counties covered). Five counties rely on one market, while Samburu (20 markets, 0.00% survey coverage), Kisumu (0.00% coverage, +18.43% YoY on Page 1), and Garissa (21 markets, 3.85% all-commodity coverage on the sub-5% bar chart) fall in the blind-spot quadrant (Page 4 Priority Quadrant & Low-Survey Bar Chart, [Survey Coverage Rate %]).

## Five Stakeholder Recommendations

- **Recommendation 1: Decouple Grain Price Tracking From the Composite Index:** County food-security dashboards should alert on commodity-specific [Commodity YoY Inflation %] and [Avg Price (KES)] for Maize (1 kg) and Beans (1 kg) alongside [National Food Price Index], because raw index shifts reflect 99.99% co-movement with Goat (1 head) prices.
- **Recommendation 2: Deploy Field Price Audits to Zero-Survey High-Risk Counties:** Assign county agricultural enumerators first to Samburu (20 markets, 0.00% raw survey coverage), Kisumu (0.00% coverage, +18.43% YoY), and large northern ASAL clusters (Turkana at 1.96%, Marsabit at 3.00%, and Garissa at 3.85%) to raise [Survey Coverage Rate %] above the 5% blind-spot threshold.
- **Recommendation 3: Pre-Position Grain Buffers Ahead of June-to-September Peaks:** Trigger county maize and bean strategic reserve releases in May before the Cool Dry / Harvest (Jun-Sep) seasonal price peak (1.023 maize index, 1.013 beans index), and schedule livestock offtake or pastoral support for Jan-Feb (1.060 goat peak).
- **Recommendation 4: Target Staple Grain Logistics Using Affordability Gaps:** Direct maize transport and price-stabilization support toward chronic high-price counties with the largest positive [Affordability Gap (KES)], including Turkana (+15.26 KES/kg), Mandera (+10.65 KES/kg), and Kisumu (+9.89 KES/kg), and build trade links with nearby lower-price agricultural markets such as Kitui (-15.59 KES/kg).
- **Recommendation 5: Expand Market Coverage to Unmonitored Counties:** Partner with the Kenya National Bureau of Statistics (KNBS) and county trade offices to add physical monitoring sites across the 20 unrepresented counties (including Western Province) and single-market counties (Embu, Lamu, Machakos, Nyeri, Uasin Gishu) so future World Bank RTFP releases cover all 47 Kenyan counties.

## Summary Commodity Benchmarks

| Commodity | Full Mean (KES) | 12m Mean (KES) | 12m YoY % | CV % | Correlation `r` vs. Index | R^2 vs. Index |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Beans (1 kg) | 105.69 | 150.42 | +0.55% | 31.02% | 0.69163 | 47.83% |
| Maize (1 kg) | 56.02 | 80.13 | -10.51% | 40.56% | 0.43977 | 19.34% |
| Goat (1 head) | 3,456.14 | 5,438.29 | +7.77% | 84.72% | 0.99996 | 99.99% |

## Workflow Step Evidence & Verification Screenshots

| Stage | Visual Evidence | Scope Captured |
| --- | --- | --- |
| Week 1: Raw Import & Profiling | `screenshots/week1-initial-import.png` | Power Query raw 46-column CSV preview prior to transformations |
| Week 2: Data Cleaning & QA | `screenshots/week2-powerquery-cleaning.png` | 10 Power Query M steps (`T1` to `T10`), zero orphan foreign keys, and 1,866 flagged outlier rows |
| Week 3: Star Schema Diagram | `docs/model-diagram.png` | 4-table single-direction `1:*` schema with market-month index deduplication |
| Week 3: Power BI Desktop Model View | `screenshots/week3-powerbi-model-view.png` | Live Power BI Desktop Model View with all 4 joined tables |
| Week 3: DAX Verification Audit | `screenshots/week3-dax-validation.png` | 15 DAX measures using `EDATE` and `TREATAS` to handle missing months, plus commodity benchmarks |
| Week 4: Dashboard Pages 1 to 4 | `screenshots/page1-executive-pulse.png`, `screenshots/page2-county-commodity.png`, `screenshots/page3-trends-diagnostics.png`, `screenshots/page4-decisions-action.png` | Power BI Desktop captures of all 4 report pages (46 visuals, custom theme, and top header page navigator) |

## AI Assistance Disclosure and Data Authenticity Statement

All 55,692 raw records, market coordinates, and commodity price observations come directly from the World Bank Real Time Food Prices (RTFP) Kenya release (CC BY 4.0) without synthetic observations. AI coding and documentation tools assisted with Python validation scripting, Power Query M drafting, Tabular Model Definition Language (TMDL) packaging, report formatting, and slide generation. An automated pytest suite verifies ETL invariants, PBIR/TMDL bindings, and Python reference benchmarks against the raw CSV.
