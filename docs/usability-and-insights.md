# Week 4 Dashboard Design, Usability Checklist, and Preliminary Insights

**Course:** DSA 3050A | Business Intelligence and Data Visualization (Group Project B)
**Project:** Mzigo Chakula (Kenya Food Price Inflation and Household Affordability, 2007 to 2026)
**Authors:** Prince Nzamuwe, Yizere Denis Derick

---

## 1. Four-Page Report Architecture (46 Visuals Across 4 Power BI Report Pages)

All four report pages are defined using Power BI Enhanced Report Format (PBIR) under `pbip/mzigo-chakula.Report/definition/pages/` (1280 x 720 canvas, 16:9 ratio, custom theme `MzigoChakulaTheme.json`) and captured from Power BI Desktop at 2400 x 1350 (300 DPI) under `screenshots/` and `output/`:

| Page | Purpose | Key Visuals Included (Live PBIR) | Analytical Question(s) |
| --- | --- | --- | --- |
| `1. Executive Pulse` (`screenshots/page1-executive-pulse.png`) | National and county overview (16 visuals) | Top banner with native page navigator, 5 dropdown slicers, 5 Key Performance Indicator (KPI) cards (1.88 index, 7.56% Year-over-Year [YoY], 1.92 Year-to-Date [YTD], 100.00% data completeness, 4.49% survey coverage), 238-month National Food Price Index line chart, Top 10 Counties by Recent 12m YoY Inflation bar chart, Recent 12m Commodity Matrix, Top 10 County Watchlist table | Q1, Q2 |
| `2. County & Commodity` (`screenshots/page2-county-commodity.png`) | Geographic and commodity comparison (10 visuals) | Top banner with native page navigator, 4 slicers, Top 5 Deficit vs. Bottom 5 Surplus Maize Affordability Gap diverging bar chart (Turkana to Lamu), 233-market Longitude/Latitude scatter plot, Arid and Semi-Arid Lands (ASAL) vs. Agricultural and Urban Coefficient of Variation (CV%) grouped columns, County Maize Affordability & Survey table | Q3, Q5 |
| `3. Trends & Diagnostics` (`screenshots/page3-trends-diagnostics.png`) | Seasonality, smoothing, and volatility audit (10 visuals) | Top banner with native page navigator, 4 slicers, Beans and Maize 238-month prices (hover tooltips show 12m Rolling Avg, Month-over-Month [MoM] %, and Standard Deviation), Jan-to-Dec Seasonal Index curves, Top 10 Counties by Maize CV% bars, Seasonal Index by Cropping Window columns | Q3, Q4 |
| `4. Decisions & Action` (`screenshots/page4-decisions-action.png`) | Stakeholder triage and monitoring matrix (10 visuals) | Top banner with native page navigator, 4 slicers, Survey % vs. Maize CV% Monitoring Priority scatter (where Maize zero-survey counties plot at 0.00%), Maize-filtered County Priority Action Matrix, 10 Low-Survey Counties Under 5% (All Commodities) bar chart, Regional Maize Price (KES/kg) grouped columns | All (Q1 to Q5) |

---

## 2. Interactive Controls Built in Power BI Desktop

- **Global Slicer Dropdowns:** Standardized left-to-right dropdown slicers filter across single-direction `1:*` joins: Page 1 provides 5 slicers (`Commodity` via `dim_commodity[commodity_name]`, `County Group` via `dim_markets[county_group]`, `Region` via `dim_markets[adm1_name]`, `Cropping Season` via `dim_date[season]`, and `Year` via `dim_date[year]`); Pages 2 and 4 include `Commodity`, `County Group`, `Region`, and `Year`; Page 3 includes `Commodity`, `County Group`, `Region`, and `Cropping Season`.
- **Cross-Filtering:** Clicking any county bar, scatter marker, or table row filters time series and comparison metrics through single-direction dimension-to-fact joins. On Page 4, `Monitoring Priority Quadrant` (`v46_scatter_coverage_risk`) and `County Priority Action Matrix` (`v47_table_priority_action`) filter to `Maize (1 kg)`, so counties with zero Maize raw surveys (including Nairobi) plot at 0.00%. In contrast, `10 Low-Survey Counties Under 5% (All Commodities)` (`v48_bar_coverage_gap`) evaluates all three tracked commodities across 10 non-zero sub-5% counties (excluding 7 counties that have 0.00% raw survey coverage across all commodities).
- **Hover Tooltips:** Line, bar, scatter, and column charts include hover tooltips for `12-Month Rolling Avg (KES)`, `MoM Change %`, `Price Volatility (KES)`, and `County Inflation Rank`.
- **Top Header Page Navigator:** Native PBIR page navigator strip (`v00_page_nav`) placed in the `#0F2942` top banner on all four pages with `#0284C7` active page highlighting. In Power BI Desktop authoring view, hold `Ctrl + Click` on any navigation button to switch pages; in Power BI Service Reading View, page switching works on single-click (or use the bottom sheet tabs in Desktop).

