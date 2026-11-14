# Initial Data Quality Profile

Dataset: World Bank Real Time Food Prices (RTFP), Kenya (`KEN_RTFP_mkt_2007_2026-10-05.csv`)
Accessed: 29 October 2026 | License: CC BY 4.0

## 1. Volume and Granularity

The raw CSV contains 55,692 rows and 46 columns covering 238 monthly dates from 2007-01-01 to 2026-10-01. Every series has an unbroken monthly grid of 238 observations, giving 234 series multiplied by 238 months (55,692 rows).

| Slice | Row Count | Distinct Markets | Share of Total |
| --- | ---: | ---: | ---: |
| Physical markets | 55,454 | 233 | 99.57% |
| National aggregate (`Market Average`) | 238 | 1 | 0.43% |
| Full raw CSV | 55,692 | 234 | 100.00% |

Power Query must separate or filter out the 238 `Market Average` rows before building market and county aggregations. Leaving those rows inside `fact_prices` would add a synthetic national series on top of the 233 physical markets.

## 2. Missing Values Audit

Missing values appear in only 13 of the 46 columns and follow three distinct causes:

1. Coordinates (`lat`, `lon`): Exactly 238 rows (0.43%) are blank because `Market Average` has no physical location. All 55,454 physical market rows have valid coordinates.
2. Year-over-year inflation columns (`inflation_beans`, `inflation_livestock_goat_s_fao`, `inflation_maize_fao`, `inflation_food_price_index`): Exactly 2,808 rows (5.04%, equal to 234 series times 12 months) are blank in 2007 because no 2006 baseline exists for year-over-year calculation. From January 2008 onward, these columns are 100% populated.
3. Raw spot survey columns (`beans`, `livestock_goat_s_fao`, `maize_fao`): Between 94.53% and 96.72% of cells are empty because physical market surveys occur sporadically. The dataset pairs those sparse raw surveys with modelled open, high, low, and close estimates (`o_`, `h_`, `l_`, `c_`) that have 0.00% missingness.

| Column | Non-Null Rows | Null Rows | Missing % | Reason |
| --- | ---: | ---: | ---: | --- |
| `lat` | 55,454 | 238 | 0.43% | Market Average rows have no point coordinates |
| `lon` | 55,454 | 238 | 0.43% | Market Average rows have no point coordinates |
| `beans` | 1,824 | 53,868 | 96.72% | Sporadic raw field survey coverage; modelled OHLC series are complete |
| `livestock_goat_s_fao` | 2,601 | 53,091 | 95.33% | Sporadic raw field survey coverage; modelled OHLC series are complete |
| `maize_fao` | 3,045 | 52,647 | 94.53% | Sporadic raw field survey coverage; modelled OHLC series are complete |
| `inflation_beans` | 52,884 | 2,808 | 5.04% | First 12 months (2007) lack a 2006 prior-year baseline |
| `inflation_livestock_goat_s_fao` | 52,884 | 2,808 | 5.04% | First 12 months (2007) lack a 2006 prior-year baseline |
| `inflation_maize_fao` | 52,884 | 2,808 | 5.04% | First 12 months (2007) lack a 2006 prior-year baseline |
| `inflation_food_price_index` | 52,884 | 2,808 | 5.04% | First 12 months (2007) lack a 2006 prior-year baseline |

## 3. Constant Metadata Columns

10 columns hold a single constant value across all 55,692 rows:

| Column | Constant Value | Handling in Model |
| --- | --- | --- |
| `ISO3` | `KEN` | Move to documentation or `dim_commodity` / `dim_markets` |
| `country` | `Kenya` | Move to documentation or `dim_commodity` / `dim_markets` |
| `currency` | `KES` | Move to documentation or `dim_commodity` / `dim_markets` |
| `components` | `beans (1 KG, Index Weight = 1), livestock_goat_s_fao...` | Move to documentation or `dim_commodity` / `dim_markets` |
| `start_dense_data` | `Jan 2007` | Move to documentation or `dim_commodity` / `dim_markets` |
| `last_survey_point` | `Sep 2026` | Move to documentation or `dim_commodity` / `dim_markets` |
| `data_coverage` | `4.46` | Move to documentation or `dim_commodity` / `dim_markets` |
| `data_coverage_recent` | `5.45` | Move to documentation or `dim_commodity` / `dim_markets` |
| `index_confidence_score` | `0.97` | Move to documentation or `dim_commodity` / `dim_markets` |
| `spatially_interpolated` | `0` | Move to documentation or `dim_commodity` / `dim_markets` |

