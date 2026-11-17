// Mzigo Chakula: dim_commodity (3 tracked Kenyan staple commodities)
let
    CommodityTable = #table(
        type table [
            commodity_id = text,
            commodity_name = text,
            category = text,
            unit = text,
            index_weight_note = text
        ],
        {
        {"beans", "Beans (1 kg)", "Legume Staple", "KG", "RTFP basket item: beans (1 KG, Index Weight = 1)"},
        {"maize_fao", "Maize (1 kg)", "Cereal Staple", "KG", "RTFP basket item: maize_fao (1 Kg, Index Weight = 1)"},
        {"livestock_goat_s_fao", "Goat (1 head)", "Livestock / Protein", "Head", "RTFP basket item: livestock_goat_s_fao (1 unit, Index Weight = 0)"}
        }
    )
in
    CommodityTable
