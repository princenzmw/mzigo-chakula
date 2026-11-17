# Week 4 Dashboard Design, Usability Checklist, and Preliminary Insights

**Course:** DSA 3050A | Business Intelligence and Data Visualization (Group Project B)
**Project:** Mzigo Chakula (Kenya Food Price Inflation and Household Affordability, 2007 to 2026)
**Authors:** Prince Nzamuwe, Yizere Denis Derick

---

## 1. Four-Page Report Architecture (18 Visuals Across 4 Pages)

All four report pages are defined in `pbip/mzigo-chakula.Report/report.json` (`1280 x 720`, 16:9) and rendered at 300 DPI under `screenshots/` and `output/`:

| Page | Purpose | Key Visuals Included | Analytical Question(s) |
| --- | --- | --- | --- |
| `1. Executive Pulse` (`screenshots/page1-executive-pulse.png`) | Rapid situational overview | 5 KPI cards, 238-month National Food Price Index line chart, Top 10 Counties by 12m YoY Inflation bar chart, Commodity summary matrix, Exception alerts | Q1, Q2 |
| `2. County & Commodity` (`screenshots/page2-county-commodity.png`) | Geographic and commodity comparison | Diverging Maize Affordability Gap bar chart, 233-market Lon/Lat scatter map, ASAL vs. Agri/Urban CV grouped bars, Top 8 county cost matrix with drill-through | Q1, Q3, Q5 |
| `3. Trends & Diagnostics` (`screenshots/page3-trends-diagnostics.png`) | Seasonality, smoothing, and anomaly audit | Beans/Maize 238-month prices + 12m rolling avg + custom tooltip card, Jan to Dec Seasonal Index curves, Top 10 county Maize CV bars, Outlier diagnostic breakdown | Q2, Q4 |
| `4. Decisions & Action` (`screenshots/page4-decisions-action.png`) | Stakeholder response matrix | Survey Coverage % vs. Maize CV quadrant scatter, Top 10 Priority Action county table, 3 Decision playbook cards, Limitations footer | All (Q1 to Q5) |

---

## 2. Interactive Controls Designed in Report Architecture

- **Global Slicer Ribbon:** Filters all visuals across `dim_date[year]`, `dim_markets[adm1_name]`, `dim_markets[county_group]`, `dim_commodity[commodity_name]`, and `dim_date[season]` using single-direction `1:*` relationships.
- **Cross-Filtering:** Clicking any county bar or map marker filters time trends, KPI cards, and commodity tables synchronously without bidirectional ambiguity.
- **County-to-Market Drill-Through:** `Page 2` supports drilling from any `adm2_name` county row directly to individual `mkt_name` physical markets.
- **Custom Tooltips:** Hovering time-series or county visuals displays closing KES price, `MoM Change %`, and `12-Month Rolling Avg (KES)`.
- **Top Header Navigation:** Persistent 4-tab bar across the top of all four pages (`Executive Pulse`, `County & Commodity`, `Trends & Diagnostics`, `Decisions & Action`).

---

## 3. Usability and Visual Design Verification Checklist

| Category | Check Item | Verification Status |
| --- | --- | --- |
| **Color Palette** | Colorblind-safe Orange (`#EA580C`) vs. Teal (`#0F766E`) used for ASAL vs. Agricultural/Urban groups instead of Red/Green pairs | Verified |
| **Honest Axes** | Price and index time-series start cleanly at zero (`0.0`); seasonal parity chart explicitly labels dashed `1.000` reference baseline | Verified |
| **Typography** | Clear hierarchy (32pt page header, 21pt chart titles, 38pt KPI values, 16pt table labels) with zero overlapping annotations | Verified |
| **Grain Integrity** | Composite `National Food Price Index` evaluated once per `(mkt_id, date_key)` via `SUMMARIZE` so multi-commodity pages never triple-count | Verified |
| **Direct Labeling** | Horizontal bar charts and KPI cards include exact formatted units (`KES`, `%`, index points) directly on marks | Verified |
| **Decision Framing** | Page 4 separates monitoring deployment, seasonal timing, and commodity targeting into concrete actions with limitations stated | Verified |

---

## 4. Six Preliminary Evidence-Backed Insights

1. **Recent Inflation Resurgence Across Diverse Counties (Page 1 Top 10 Bar Chart):** Although 36-month index comparisons sit below 2023 highs (`3.465`), national food index inflation over the latest 12 months (`2025-11-01` to `2026-10-01`) returned to `+7.56%`, led by Tharaka Nithi (`+25.13%`), Marsabit (`+19.85%`), and Kisumu (`+18.43%`).
2. **Composite Index Tracks Livestock Goat Prices (Page 1 Matrix & Q2):** Across all 55,454 physical market-months, `Goat (1 head)` explains `99.99%` of `c_food_price_index` variance (`r = 0.99996`), compared to `47.83%` for Beans and `19.34%` for Maize. Unweighted KES basket sums allow a single 3,456 KES livestock unit to mask cereal swings.
3. **Maize Deflated Recently While Beans and Goats Rose (Page 1 Matrix & Page 3 Trend):** Over the latest 12 months, Maize `[Commodity YoY Inflation %]` eased to `-10.51%` (`80.13 KES/kg`), whereas Beans rose `+0.55%` (`150.42 KES/kg`) and Goats rose `+7.77%` (`5,438.29 KES/head`).
4. **Chronic Maize Cost Premium in Northern Arid Markets (Page 2 Gap Bar Chart):** ASAL markets average `+9.75 KES/kg` more for maize than Agricultural/Urban markets, led by Turkana (`+15.26 KES/kg`) and Mandera (`+10.65 KES/kg`) versus Lamu (`-17.51 KES/kg`).
5. **Inverse Seasonal Timing Between Crops and Livestock (Page 3 Seasonal Cycle):** Dry staples peak before main harvests in `Cool Dry / Harvest (Jun-Sep)` (Maize `1.023`, Beans `1.013`) and hit annual lows in `Hot Dry / Lean (Jan-Feb)` (`0.972` and `0.970`), when Goat prices reach their seasonal peak (`1.060`).
6. **Heavy Survey Coverage Blind Spots in High-Volatility Counties (Page 4 Priority Matrix):** Raw field checks cover just `4.49%` of records overall (`233` physical markets). Samburu (`20` markets, `0.00%` survey coverage), Kisumu (`0.00%`, `+18.43%` recent YoY), and Garissa (`21` markets, `3.85%` coverage) sit in the urgent blind-spot zone.