## 4. Administrative Label Inconsistencies

Physical markets span 35 distinct `(adm1_name, adm2_name)` combinations. Instead of a consistent province-to-county split, the source puts former provinces in `adm1_name` for most rows while putting modern county names (`Embu`, `Hola (Tana River)`, `Kajiado`, `Kwale`, `Lamu`, `Meru`, `Taita Taveta`, `Tharaka Nithi`) in `adm1_name` for single-market entries. Five counties (`Kwale`, `Taita Taveta`, `Tana River`, `Kajiado`, `Meru`) are split across both formats, and `Kitengela (Kajiado)` sits under `Nairobi` in the source admin fields.

Normalizing these labels assigns every physical market to 27 Kenyan counties across 7 former provinces (Western Province has no markets in this release).

| Raw `adm1_name` | Raw `adm2_name` | Clean Region | Clean County | Markets | Rows |
| --- | --- | --- | --- | ---: | ---: |
| Central | Nyeri | Central | Nyeri | 1 | 238 |
| Coast | Kilifi | Coast | Kilifi | 5 | 1,190 |
| Coast | Kwale | Coast | Kwale | 1 | 238 |
| Coast | Mombasa | Coast | Mombasa | 9 | 2,142 |
| Coast | Taita Taveta | Coast | Taita Taveta | 1 | 238 |
| Coast | Tana River | Coast | Tana River | 16 | 3,808 |
| Eastern | Isiolo | Eastern | Isiolo | 16 | 3,808 |
| Eastern | Kitui | Eastern | Kitui | 2 | 476 |
| Eastern | Machakos | Eastern | Machakos | 1 | 238 |
| Eastern | Makueni | Eastern | Makueni | 5 | 1,190 |
| Eastern | Marsabit | Eastern | Marsabit | 15 | 3,570 |
| Eastern | Meru North | Eastern | Meru | 2 | 476 |
| Eastern | Meru South | Eastern | Tharaka Nithi | 1 | 238 |
| Eastern | Moyale | Eastern | Marsabit | 4 | 952 |
| Embu | Mbeere North | Eastern | Embu | 1 | 238 |
| Hola (Tana River) | Hola (Tana River) | Coast | Tana River | 1 | 238 |
| Kajiado | Ongata Rongai | Rift Valley | Kajiado | 1 | 238 |
| Kwale | Matuga | Coast | Kwale | 1 | 238 |
| Lamu | Lamu West | Coast | Lamu | 1 | 238 |
| Meru | North Imenti | Eastern | Meru | 1 | 238 |
| Nairobi | Nairobi | Nairobi | Nairobi | 9 | 2,142 |
| North Eastern | Garissa | North Eastern | Garissa | 19 | 4,522 |
| North Eastern | Ijara | North Eastern | Garissa | 2 | 476 |
| North Eastern | Mandera | North Eastern | Mandera | 12 | 2,856 |
| North Eastern | Wajir | North Eastern | Wajir | 9 | 2,142 |
| Nyanza | Kisumu | Nyanza | Kisumu | 2 | 476 |
| Rift Valley | Baringo | Rift Valley | Baringo | 9 | 2,142 |
| Rift Valley | Kajiado | Rift Valley | Kajiado | 2 | 476 |
| Rift Valley | Nakuru | Rift Valley | Nakuru | 2 | 476 |
| Rift Valley | Samburu | Rift Valley | Samburu | 20 | 4,760 |
| Rift Valley | Turkana | Rift Valley | Turkana | 57 | 13,566 |
| Rift Valley | Uasin Gishu | Rift Valley | Uasin Gishu | 1 | 238 |
| Rift Valley | West Pokot | Rift Valley | West Pokot | 2 | 476 |
| Taita Taveta | Voi | Coast | Taita Taveta | 1 | 238 |
| Tharaka Nithi | Chuka/Igambang'Ombe | Eastern | Tharaka Nithi | 1 | 238 |

