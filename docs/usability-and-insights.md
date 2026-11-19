# Week 4 Dashboard Design, Usability Checklist, and Preliminary Insights

**Course:** DSA 3050A | Business Intelligence and Data Visualization (Group Project B)
**Project:** Mzigo Chakula (Kenya Food Price Inflation and Household Affordability, 2007 to 2026)
**Authors:** Prince Nzamuwe, Yizere Denis Derick

---

## 1. Four-Page Report Architecture (46 PBIR Visuals Across 4 Pages)

All four report pages are defined in `pbip/mzigo-chakula.Report/definition/pages/` (`1280 x 720`, 16:9, custom theme `MzigoChakulaTheme.json`) and captured directly from Power BI Desktop at `2400 x 1350` (`300 DPI`) under `screenshots/` and `output/`:

| Page | Purpose | Key Visuals Included (Live PBIR) | Analytical Question(s) |
| --- | --- | --- | --- |
| `1. Executive Pulse` (`screenshots/page1-executive-pulse.png`) | Rapid situational overview (`16` visuals) | Top banner + native `pageNavigator`, 5 dropdown slicers, 5 KPI cards (`1.88`, `+7.56%`, `1.92 YTD`, `100.00%`, `4.49%`), 238-month National Food Price Index line chart, Top 10 Counties by Recent 12m YoY Inflation bar chart, Recent 12m Commodity Matrix, Top 10 County Watchlist table | Q1, Q2 |
| `2. County & Commodity` (`screenshots/page2-county-commodity.png`) | Geographic and commodity comparison (`10` visuals) | Top banner + native `pageNavigator`, 4 slicers, Top 5 Deficit vs. Bottom 5 Surplus Maize Affordability Gap diverging bar chart, 233-market Lon/Lat scatter plot, ASAL vs. Agri/Urban CV% grouped columns, County Maize Affordability & Survey table | Q1, Q3, Q5 |
| `3. Trends & Diagnostics` (`screenshots/page3-trends-diagnostics.png`) | Seasonality, smoothing, and volatility audit (`10` visuals) | Top banner + native `pageNavigator`, 4 slicers, Beans & Maize 238-month prices (with `12m Rolling Avg`, `MoM %`, and `StdDev` hover tooltips), Jan-to-Dec Seasonal Index curves, Top 10 Counties by Maize CV% bars, Seasonal Index by Cropping Window columns | Q2, Q4 |
| `4. Decisions & Action` (`screenshots/page4-decisions-action.png`) | Stakeholder triage and monitoring matrix (`10` visuals) | Top banner + native `pageNavigator`, 4 slicers, Survey % vs. Maize CV% Monitoring Priority scatter (plotting zero-survey counties at `0.00%`), County Priority Action Matrix, 10 Low-Survey Counties Under 5% bar chart, Regional Maize Price (KES/kg) grouped columns | All (Q1 to Q5) |

---

## 2. Interactive Controls Built in Power BI Desktop

- **Global Slicer Dropdowns:** Every page provides dropdown slicers across `dim_date[year]`, `dim_markets[adm1_name]`, `dim_markets[county_group]`, `dim_commodity[commodity_name]`, and `dim_date[season]` over single-direction `1:*` joins.
- **Cross-Filtering:** Clicking any county bar, scatter marker, or table row filters time trajectories and comparison metrics without bidirectional ambiguity.
- **Hover Tooltips:** Line, bar, scatter, and column charts include rich hover tooltips for `12-Month Rolling Avg (KES)`, gap-safe `MoM Change %`, `Price Volatility (KES)`, and `County Inflation Rank`.
- **Top Header Page Navigator:** Native PBIR `pageNavigator` button strip (`v00_page_nav`) integrated inside the `#0F2942` top banner on all four pages with `#0284C7` active page highlighting.

---

## 3. Usability and Visual Design Verification Checklist

| Category | Check Item | Verification Status |
| --- | --- | --- |
| **Color Palette** | Colorblind-safe Orange (`#EA580C`) vs. Teal (`#0F766E`) distinguishes ASAL vs. Agricultural/Urban groups instead of Red/Green pairs | Verified live |
| **Honest Axes** | Price and index charts start cleanly at zero (`0.0`) except the focused Seasonal Index parity plot (`0.90` to `1.10` around `1.000`) | Verified live |
| **Non-Overlap & Bounds** | Automated unit tests verify all 46 PBIR visual containers fit inside `1280 x 720` with zero overlapping bounding boxes | Verified |
| **Grain Integrity** | Composite `National Food Price Index` evaluates once per `(mkt_id, date_key)` via `SUMMARIZE` and mixed-unit table totals are suppressed (`totals = false`) | Verified live |
| **Zero-Survey Visibility** | `Survey Coverage Rate %` adds `+ 0` to `COUNT(raw_spot_price)` so un-surveyed counties plot at `0.00%` instead of vanishing as blanks | Verified live |
| **Decision Framing** | Page 4 isolates blind-spot priority quadrants, regional maize disparities, and sub-5% survey targets for direct enumerator deployment | Verified live |

---

## 4. Six Preliminary Evidence-Backed Insights

1. **Recent Inflation Resurgence Across Diverse Counties (Page 1 Top 10 Bar Chart):** Although 36-month index comparisons sit below 2023 highs (`3.465`), national food index inflation over the latest 12 months (`2025-11-01` to `2026-10-01`) returned to `+7.56%`, led by Tharaka Nithi (`+25.13%`), Marsabit (`+19.85%`), and Kisumu (`+18.43%`).
2. **Composite Index Tracks Livestock Goat Prices (Page 1 Matrix & Q2):** Across all 55,454 physical market-months, `Goat (1 head)` explains `99.99%` of `c_food_price_index` variance (`r = 0.99996`), compared to `47.83%` for Beans and `19.34%` for Maize. Unweighted KES basket sums allow a single 3,456 KES livestock unit to mask cereal swings.
3. **Maize Deflated Recently While Beans and Goats Rose (Page 1 Matrix & Page 3 Trend):** Over the latest 12 months, Maize `[Commodity YoY Inflation %]` eased to `-10.51%` (`80.13 KES/kg`), whereas Beans rose `+0.55%` (`150.42 KES/kg`) and Goats rose `+7.77%` (`5,438.29 KES/head`).
4. **Chronic Maize Cost Premium in Northern Arid Markets (Page 2 Gap Bar Chart):** ASAL markets average `+9.75 KES/kg` more for maize than Agricultural/Urban markets, led by Turkana (`+15.26 KES/kg`) and Mandera (`+10.65 KES/kg`) versus Lamu (`-17.51 KES/kg`).
5. **Inverse Seasonal Timing Between Crops and Livestock (Page 3 Seasonal Cycle):** Dry staples peak before main harvests in `Cool Dry / Harvest (Jun-Sep)` (Maize `1.023`, Beans `1.013`) and hit annual lows in `Hot Dry / Lean (Jan-Feb)` (`0.972` and `0.970`), when Goat prices reach their seasonal peak (`1.060`).
6. **Heavy Survey Coverage Blind Spots in High-Volatility Counties (Page 4 Priority Matrix):** Raw field checks cover just `4.49%` of records overall (`233` physical markets). Samburu (`20` markets, `0.00%` survey coverage), Kisumu (`0.00%`, `+18.43%` recent YoY), and Garissa (`21` markets, `3.85%` coverage) sit in the urgent blind-spot zone.