---

## 3. Usability and Visual Design Verification Checklist

| Category | Check Item | Verification Status |
| --- | --- | --- |
| **Color Palette** | Colorblind-safe Orange (`#EA580C`) and Teal (`#0F766E`) distinguish ASAL and Agricultural/Urban groups without Red/Green pairs | Verified in Power BI Desktop |
| **Honest Axes** | Price and index charts start at 0.0, while the Seasonal Index line chart (`v37_line_seasonality`) auto-scales from 0.90 to 1.10 around 1.000 and the Page 4 Maize CV% dispersion scatter (`v46_scatter_coverage_risk`) starts at 20% | Verified in Power BI Desktop |
| **Non-Overlap & Bounds** | Automated unit tests verify all 46 PBIR visual containers fit inside `1280 x 720` with zero overlapping bounding boxes | Verified by pytest |
| **Grain Integrity** | Composite `National Food Price Index` evaluates once per `(mkt_id, date_key)` via `SUMMARIZE`, and mixed-unit table totals are suppressed (`totals = false`) | Verified in Power BI Desktop |
| **Zero-Survey Visibility** | `Survey Coverage Rate %` adds `+ 0` to `COUNT(raw_spot_price)` so un-surveyed counties plot at 0.00% instead of appearing blank | Verified in Power BI Desktop |
| **Decision Framing** | Page 4 displays the blind-spot quadrant (<5% survey coverage and >38% maize CV), sub-5% survey target counties, and regional maize price averages | Verified in Power BI Desktop |

---

## 4. Six Preliminary Evidence-Backed Insights

1. **Recent Inflation Resurgence Across ASAL and Agricultural Counties (Page 1 Top 10 Bar Chart):** Although 36-month index comparisons sit below the 2023 annual mean (3.465), national food index inflation over the latest 12 months (2025-11-01 to 2026-10-01) rose 7.56%, led by Tharaka Nithi (+25.13%), Marsabit (+19.85%), and Kisumu (+18.43%).
2. **Composite Index Tracks Livestock Goat Prices (Page 1 Matrix & Q2 Validation in docs/dax-catalogue.md):** Across all 55,454 physical market-months, Goat (1 head) explains 99.99% of `c_food_price_index` variance (r = 0.99996), compared to 47.83% for Beans and 19.34% for Maize. Because a goat averages 3,456 KES per head compared to 56 KES/kg for maize and 106 KES/kg for beans, unscaled KES index calculations let livestock prices dominate cereal price shifts.
3. **Maize Deflated Recently While Beans and Goats Rose (Page 1 Matrix & Page 3 Trend):** Over the latest 12 months, Maize `[Commodity YoY Inflation %]` fell 10.51% (to 80.13 KES/kg), whereas Beans rose 0.55% (to 150.42 KES/kg) and Goats rose 7.77% (to 5,438.29 KES/head).
4. **Chronic Maize Cost Premium in ASAL Markets (Page 2 Gap Bar Chart):** ASAL markets average +9.75 KES/kg more for maize than Agricultural and Urban markets. Relative to the national mean (56.02 KES/kg), Turkana (+15.26 KES/kg) and Mandera (+10.65 KES/kg) carry the largest county premiums, compared to Lamu (-17.51 KES/kg).
5. **Inverse Seasonal Timing Between Crops and Livestock (Page 3 Seasonal Cycle):** Maize and beans peak before main harvests in Cool Dry / Harvest (Jun-Sep) (Maize 1.023, Beans 1.013) and hit annual lows in Hot Dry / Lean (Jan-Feb) (0.972 and 0.970), when Goat prices reach their seasonal peak (1.060).
6. **Survey Coverage Blind Spots in High-Volatility Counties (Page 4 Priority Matrix):** Raw field checks cover 4.49% of records across 233 physical markets. Samburu (20 markets, 0.00% survey coverage), Kisumu (0.00% coverage, +18.43% recent YoY), and Garissa (21 markets, 3.85% coverage) fall inside the Page 4 blind-spot quadrant (<5% survey coverage and >38% maize CV).