## 5. County Coverage Imbalance

Market representation varies sharply by county. Turkana alone contains 57 markets (24.5% of physical markets), Samburu has 20, and Garissa has 19, while Nyeri, Embu, Machakos, Lamu, and Uasin Gishu have 1 market each.

| Clean Region | Clean County | Markets | Sample Markets |
| --- | --- | ---: | --- |
| Central | Nyeri | 1 | Karatina (Nyeri) |
| Coast | Kilifi | 5 | Dzikunze, Kachororoni, Kaembeni |
| Coast | Kwale | 2 | Kwale, Vanga (Kwale) |
| Coast | Lamu | 1 | Lamu |
| Coast | Mombasa | 9 | Bangladesh (Mombasa), Junda (Mombasa), Kalahari (Mombasa) |
| Coast | Taita Taveta | 2 | Mtito Andei, Taita Taveta |
| Coast | Tana River | 17 | Adele Center, Bangale, Bilbil |
| Eastern | Embu | 1 | Embu-Mbeere |
| Eastern | Isiolo | 16 | Benane, Biliqo, Boji |
| Eastern | Kitui | 2 | Kitui, Kitui town (Kitui) |
| Eastern | Machakos | 1 | Tala Centre Market (Machakos) |
| Eastern | Makueni | 5 | Emali, Kathonzweni (Makueni), Kibwezi |
| Eastern | Marsabit | 19 | Dambala Fachana, Dirib, Dub Goba |
| Eastern | Meru | 3 | Kiwanja, Meru, Ngaremara |
| Eastern | Tharaka Nithi | 2 | Kaanwa (Tharaka Nithi), Tharaka Nithi |
| Nairobi | Nairobi | 8 | Dandora (Nairobi), Kangemi (Nairobi), Kawangware (Nairobi) |
| North Eastern | Garissa | 21 | Alango Arba, Alinjugur, Baraki |
| North Eastern | Mandera | 12 | Alungu, Ashabito, Banissa |
| North Eastern | Wajir | 9 | Buna, Bute, Eldas |
| Nyanza | Kisumu | 2 | Kibuye (Kisumu), Kisumu |
| Rift Valley | Baringo | 9 | Amaya, Chemolingot, Kimalel Center |
| Rift Valley | Kajiado | 4 | Illbissil Food Market (Kajiado), Kajiado, Kitengela (Kajiado) |
| Rift Valley | Nakuru | 2 | Nakuru, Wakulima (Nakuru) |
| Rift Valley | Samburu | 20 | Archers Post, Baragoi, Kisima |
| Rift Valley | Turkana | 57 | Alemsekon, Aposta, Elelea |
| Rift Valley | Uasin Gishu | 1 | Eldoret town (Uasin Gishu) |
| Rift Valley | West Pokot | 2 | Lomut (West Pokot), Makutano (West Pokot) |

## 6. Price and Index Summary Statistics (Physical Markets, n = 55,454)

| Series | Min | Median | Mean | Max | Std Dev |
| --- | ---: | ---: | ---: | ---: | ---: |
| Beans close (`c_beans`, KES/kg) | 34.00 | 99.35 | 105.69 | 241.19 | 32.79 |
| Maize close (`c_maize_fao`, KES/kg) | 9.00 | 51.87 | 56.02 | 136.98 | 22.72 |
| Goat close (`c_livestock_goat_s_fao`, KES/head) | 480.69 | 2782.73 | 3456.14 | 28380.59 | 2928.08 |
| Food Price Index (`c_food_price_index`) | 0.19 | 0.97 | 1.20 | 9.63 | 0.99 |

## 7. Grain Note for Modelling

Beans, maize, and goat prices sit at the `(market, month, commodity)` grain once unpivoted, whereas `c_food_price_index` sits at the `(market, month)` grain (each market-month carries one composite index value). Week 3 modelling will either place `c_food_price_index` in a dedicated `fact_market_index` table or aggregate it at the market-month grain in DAX so unpivoting three commodities does not triple-count the index.
