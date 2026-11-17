# Mzigo Chakula: Kenya Food Price Inflation and Household Affordability Intelligence (2007 to 2026)

**Course:** DSA 3050A | Business Intelligence and Data Visualization (Group Project B)
**Authors:** Prince Nzamuwe, Yizere Denis Derick
**Date:** 17 November 2026

## Executive Summary

This report documents an end-to-end Microsoft Power BI and Python analytics solution analyzing 55,692 raw monthly market rows (55,454 physical market-months expanded to 166,362 commodity observations) across 233 Kenyan markets, 27 counties, and 238 consecutive months (`2007-01-01` to `2026-10-01`). Over the most recent 12 months (`2025-11-01` to `2026-10-01`), Kenya's grain-safe National Food Price Index rose +7.56% year over year (reaching 1.88 against a 19-year baseline of 1.20), led by Tharaka Nithi (+25.13%), Marsabit (+19.85%), and Kisumu (+18.43%).

## Five Evidence-Backed Findings

- **Finding 1 (Q1): Regional YoY Food Price Resurgence:** While multi-year index averages reflect the steep decline from the 2023 livestock price spike (mean 3.465 vs. 1.744 in 2025), recent 12-month National Food Price Index inflation (2025-11-01 to 2026-10-01) rebounded to +7.56%. Tharaka Nithi (+25.13%), Marsabit (+19.85%), and Kisumu (+18.43%) posted the sharpest local increases (Page 1 Top 10 YoY Bar Chart, [YoY Inflation %]).
- **Finding 2 (Q2): Composite Index Co-Moves With Goats Over Staples:** Although the source components label assigns Goat (1 head) weight 0, live goat close prices explain 99.99% of c_food_price_index variance across 55,454 physical market-months (r = 0.99996), versus 47.83% for Beans and 19.34% for Maize. In the latest 12 months, Maize fell -10.51% (80.13 KES/kg) while Goats rose +7.77% (5,438.29 KES/head) (Page 1 Commodity Matrix, [Commodity YoY Inflation %]).
- **Finding 3 (Q3): Structural ASAL Maize Price Premium and Dispersion:** ASAL markets (202 markets in 16 counties) exhibit higher Food Index CV (83.70% vs. 77.28%), higher Maize CV (40.21% vs. 38.52%), higher Goat CV (85.64% vs. 78.82%), higher outlier rates (1.14% vs. 1.03%), and +9.75 KES/kg higher maize prices than Agricultural & Urban markets (31 markets). Turkana (+15.26 KES/kg) and Mandera (+10.65 KES/kg) carry the heaviest chronic maize premiums against Lamu (-17.51 KES/kg) (Page 2 Gap Bar Chart & Grouped Bars, [Affordability Gap (KES)]).
- **Finding 4 (Q4): Inverse Crop vs. Livestock Seasonal Price Cycles:** Dry grains and livestock follow opposite annual cycles across 238 months. Maize (1.023) and Beans (1.013) reach seasonal highs during Cool Dry / Harvest (Jun-Sep) pre-harvest depletion and trough during Hot Dry / Lean (Jan-Feb) (0.972 and 0.970), when Goat prices peak at 1.060 before troughing at 0.968 (Page 3 Seasonal Cycle, [Seasonal Index]).
- **Finding 5 (Q5): Uneven County Coverage and High-Risk Field Survey Gaps:** Modelled OHLC series populate 100.00% of the 233 x 238 x 3 grid (166,362 rows), yet actual field surveys cover only 4.49% of records and omit Western Province completely (27 of 47 counties covered). Five counties rely on one market, while Samburu (20 markets, 0.00% survey coverage), Kisumu (0.00% coverage, +18.43% YoY), and Garissa (21 markets, 3.85% coverage) occupy the monitoring blind-spot quadrant (Page 4 Priority Matrix, [Survey Coverage Rate %]).

## Five Stakeholder Recommendations

- **Recommendation 1: Decouple Grain Price Tracking From the Composite Index:** County food-security dashboards should alert on commodity-specific [Commodity YoY Inflation %] and [Avg Price (KES)] for Maize (1 kg) and Beans (1 kg) alongside [National Food Price Index], because raw index shifts reflect 99.99% co-movement with Goat (1 head) prices.
- **Recommendation 2: Deploy Emergency Price Audits to Zero-Survey High-Risk Counties:** Assign county agricultural enumerators first to Samburu (20 markets, 0.00% raw survey coverage), Kisumu (0.00% coverage, +18.43% YoY surge), and large northern ASAL clusters (Turkana at 3.0% and Garissa at 3.9% coverage) to raise [Survey Coverage Rate %] above 10% across blind-spot corridors.
- **Recommendation 3: Pre-Position Grain Buffers Ahead of June-to-September Peaks:** Trigger county maize and bean strategic reserve releases in May before the Cool Dry / Harvest (Jun-Sep) seasonal price peak (1.023 maize index, 1.013 beans index), and schedule livestock offtake or pastoral support for Jan-Feb (1.060 goat peak).
- **Recommendation 4: Target ASAL Transport Subsidies Using Affordability Gaps:** Direct staple grain logistics support toward chronic net-deficit markets with the largest positive [Affordability Gap (KES)], specifically Turkana (+15.26 KES/kg), Mandera (+10.65 KES/kg), and Kisumu (+9.89 KES/kg), paired with market linkages from surplus hubs like Lamu (-17.51 KES/kg) and Kitui (-15.59 KES/kg).
- **Recommendation 5: Expand Market Instrumentation Into Western Kenya Counties:** Partner with KNBS and county trade offices to onboard physical market monitoring sites across Western Province and single-market counties (Embu, Lamu, Machakos, Nyeri, Uasin Gishu) so future RTFP releases reflect all 47 Kenyan counties.

## Summary Commodity Benchmarks

| Commodity | Full Mean (KES) | 12m Mean (KES) | 12m YoY % | CV % | Correlation `r` vs. Index |
| --- | ---: | ---: | ---: | ---: | ---: |
| Beans (1 kg) | 105.69 | 150.42 | +0.55% | 31.02% | 0.69163 |
| Maize (1 kg) | 56.02 | 80.13 | -10.51% | 40.56% | 0.43977 |
| Goat (1 head) | 3,456.14 | 5,438.29 | +7.77% | 84.72% | 0.99996 |

## AI Assistance Disclosure and Data Authenticity Statement

All 55,692 raw records, market coordinates, and commodity price observations come directly from the World Bank Real Time Food Prices (RTFP) Kenya release (CC BY 4.0) without synthetic observations. AI coding and documentation tooling assisted with Python validation scripting, Power Query M code drafting, TMDL semantic model packaging, report formatting, and slide generation, with every computed metric verified deterministically against the raw CSV through an automated pytest suite.
