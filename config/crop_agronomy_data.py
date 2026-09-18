"""
AgriSense AI - Crop Agronomy & Economics Data Registry
========================================================

SINGLE SOURCE OF TRUTH for real-world agronomic planning information:
seed/planting-material requirement, crop duration, fertilizer
recommendations, plant-protection guidance, and cost-input components.

CRITICAL HONESTY RULE (per project requirements):
Every value in this file must be traceable to a named, dated source
(an ICAR institute, a State Agricultural University package of
practices, a government agriculture department, or an equivalent
authoritative agricultural extension source). Nothing here is
invented, averaged across "similar" crops, or backfilled with
plausible-looking numbers.

Where reliable data could not be located and verified within the
scope of this update, the corresponding field is explicitly set to
None / an empty list and carries status "UNAVAILABLE" together with
a short explanation - never a fabricated number. Unit prices for
cost calculation are intentionally left unset (None) everywhere in
this initial release: input-quantity requirements (seed, fertilizer)
are documented from agronomic sources, but current local market
prices for AP/Telangana were not available from a verifiable source
at the time of writing, so per-hectare costs are honestly reported
as unavailable rather than estimated. This is expected to be filled
in incrementally (see docs/data-sources.md) without changing this
schema.

Status vocabulary (used throughout this file and by
services/agronomy_service.py):
    VERIFIED_SOURCE  - Value taken directly from a named, dated,
                        authoritative source.
    SOURCE_ESTIMATE  - Derived from a verified source via a
                        transparent, documented calculation (e.g.
                        unit conversion, or scaling to farm area).
    UNAVAILABLE      - No reliable source was found; no value is
                        shown, only an honest explanation.

Schema per crop (see get_crop_agronomy() for the normalized shape
returned to callers):
    duration:            {min_days, max_days, description, source...} | unavailable
    planting_material:   {type, quantity_per_ha, unit, spacing, source...} | unavailable
    fertilizers:         [ {nutrient/name, quantity_per_ha, unit, stage,
                             purpose, source...} , ... ]  (may be empty)
    fertilizer_note:      free-text caveat (e.g. "adjust to soil test")
    plant_protection:    [ {target, management, active_ingredient, rate,
                             stage, source...} , ... ]  (may be empty)
    region_scope:         "Andhra Pradesh / Telangana (State Agricultural
                           University)" | "National / ICAR" | etc.
    last_verified:         ISO-ish string, when this entry was last checked
"""
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Reusable source citations
# ---------------------------------------------------------------------------
_SRC_RARS_TPT_RICE = {
    "org": "RARS Tirupati, Acharya N.G. Ranga Agricultural University (ANGRAU)",
    "title": "Recommendations for Rice Crop Production and Package of Practices, Kharif 2014 & Rabi 2014-15",
    "url": "https://www.rarstpt.org/files/rars/package%20of%20practices/Rice.pdf",
    "year": "2014",
}
_SRC_RARS_TPT_MAIZE = {
    "org": "RARS Tirupati, ANGRAU",
    "title": "Maize (Zea mays L.) - Package of Practices (Kharif and Rabi)",
    "url": "https://www.rarstpt.org/files/rars/package%20of%20practices/MaizePackage.pdf",
    "year": "not dated in source (area/production figures cited are for 2012-13)",
}
_SRC_RARS_TPT_PULSES = {
    "org": "RARS Tirupati, ANGRAU",
    "title": "Package of Practices - Blackgram, Greengram, Redgram (Pigeonpea), Bengalgram (Chickpea)",
    "url": "https://www.rarstpt.org/files/rars/package%20of%20practices/Pulses.pdf",
    "year": "not dated in source",
}
_SRC_CICR = {
    "org": "ICAR - Central Institute for Cotton Research (CICR)",
    "title": "Cotton fertilizer recommendation (rainfed) - reproduced in university hybrid-seed-production package of practices",
    "url": "https://static.vikaspedia.in/media/files_en/agriculture/crop-production/package-of-practices/hybrid-cotton-seed-production.pdf",
    "year": "not dated in source",
}
_SRC_TRACTORJUNCTION_COTTON = {
    "org": "Tractor Junction (agri-extension summary, seed-rate figures consistent with State Dept. of Agriculture advisories)",
    "title": "Cotton Cultivation in India - Varieties, Sowing, Management",
    "url": "https://www.tractorjunction.com/agriculture-news/kharif-farming-news/cotton-crop/",
    "year": "2025",
}

_SRC_TNAU_FRUIT_FERT = {
    "org": "Tamil Nadu Agricultural University (TNAU) - AgriTech Portal",
    "title": "Fertilizer Schedule for Fruit Crops",
    "url": "https://agritech.tnau.ac.in/horticulture/FERTILIZER%20SCHEDULE%20FOR%20FRUIT%20CROPS.pdf",
    "year": "not dated in source",
}
_SRC_ICAR_CCARI_MANGO = {
    "org": "ICAR - Central Coastal Agricultural Research Institute (CCARI), Goa",
    "title": "Mango - Decision Support System",
    "url": "https://ccari.icar.gov.in/dss/mango.html",
    "year": "not dated in source",
}
_SRC_TNAU_BANANA = {
    "org": "Tamil Nadu Agricultural University (TNAU) - AgriTech Portal",
    "title": "Banana Cultivation",
    "url": "http://www.agritech.tnau.ac.in/expert_system/banana/cultivation.html",
    "year": "not dated in source",
}
_SRC_ICAR_CPCRI_COCONUT = {
    "org": "ICAR - Central Plantation Crops Research Institute (CPCRI)",
    "title": "Research Achievements - Crop Production (Coconut)",
    "url": "https://cpcri.gov.in/page/research_achievements_crop_production/",
    "year": "2026 (page access date; underlying recommendation not separately dated)",
}
_SRC_ICAR_CRIJAF_JUTE = {
    "org": "ICAR - Central Research Institute for Jute and Allied Fibres (CRIJAF)",
    "title": "Economy of Low Density Sowing in Jute (Ghorai & Chakraborty)",
    "url": "https://www.ijcmas.com/9-9-2020/A.%20K.%20Ghorai%20and%20A.%20K.%20Chakraborty.pdf",
    "year": "2020",
}
_SRC_FAO_FERTUSE_INDIA = {
    "org": "FAO, citing Indian Ministry of Agriculture fertilizer consumption statistics",
    "title": "Fertilizer Use by Crop in India - Chapter 4",
    "url": "https://www.fao.org/4/a0257e/a0257e05.htm",
    "year": "2003-04 (data year; document is significantly older than this release)",
}
_SRC_DPD_ICAR_IIPR_LENTIL = {
    "org": "Directorate of Pulses Development, Ministry of Agriculture & Farmers Welfare, Govt. of India, "
           "citing Seednet GOI & ICAR - Indian Institute of Pulses Research (IIPR), Kanpur",
    "title": "Lentil - Package of Practices",
    "url": "https://dpd.gov.in/Lentil.PDF",
    "year": "not dated in source",
}
_SRC_ANGRAU_COTTON_OUTLOOK = {
    "org": "ANGRAU (Acharya N.G. Ranga Agricultural University) - Agricultural Market Intelligence Centre",
    "title": "Cotton Outlook Report, June 2023 to May 2024 (cost-return structure of Cotton in Andhra Pradesh)",
    "url": "https://angrau.ac.in/downloads/AMIC/OutlookReports/2023_24/Cotton%20outlook%20-June%20to%20May%202023-24.pdf",
    "year": "2023-24",
}
_SRC_TELANGANA_COTTON_STUDY = {
    "org": "Peer-reviewed study (Barre Jyothsna Priyadarshini et al., Bioved/Research Trend journal), using "
           "farm-survey cost data",
    "title": "Economic Analysis of Cotton Production in Bhadradri Kothagudem District of Telangana",
    "url": "https://www.researchtrend.net/bfij/pdf/306%20Economic%20Analysis%20of%20Cotton%20Production%20in%20Bhadradri%20Kothagudem%20District%20of%20Telangana%20Barre%20Jyothsna%20Priyadarshini.pdf",
    "year": "2019-20 (survey year), published 2022",
}
_SRC_TELANGANA_RICE_STUDY = {
    "org": "Peer-reviewed study (Yadav et al., International Journal of Agriculture Extension and Social "
           "Development), using official Cost of Cultivation Scheme (CACP/Directorate of Economics & "
           "Statistics) plot-level data for Bhoopalpalli district, Telangana",
    "title": "Economic analysis and supply response of rice cultivation in India: Insights from NITI "
              "Aspirational districts",
    "url": "https://www.extensionjournal.com/uploads/archives/7-12-40-977.pdf",
    "year": "TE (Triennium Ending) 2021-22, published December 2024",
}
_SRC_MAIZE_STATEWISE_STUDY = {
    "org": "Peer-reviewed study, using secondary data from the official Cost of Cultivation of Principal "
           "Crops survey (CACP concepts)",
    "title": "Cost Competitiveness of Maize Cultivation in India: A State-wise Analysis",
    "url": "https://www.researchgate.net/publication/395726954_Cost_Competitiveness_of_Maize_Cultivation_in_India_A_State-wise_Analysis",
    "year": "TE (Triennium Ending) 2021-22, published 2025",
}

UNVERIFIED_NOTE = (
    "No reliable, dated agronomic source for this field was located and verified "
    "for this release. Rather than estimate, this value is intentionally left "
    "unavailable. Consult your local Krishi Vigyan Kendra (KVK) or state "
    "agriculture department for current guidance."
)

COST_UNAVAILABLE_NOTE = (
    "Current local market prices for AP/Telangana were not available from a "
    "verified source at the time of writing. Input quantities are documented "
    "above from agronomic sources; multiply by your local purchase price to "
    "estimate cost, or check with your local KVK / input dealer for current rates."
)


def _unavailable(note: str = UNVERIFIED_NOTE) -> Dict:
    return {"status": "UNAVAILABLE", "note": note}


# ---------------------------------------------------------------------------
# Crop Agronomy Registry
# ---------------------------------------------------------------------------
CROP_AGRONOMY: Dict[str, Dict] = {

    "rice": {
        "region_scope": "Andhra Pradesh (ANGRAU, Southern Zone)",
        "last_verified": "2026-09",
        "duration": {
            "status": "VERIFIED_SOURCE",
            "min_days": 90,
            "max_days": 170,
            "description": "Variety-dependent: short-duration varieties (e.g. Varalu) mature in "
                            "90-95 days; long-duration varieties (e.g. Sri Ranga, Simhapuri) take "
                            "160-170 days. Most widely grown AP varieties fall in the 120-150 day range.",
            "source": _SRC_RARS_TPT_RICE,
        },
        "planting_material": {
            "status": "VERIFIED_SOURCE",
            "type": "seed",
            "quantity_per_ha": 55.0,
            "unit": "kg",
            "quantity_range": "For nursery raising (transplanted rice): 20-25 kg/acre (~49-62 kg/ha) "
                               "of nursery seed for wet nursery, 25-30 kg/acre (~62-74 kg/ha) for dry-seed "
                               "nursery, or 10-12 kg/acre (~25-30 kg/ha) for direct seeding.",
            "spacing": "Transplanted at 33 hills/m2 (kharif) or 44 hills/m2 (rabi), 2-3 seedlings/hill",
            "notes": "Figure shown (55 kg/ha) is the midpoint of the wet-nursery seed-rate range for "
                     "transplanted rice, converted from acre to hectare. Direct-seeded rice needs "
                     "substantially less seed - see quantity_range.",
            "source": _SRC_RARS_TPT_RICE,
        },
        "fertilizers": [
            {"status": "VERIFIED_SOURCE", "nutrient": "Nitrogen (N)", "quantity_per_ha": 80, "unit": "kg N/ha",
             "stage": "3 equal splits: basal, active tillering, panicle initiation (kharif dose; rabi dose is 120 kg N/ha)",
             "purpose": "Vegetative growth and tillering", "source": _SRC_RARS_TPT_RICE},
            {"status": "VERIFIED_SOURCE", "nutrient": "Phosphorus (P2O5)", "quantity_per_ha": 60, "unit": "kg P2O5/ha",
             "stage": "Entire dose as basal", "purpose": "Root and early growth",
             "source": _SRC_RARS_TPT_RICE},
            {"status": "VERIFIED_SOURCE", "nutrient": "Potassium (K2O)", "quantity_per_ha": 40, "unit": "kg K2O/ha",
             "stage": "Basal, or split basal + panicle initiation on light soils",
             "purpose": "Grain filling and lodging resistance", "source": _SRC_RARS_TPT_RICE},
            {"status": "VERIFIED_SOURCE", "nutrient": "Zinc Sulphate", "quantity_per_ha": 50, "unit": "kg/ha",
             "stage": "Basal (only if soil is zinc-deficient)", "purpose": "Correct zinc deficiency",
             "source": _SRC_RARS_TPT_RICE},
        ],
        "fertilizer_note": "Kharif dose shown above (80:60:40 N:P2O5:K2O kg/ha); rabi dose is higher "
                            "at 120:60:40 kg/ha. Final fertilizer dose should be adjusted according to "
                            "soil-test results where available.",
        "plant_protection": [
            {"status": "VERIFIED_SOURCE", "target": "Stem borer", "management": "Cartap hydrochloride 50WP or "
             "acephate or chlorantraniliprole, sprayed at economic threshold (1 egg mass/m2 or 5% dead hearts)",
             "active_ingredient": "Cartap hydrochloride / Acephate / Chlorantraniliprole", "rate": "2.0 g, 1.5 g, "
             "or 0.4 ml per litre of water respectively", "stage": "Tillering to booting",
             "source": _SRC_RARS_TPT_RICE},
            {"status": "VERIFIED_SOURCE", "target": "Brown/white-backed plant hopper (BPH/WBPH)",
             "management": "Spray at threshold (10-15 insects/hill tillering, 20-25/hill after flowering)",
             "active_ingredient": "Imidacloprid / Thiamethoxam / Buprofezin",
             "rate": "0.25 ml, 0.2 g, or 1.6 ml per litre respectively", "stage": "Panicle initiation to booting",
             "source": _SRC_RARS_TPT_RICE},
            {"status": "VERIFIED_SOURCE", "target": "Leaf blast / neck blast",
             "management": "Spray at first appearance under favourable (humid) weather",
             "active_ingredient": "Tricyclazole / Isoprothiolane",
             "rate": "0.6 g/l or 1.5 ml/l respectively", "stage": "2-3 sprays at 15-day interval",
             "source": _SRC_RARS_TPT_RICE},
            {"status": "VERIFIED_SOURCE", "target": "Sheath blight",
             "management": "Spray at disease initiation, ~30-45 days after transplanting",
             "active_ingredient": "Hexaconazole / Validamycin / Propiconazole",
             "rate": "2 ml/l, 2 ml/l, or 1 ml/l respectively", "stage": "2 sprays at 15-day interval",
             "source": _SRC_RARS_TPT_RICE},
        ],
        "sources": [_SRC_RARS_TPT_RICE],
        "cost_survey": {
            "status": "VERIFIED_SOURCE",
            "total_per_ha": 66985.0,
            "currency": "INR",
            "cost_concept": "Total cultivation cost (comprehensive survey cost - includes seed, fertiliser, "
                             "manure, human/animal/machine labour, and irrigation)",
            "region": "Bhoopalpalli district, Telangana (a single NITI Aspirational district, not a "
                      "full-state average)",
            "year": "TE (Triennium Ending) 2021-22",
            "breakdown_pct": [
                {"component": "Labour", "pct_of_total": 45.36},
                {"component": "Machinery", "pct_of_total": 24.0},
                {"component": "Fertilizer", "pct_of_total": 7.0},
                {"component": "Seed", "pct_of_total": 3.0},
                {"component": "Other (irrigation, manure, misc.)", "pct_of_total": 20.64},
            ],
            "source": _SRC_TELANGANA_RICE_STUDY,
            "notes": "This is a district-level academic estimate (Bhoopalpalli, Telangana) built from "
                     "official Cost of Cultivation Scheme (CACP) plot-level data, not a full Andhra "
                     "Pradesh/Telangana state average - actual cost in your district will differ. Shown "
                     "as the most specific real, sourced total-cost figure available for this crop/region "
                     "in this release; do not add this to the itemized seed/fertilizer quantities above - "
                     "it already includes them.",
        },
    },

    "maize": {
        "region_scope": "Andhra Pradesh (RARS Tirupati, ANGRAU)",
        "last_verified": "2026-09",
        "duration": {
            "status": "VERIFIED_SOURCE",
            "min_days": 90,
            "max_days": 120,
            "description": "Hybrid maturity classes: short-duration hybrids under 90 days, "
                            "medium-duration 90-100 days, long-duration 100-120 days.",
            "source": _SRC_RARS_TPT_MAIZE,
        },
        "planting_material": {
            "status": "VERIFIED_SOURCE",
            "type": "seed",
            "quantity_per_ha": 18.5,
            "unit": "kg",
            "quantity_range": "7-8 kg/acre for normal hybrids (~17.3-19.8 kg/ha); lower for speciality "
                               "corn (3-4 kg/acre sweet corn, 5 kg/acre popcorn, 10 kg/acre baby corn).",
            "spacing": "60 cm x 20 cm (or 75 cm x 20 cm for tractor-drawn intercultivation)",
            "notes": "Figure shown is the midpoint of the normal-hybrid seed-rate range, converted "
                     "from acre to hectare (1 acre = 0.4047 ha).",
            "source": _SRC_RARS_TPT_MAIZE,
        },
        "fertilizers": [
            {"status": "VERIFIED_SOURCE", "nutrient": "Nitrogen (N)", "quantity_per_ha": 178, "unit": "kg N/ha",
             "stage": "3 splits (kharif): sowing, knee-high, flowering",
             "purpose": "Vegetative growth and cob development",
             "source": _SRC_RARS_TPT_MAIZE,
             "notes": "Kharif dose is 72-80 kg N/acre (~178-198 kg N/ha); rabi dose is higher at "
                      "80-100 kg N/acre (~198-247 kg N/ha) applied in 4 splits."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Phosphorus (P2O5)", "quantity_per_ha": 59, "unit": "kg P2O5/ha",
             "stage": "Entire dose as basal", "purpose": "Root establishment",
             "source": _SRC_RARS_TPT_MAIZE, "notes": "Kharif: 24 kg/acre (~59 kg/ha); rabi: 32 kg/acre (~79 kg/ha)."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Potassium (K2O)", "quantity_per_ha": 49, "unit": "kg K2O/ha",
             "stage": "Basal", "purpose": "Grain fill and stalk strength",
             "source": _SRC_RARS_TPT_MAIZE, "notes": "Kharif: 20 kg/acre (~49 kg/ha); rabi: 32 kg/acre (~79 kg/ha)."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Zinc Sulphate", "quantity_per_ha": 49, "unit": "kg/ha",
             "stage": "Basal (only if soil is zinc-deficient)", "purpose": "Correct zinc deficiency",
             "source": _SRC_RARS_TPT_MAIZE, "notes": "20 kg/acre (~49 kg/ha)."},
        ],
        "fertilizer_note": "Figures shown are the kharif-season dose converted from kg/acre to kg/ha "
                            "(1 acre = 0.4047 ha); rabi doses are higher (see notes on each nutrient). "
                            "Final fertilizer dose should be adjusted according to soil-test results.",
        "plant_protection": [
            {"status": "VERIFIED_SOURCE", "target": "Stem borer (Chilo partellus / Sesamia inferens)",
             "management": "Prophylactic spray when crop is 10-12 days old, or Carbofuran 3G in leaf whorls at 25-30 days",
             "active_ingredient": "Monocrotophos 36SC / Coragen (chlorantraniliprole) / Carbofuran 3G",
             "rate": "1.6 ml/l, 0.3 ml/l, or 3 kg/acre respectively", "stage": "Early vegetative stage",
             "source": _SRC_RARS_TPT_MAIZE},
            {"status": "VERIFIED_SOURCE", "target": "Leaf blight (Exserohilum turcicum)",
             "management": "1-2 sprays from knee-high stage at 7-10 day interval",
             "active_ingredient": "Mancozeb", "rate": "2.5 g/l", "stage": "Knee-high onward",
             "source": _SRC_RARS_TPT_MAIZE},
        ],
        "sources": [_SRC_RARS_TPT_MAIZE],
        "cost_survey": {
            "status": "VERIFIED_SOURCE",
            "total_per_ha": 64448.0,
            "currency": "INR",
            "cost_concept": "Cost A2+FL (all paid-out costs plus the imputed value of family labour - NOT "
                             "the full economic cost, which would also include rental value of owned land "
                             "and interest on fixed capital)",
            "region": "Telangana (state-wise CACP analysis)",
            "year": "TE (Triennium Ending) 2021-22",
            "breakdown_pct": [],
            "source": _SRC_MAIZE_STATEWISE_STUDY,
            "notes": "Telangana had the HIGHEST Cost A2+FL among Indian states studied in this analysis "
                     "(compare Madhya Pradesh's lowest at ~ Rs 37,388/ha). Andhra Pradesh's per-unit cost "
                     "of production was reported as the lowest among states studied (~ Rs 826/quintal) with "
                     "the highest gross returns (~ Rs 1,18,920/ha) - a different cost concept and metric, "
                     "not directly comparable to the Telangana per-ha figure shown here. Do not add this "
                     "to the itemized seed/fertilizer quantities above - Cost A2+FL already includes them.",
        },
    },

    "cotton": {
        "region_scope": "National / ICAR (CICR); AP/Telangana-specific current cost and seed-rate "
                         "figures not yet verified for this release",
        "last_verified": "2026-09",
        "duration": _unavailable(
            "Cotton duration varies widely by hybrid (typically 150-180 days) but a specific, dated "
            "source giving a defensible range for AP/Telangana hybrids was not verified for this "
            "release."
        ),
        "planting_material": {
            "status": "VERIFIED_SOURCE",
            "type": "seed",
            "quantity_per_ha": 1.2,
            "unit": "kg",
            "quantity_range": "Bt hybrid cotton: ~450-600 g/acre (~1.1-1.5 kg/ha) due to wide spacing; "
                               "non-hybrid (desi) varieties need substantially more, ~2.5-3 kg/acre (~6-7.4 kg/ha).",
            "spacing": "120-135 cm between rows, 45-60 cm between plants (hybrid, rainfed)",
            "notes": "Figure shown is the midpoint of the Bt hybrid range, converted acre to hectare. "
                     "Most cotton grown in AP/Telangana today is Bt hybrid.",
            "source": _SRC_TRACTORJUNCTION_COTTON,
        },
        "fertilizers": [
            {"status": "VERIFIED_SOURCE", "nutrient": "Nitrogen (N)", "quantity_per_ha": 60, "unit": "kg N/ha",
             "stage": "Split doses; 25-30 and 60-65 days after sowing", "purpose": "Vegetative and boll growth",
             "source": _SRC_CICR, "notes": "ICAR-CICR standard recommended dose for RAINFED cotton is "
                                            "60:30:30 NPK kg/ha; irrigated hybrid cotton commonly receives "
                                            "higher doses (100:50:50 or more) per soil-test recommendation."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Phosphorus (P2O5)", "quantity_per_ha": 30, "unit": "kg P2O5/ha",
             "stage": "Basal", "purpose": "Root and boll development", "source": _SRC_CICR},
            {"status": "VERIFIED_SOURCE", "nutrient": "Potassium (K2O)", "quantity_per_ha": 30, "unit": "kg K2O/ha",
             "stage": "Basal", "purpose": "Fibre quality and boll retention", "source": _SRC_CICR},
        ],
        "fertilizer_note": "Figure shown is the ICAR-CICR rainfed baseline (60:30:30 NPK kg/ha). "
                            "Irrigated hybrid cotton is commonly given a higher dose per local "
                            "soil-test recommendation - confirm with your local agriculture department "
                            "before applying.",
        "plant_protection": _unavailable(
            "Cotton plant-protection needs (pink bollworm, sucking pests) are highly regional and "
            "season-specific and change year to year with resistance status. A specific, dated, "
            "crop-specific advisory was not verified for this release; consult your current-season "
            "ICAR/state agriculture department cotton advisory before spraying."
        ),
        "sources": [_SRC_CICR, _SRC_TRACTORJUNCTION_COTTON],
        "cost_survey": {
            "status": "VERIFIED_SOURCE",
            "total_per_ha": 162019.99,
            "currency": "INR",
            "cost_concept": "Total cultivation cost (comprehensive survey cost; working capital share "
                             "82.03%, fixed capital share 17.97%)",
            "region": "Andhra Pradesh (state-level)",
            "year": "2023-24",
            "breakdown_pct": [
                {"component": "Labour", "pct_of_total": 49.26},
            ],
            "source": _SRC_ANGRAU_COTTON_OUTLOOK,
            "notes": "From ANGRAU's official Cotton Outlook Report - cost of production was Rs 8,222.28 "
                     "per quintal, and due to low productivity that year, both gross margin and net returns "
                     "were reported as NEGATIVE for 2023-24 (a loss-making season). A separate district-level "
                     "academic study in Bhadradri Kothagudem, Telangana (2019-20) found a considerably "
                     "lower total cost of ~Rs 94,159/ha - cost estimates vary significantly by year, "
                     "district, input prices and survey methodology; treat this figure as indicative for "
                     "the specific year and region shown, not a stable constant. Do not add this to the "
                     "itemized seed/fertilizer quantities above - it already includes them.",
        },
    },

    "chickpea": {
        "region_scope": "Andhra Pradesh (RARS Tirupati, ANGRAU) - listed there as Bengalgram",
        "last_verified": "2026-09",
        "duration": _unavailable(
            "A specific days-to-maturity figure was not stated in the verified source (sowing window "
            "October 15 - end November is documented; maturity range was not)."
        ),
        "planting_material": {
            "status": "VERIFIED_SOURCE",
            "type": "seed",
            "quantity_per_ha": 62.5,
            "unit": "kg",
            "quantity_range": "60-65 kg/ha; use higher rate (up to ~30 kg/ha higher) for late-sown "
                               "double-cropped conditions in coastal districts.",
            "spacing": "30 cm x 10 cm",
            "notes": None,
            "source": _SRC_RARS_TPT_PULSES,
        },
        "fertilizers": [
            {"status": "VERIFIED_SOURCE", "nutrient": "Nitrogen (N)", "quantity_per_ha": 20, "unit": "kg N/ha",
             "stage": "Basal", "purpose": "Starter dose (chickpea is a nitrogen-fixing legume)",
             "source": _SRC_RARS_TPT_PULSES},
            {"status": "VERIFIED_SOURCE", "nutrient": "Phosphorus (P2O5)", "quantity_per_ha": 50, "unit": "kg P2O5/ha",
             "stage": "Basal", "purpose": "Root and nodule development", "source": _SRC_RARS_TPT_PULSES},
            {"status": "VERIFIED_SOURCE", "nutrient": "Sulphur (S)", "quantity_per_ha": 40, "unit": "kg S/ha",
             "stage": "Basal", "purpose": "Oil/protein quality and nodulation", "source": _SRC_RARS_TPT_PULSES},
        ],
        "fertilizer_note": "As a legume, chickpea fixes a portion of its own nitrogen once nodulation "
                            "is established (seed treatment with Rhizobium culture is recommended).",
        "plant_protection": [
            {"status": "VERIFIED_SOURCE", "target": "Pod borer (Helicoverpa armigera)",
             "management": "IPM: pheromone traps (10/ha), bird perches (50/ha), NSKE/neem sprays before chemical use; "
                            "chemical spray only if needed",
             "active_ingredient": "Endosulfan / Chlorpyriphos / Quinalphos / Acephate",
             "rate": "2 ml/l, 2.5 ml/l, 2 ml/l, or 1 g/l respectively", "stage": "Flowering to pod formation",
             "source": _SRC_RARS_TPT_PULSES},
            {"status": "VERIFIED_SOURCE", "target": "Wilt / Dry root rot",
             "management": "Seed treatment before sowing; grow resistant varieties (e.g. JG-11, ICCV-10)",
             "active_ingredient": "Captan or Thiram (seed treatment)", "rate": "2.5 g/kg seed", "stage": "Pre-sowing",
             "source": _SRC_RARS_TPT_PULSES},
        ],
        "sources": [_SRC_RARS_TPT_PULSES],
    },

    "blackgram": {
        "region_scope": "Andhra Pradesh (RARS Tirupati, ANGRAU)",
        "last_verified": "2026-09",
        "duration": _unavailable(
            "Days-to-maturity not stated in the verified source; varies by variety/season."
        ),
        "planting_material": {
            "status": "VERIFIED_SOURCE",
            "type": "seed",
            "quantity_per_ha": 17.5,
            "unit": "kg",
            "quantity_range": "15-20 kg/ha (line-sown, kharif/rabi under irrigation); 40-45 kg/ha "
                               "if broadcast in rice fallows.",
            "spacing": "30 cm x 10 cm (line-sown)",
            "notes": None,
            "source": _SRC_RARS_TPT_PULSES,
        },
        "fertilizers": [
            {"status": "VERIFIED_SOURCE", "nutrient": "Nitrogen (N)", "quantity_per_ha": 20, "unit": "kg N/ha",
             "stage": "Basal", "purpose": "Starter dose", "source": _SRC_RARS_TPT_PULSES},
            {"status": "VERIFIED_SOURCE", "nutrient": "Phosphorus (P2O5)", "quantity_per_ha": 50, "unit": "kg P2O5/ha",
             "stage": "Basal", "purpose": "Root and nodule development", "source": _SRC_RARS_TPT_PULSES},
        ],
        "fertilizer_note": "Seed treatment with Rhizobium culture can save 20-25% of the nitrogen "
                            "requirement.",
        "plant_protection": [
            {"status": "VERIFIED_SOURCE", "target": "Maruca pod borer",
             "management": "Monitor from flower-bud initiation (35-40 DAS); NSKE/neem before chemical use",
             "active_ingredient": "Acephate / Chlorpyriphos / Thiodicarb",
             "rate": "1.0 g/l, 2 ml/l, or 1.5 g/l respectively", "stage": "Flowering initiation",
             "source": _SRC_RARS_TPT_PULSES},
            {"status": "VERIFIED_SOURCE", "target": "Yellow mosaic virus (whitefly-transmitted)",
             "management": "Grow resistant varieties (LBG-752, T-9, Pant U-31); seed treatment against whitefly",
             "active_ingredient": "Carbosulfan / Imidacloprid / Thiamethoxam (seed treatment)",
             "rate": "30 g, 5 ml, or 5 g per kg seed respectively", "stage": "Pre-sowing",
             "source": _SRC_RARS_TPT_PULSES},
        ],
        "sources": [_SRC_RARS_TPT_PULSES],
    },

    "mungbean": {
        "region_scope": "Andhra Pradesh (RARS Tirupati, ANGRAU) - listed there as Greengram",
        "last_verified": "2026-09",
        "duration": _unavailable(
            "Days-to-maturity not stated in the verified source; varies by variety/season."
        ),
        "planting_material": {
            "status": "VERIFIED_SOURCE",
            "type": "seed",
            "quantity_per_ha": 17.5,
            "unit": "kg",
            "quantity_range": "15-20 kg/ha (line-sown, kharif/rabi/summer under irrigation); "
                               "30-35 kg/ha if broadcast in rice fallows.",
            "spacing": "30 cm x 10 cm (line-sown)",
            "notes": None,
            "source": _SRC_RARS_TPT_PULSES,
        },
        "fertilizers": [
            {"status": "VERIFIED_SOURCE", "nutrient": "Nitrogen + Phosphorus", "quantity_per_ha": None, "unit": None,
             "stage": None, "purpose": None,
             "source": _SRC_RARS_TPT_PULSES,
             "notes": "Source states greengram fertilizer, weed, and plant-protection management "
                       "'are similar to blackgram' without repeating exact figures. See the blackgram "
                       "entry (20 kg N + 50 kg P2O5 per ha) as the documented reference."},
        ],
        "fertilizer_note": "Documented as agronomically similar to blackgram (20 N + 50 P2O5 kg/ha) "
                            "in the source; not restated with independent figures for greengram.",
        "plant_protection": _unavailable(
            "Source states plant-protection practices mirror blackgram; no greengram-specific figures "
            "were separately verified for this release. See the blackgram entry for the documented "
            "reference practices."
        ),
        "sources": [_SRC_RARS_TPT_PULSES],
    },

    "pigeonpeas": {
        "region_scope": "Andhra Pradesh (RARS Tirupati, ANGRAU) - listed there as Redgram",
        "last_verified": "2026-09",
        "duration": _unavailable(
            "Source distinguishes 'medium duration' and 'short duration' varieties by name but does "
            "not give a numeric days-to-maturity range."
        ),
        "planting_material": {
            "status": "VERIFIED_SOURCE",
            "type": "seed",
            "quantity_per_ha": 12.5,
            "unit": "kg",
            "quantity_range": "Kharif medium-duration varieties: 5-10 kg/ha; kharif short-duration: "
                               "15-18 kg/ha; rabi: 15-20 kg/ha.",
            "spacing": "Medium-duration: 150-240 cm x 20 cm; short-duration: 60-90 cm x 20 cm",
            "notes": "Figure shown is the midpoint of the kharif medium-duration range.",
            "source": _SRC_RARS_TPT_PULSES,
        },
        "fertilizers": [
            {"status": "VERIFIED_SOURCE", "nutrient": "Nitrogen (N)", "quantity_per_ha": 20, "unit": "kg N/ha",
             "stage": "Basal", "purpose": "Starter dose", "source": _SRC_RARS_TPT_PULSES},
            {"status": "VERIFIED_SOURCE", "nutrient": "Phosphorus (P2O5)", "quantity_per_ha": 50, "unit": "kg P2O5/ha",
             "stage": "Basal", "purpose": "Root and nodule development", "source": _SRC_RARS_TPT_PULSES},
        ],
        "fertilizer_note": "Seed treatment with Rhizobium culture recommended before sowing.",
        "plant_protection": [
            {"status": "VERIFIED_SOURCE", "target": "Pod borer (Helicoverpa armigera)",
             "management": "IPM first: pheromone traps (10/ha), Trichogramma release (65,000/ha twice weekly), "
                            "bird perches (50/ha); chemical only if needed at flowering/pod stage",
             "active_ingredient": "Chlorpyriphos / Quinalphos / Acephate / Chlorantraniliprole",
             "rate": "2.5 ml/l, 2 ml/l, 1 g/l, or 0.3 ml/l respectively", "stage": "Flowering and pod formation",
             "source": _SRC_RARS_TPT_PULSES},
            {"status": "VERIFIED_SOURCE", "target": "Wilt / Sterility mosaic virus",
             "management": "Grow resistant varieties (ICPL 87119, PRG 158, BSMR 853, BSMR 736)",
             "active_ingredient": None, "rate": None, "stage": "Variety selection at sowing",
             "source": _SRC_RARS_TPT_PULSES},
        ],
        "sources": [_SRC_RARS_TPT_PULSES],
    },

    "mango": {
        "region_scope": "National / ICAR-CCARI (Goa) + TNAU (Tamil Nadu) - not AP/Telangana-specific",
        "last_verified": "2026-09",
        "duration": _unavailable(
            "Mango is a perennial tree crop; a specific, dated source for years-to-first-bearing "
            "(commonly cited informally as ~4-5 years for grafts) was not verified for this release."
        ),
        "planting_material": {
            "status": "VERIFIED_SOURCE",
            "type": "grafted plant",
            "quantity_per_ha": 100.0,
            "unit": "plants",
            "quantity_range": "100 grafts/ha at standard 10m x 10m square spacing; up to 400/ha for "
                               "dwarf varieties (e.g. Sindhu, Amrapali) at 5m x 5m spacing or more under "
                               "high-density planting systems.",
            "spacing": "10 m x 10 m (square system, standard varieties)",
            "notes": None,
            "source": _SRC_ICAR_CCARI_MANGO,
        },
        "fertilizers": [
            {"status": "SOURCE_ESTIMATE", "nutrient": "Nitrogen (N)", "quantity_per_ha": 100, "unit": "kg N/ha",
             "quantity_per_plant": 1.0, "unit_per_plant": "kg/tree/year",
             "stage": "Bearing tree (6th year onwards), split basal doses (Aug and post-fruit-set under irrigation)",
             "purpose": "Vegetative growth and fruiting", "source": _SRC_TNAU_FRUIT_FERT,
             "notes": "TNAU gives 1.0 kg N/tree/year for a bearing tree (6th year onwards). The kg/ha figure "
                      "here is DERIVED by multiplying by the standard planting density of 100 trees/ha "
                      "(ICAR-CCARI Goa) - it is an estimate, not a separately sourced per-ha figure. "
                      "Recompute using your actual tree count if your spacing differs."},
            {"status": "SOURCE_ESTIMATE", "nutrient": "Phosphorus (P)", "quantity_per_ha": 100, "unit": "kg P/ha",
             "quantity_per_plant": 1.0, "unit_per_plant": "kg/tree/year",
             "stage": "Bearing tree (6th year onwards)", "purpose": "Root and fruit development",
             "source": _SRC_TNAU_FRUIT_FERT,
             "notes": "Derived the same way as the nitrogen figure above - see that note."},
            {"status": "SOURCE_ESTIMATE", "nutrient": "Potassium (K)", "quantity_per_ha": 150, "unit": "kg K/ha",
             "quantity_per_plant": 1.5, "unit_per_plant": "kg/tree/year",
             "stage": "Bearing tree (6th year onwards)", "purpose": "Fruit quality and yield",
             "source": _SRC_TNAU_FRUIT_FERT,
             "notes": "Derived the same way as the nitrogen figure above - see that note."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Farmyard Manure (FYM)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 50, "unit_per_plant": "kg/tree/year",
             "stage": "Bearing tree (6th year onwards), applied Sep-Oct", "purpose": "Organic matter and soil health",
             "source": _SRC_TNAU_FRUIT_FERT,
             "notes": "Shown per tree only (not converted to per-ha) to avoid compounding two derived "
                      "conversions in one figure."},
        ],
        "fertilizer_note": "Source figures are per bearing tree/year (TNAU); per-hectare values are "
                            "calculated using a standard 100 trees/ha planting density and are therefore "
                            "estimates, not independently sourced per-ha figures. Young (1st year) trees "
                            "receive a much smaller dose that increases annually - see source for the "
                            "full age-wise schedule.",
        "plant_protection": _unavailable(
            "A specific, dated, crop-specific pest/disease advisory for mango was not verified for this "
            "release."
        ),
        "sources": [_SRC_ICAR_CCARI_MANGO, _SRC_TNAU_FRUIT_FERT],
    },

    "banana": {
        "region_scope": "National / TNAU (Tamil Nadu) - not AP/Telangana-specific",
        "last_verified": "2026-09",
        "duration": _unavailable(
            "A specific, dated source for days/months-to-harvest was not verified for this release."
        ),
        "planting_material": {
            "status": "SOURCE_ESTIMATE",
            "type": "sucker / tissue-culture plantlet",
            "quantity_per_ha": 2500.0,
            "unit": "plants",
            "quantity_range": "TNAU documents a wide commercial range of 1,600-10,000 plants/ha depending "
                               "on spacing (1.0 x 1.1 m to 2.0 x 2.0 m) and system (square, high-density, "
                               "paired-row, etc.).",
            "spacing": "Commonly used spacing is in the 1.8-2.0 m x 1.8-2.0 m range",
            "notes": "The 2,500/ha figure is a representative estimate (2m x 2m spacing) from within TNAU's "
                     "documented range - not a single explicit 'recommended' figure from the source. "
                     "Actual density varies significantly by variety and system - see quantity_range.",
            "source": _SRC_TNAU_BANANA,
        },
        "fertilizers": [
            {"status": "SOURCE_ESTIMATE", "nutrient": "Nitrogen (N)", "quantity_per_ha": 275, "unit": "kg N/ha",
             "quantity_per_plant": 110, "unit_per_plant": "g/plant/year",
             "stage": "Garden land, varieties other than Nendran", "purpose": "Vegetative growth and bunch development",
             "source": _SRC_TNAU_FRUIT_FERT,
             "notes": "TNAU gives 110 g N/plant/year for garden-land banana (varieties other than Nendran). "
                      "The kg/ha figure is DERIVED using the 2,500 plants/ha estimate above - recompute "
                      "using your actual plant count. Wetland/Nendran/hill-banana doses differ - see source."},
            {"status": "SOURCE_ESTIMATE", "nutrient": "Phosphorus (P)", "quantity_per_ha": 88, "unit": "kg P/ha",
             "quantity_per_plant": 35, "unit_per_plant": "g/plant/year",
             "stage": "Garden land, varieties other than Nendran", "purpose": "Root and root system development",
             "source": _SRC_TNAU_FRUIT_FERT, "notes": "Derived the same way as nitrogen above."},
            {"status": "SOURCE_ESTIMATE", "nutrient": "Potassium (K)", "quantity_per_ha": 825, "unit": "kg K/ha",
             "quantity_per_plant": 330, "unit_per_plant": "g/plant/year",
             "stage": "Garden land, varieties other than Nendran", "purpose": "Bunch/fruit quality",
             "source": _SRC_TNAU_FRUIT_FERT, "notes": "Derived the same way as nitrogen above."},
        ],
        "fertilizer_note": "Figures are for garden-land banana, varieties other than Nendran. TNAU "
                            "documents different doses for Nendran, wetland, hill, and tissue-culture "
                            "banana (tissue-culture plants get 50% extra at months 2/4/6/8) - see source. "
                            "Per-hectare values are estimates derived from a representative plant density, "
                            "not independently sourced per-ha figures.",
        "plant_protection": _unavailable(
            "A specific, dated, crop-specific pest/disease advisory for banana was not verified for this "
            "release."
        ),
        "sources": [_SRC_TNAU_BANANA, _SRC_TNAU_FRUIT_FERT],
    },

    "coconut": {
        "region_scope": "National / ICAR-CPCRI",
        "last_verified": "2026-09",
        "duration": _unavailable(
            "Coconut is a long-duration perennial (commonly informally cited as ~5-7 years to first "
            "bearing); a specific dated source for this figure was not verified for this release."
        ),
        "planting_material": {
            "status": "VERIFIED_SOURCE",
            "type": "seedling",
            "quantity_per_ha": 175.0,
            "unit": "plants",
            "quantity_range": "175 palms/ha at the recommended square-system spacing.",
            "spacing": "7.5 m x 7.5 m (square system)",
            "notes": None,
            "source": _SRC_ICAR_CPCRI_COCONUT,
        },
        "fertilizers": [
            {"status": "SOURCE_ESTIMATE", "nutrient": "Nitrogen (N)", "quantity_per_ha": 87.5, "unit": "kg N/ha",
             "quantity_per_plant": 500, "unit_per_plant": "g/palm/year",
             "stage": "2 splits per year (September and May)", "purpose": "Vegetative growth and nut development",
             "source": _SRC_ICAR_CPCRI_COCONUT,
             "notes": "ICAR-CPCRI gives 500 g N/palm/year. The kg/ha figure is DERIVED using the 175 "
                      "palms/ha spacing above - recompute using your actual palm count."},
            {"status": "SOURCE_ESTIMATE", "nutrient": "Phosphorus (P2O5)", "quantity_per_ha": 56, "unit": "kg P2O5/ha",
             "quantity_per_plant": 320, "unit_per_plant": "g/palm/year",
             "stage": "2 splits per year (September and May)", "purpose": "Root and nut development",
             "source": _SRC_ICAR_CPCRI_COCONUT, "notes": "Derived the same way as nitrogen above."},
            {"status": "SOURCE_ESTIMATE", "nutrient": "Potassium (K2O)", "quantity_per_ha": 210, "unit": "kg K2O/ha",
             "quantity_per_plant": 1200, "unit_per_plant": "g/palm/year",
             "stage": "2 splits per year (September and May)", "purpose": "Nut quality and copra content (coconut is a heavy K feeder)",
             "source": _SRC_ICAR_CPCRI_COCONUT, "notes": "Derived the same way as nitrogen above."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Organic manure", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 50, "unit_per_plant": "kg/palm/year (or 30 kg green manure)",
             "stage": "Annual", "purpose": "Organic matter and soil health",
             "source": _SRC_ICAR_CPCRI_COCONUT, "notes": None},
        ],
        "fertilizer_note": "Per-hectare values are derived from ICAR-CPCRI's per-palm dose using the "
                            "recommended 175 palms/ha spacing - they are estimates, not independently "
                            "sourced per-ha figures.",
        "plant_protection": _unavailable(
            "A specific, dated, crop-specific pest/disease advisory for coconut was not verified for "
            "this release."
        ),
        "sources": [_SRC_ICAR_CPCRI_COCONUT],
    },

    "orange": {
        "region_scope": "National / TNAU (Tamil Nadu) - not AP/Telangana-specific",
        "last_verified": "2026-09",
        "duration": _unavailable(
            "Citrus is a perennial tree crop; a specific dated source for years-to-first-bearing was "
            "not verified for this release."
        ),
        "planting_material": _unavailable(
            "A specific, dated source for recommended planting density/spacing for sweet orange was "
            "not verified for this release (only the manure-application radius, 70 cm from trunk, was "
            "documented)."
        ),
        "fertilizers": [
            {"status": "VERIFIED_SOURCE", "nutrient": "Nitrogen (N)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 600, "unit_per_plant": "g/tree/year",
             "stage": "Bearing tree (6th year onwards); applied in 2 doses, March and October",
             "purpose": "Vegetative growth and fruiting", "source": _SRC_TNAU_FRUIT_FERT,
             "notes": "Shown per tree only - no verified planting-density source to convert to per-ha "
                      "without guessing (see planting_material above)."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Phosphorus (P2O5)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 200, "unit_per_plant": "g/tree/year",
             "stage": "Bearing tree (6th year onwards); applied October", "purpose": "Root and fruit development",
             "source": _SRC_TNAU_FRUIT_FERT, "notes": "Shown per tree only - see nitrogen note above."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Potassium (K2O)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 300, "unit_per_plant": "g/tree/year",
             "stage": "Bearing tree (6th year onwards); applied October", "purpose": "Fruit quality",
             "source": _SRC_TNAU_FRUIT_FERT, "notes": "Shown per tree only - see nitrogen note above."},
        ],
        "fertilizer_note": "Figures are per bearing tree/year (TNAU sweet orange schedule). Not converted "
                            "to per-hectare because no verified planting-density source was found for this "
                            "release - multiply by your actual tree count to estimate a farm total.",
        "plant_protection": _unavailable(
            "A specific, dated, crop-specific pest/disease advisory for orange was not verified for "
            "this release."
        ),
        "sources": [_SRC_TNAU_FRUIT_FERT],
    },

    "grapes": {
        "region_scope": "National / TNAU (Tamil Nadu) - not AP/Telangana-specific",
        "last_verified": "2026-09",
        "duration": _unavailable(
            "Grapevines are a perennial crop; a specific dated source for years-to-first-bearing was "
            "not verified for this release."
        ),
        "planting_material": _unavailable(
            "A specific, dated Indian source for recommended vine spacing/density was not verified for "
            "this release."
        ),
        "fertilizers": [
            {"status": "VERIFIED_SOURCE", "nutrient": "Nitrogen (N)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 40, "unit_per_plant": "g/vine/year (year III onwards, Thompson Seedless)",
             "stage": "Applied twice: half immediately after pruning, half 60 days later",
             "purpose": "Vegetative growth and bunch development", "source": _SRC_TNAU_FRUIT_FERT,
             "notes": "TNAU gives a year I/II/III progression per vine for Thompson Seedless: N 20/30/40 g, "
                      "P 8/16/24 g, K 40/80/20 g (K figure for year III is lower than year II in the "
                      "original source table - reproduced as documented). Not converted to per-ha "
                      "because no verified vine-spacing source was found - see planting_material above."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Phosphorus (P)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 24, "unit_per_plant": "g/vine/year (year III onwards, Thompson Seedless)",
             "stage": "Applied twice: half immediately after pruning, half 60 days later",
             "purpose": "Root and bunch development", "source": _SRC_TNAU_FRUIT_FERT,
             "notes": "See nitrogen note above for the full year I/II/III progression."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Potassium (K)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 20, "unit_per_plant": "g/vine/year (year III onwards, Thompson Seedless)",
             "stage": "Half immediately after pruning, half 60 days later", "purpose": "Berry quality",
             "source": _SRC_TNAU_FRUIT_FERT,
             "notes": "See nitrogen note above; this year-III figure is lower than year II (80 g) in the "
                      "original source table."},
        ],
        "fertilizer_note": "Figures shown are per vine/year for Thompson Seedless (the most widely grown "
                            "Indian table-grape variety); TNAU documents different doses for Muscat, "
                            "Sonaka/Manikchaman/Sharad Seedless/Anab-e-Shahi. Not converted to per-hectare "
                            "because no verified vine-spacing source was found for this release.",
        "plant_protection": _unavailable(
            "A specific, dated, crop-specific pest/disease advisory for grapes was not verified for "
            "this release."
        ),
        "sources": [_SRC_TNAU_FRUIT_FERT],
    },

    "papaya": {
        "region_scope": "National / TNAU (Tamil Nadu) - not AP/Telangana-specific",
        "last_verified": "2026-09",
        "duration": _unavailable(
            "A specific, dated source for months-to-first-harvest was not verified for this release."
        ),
        "planting_material": _unavailable(
            "A specific, dated Indian source for recommended planting density/spacing for papaya was "
            "not verified for this release."
        ),
        "fertilizers": [
            {"status": "VERIFIED_SOURCE", "nutrient": "Nitrogen (N)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 50, "unit_per_plant": "g/plant per application",
             "stage": "Bimonthly (every 2 months) from the 3rd month after planting, after removing unwanted sex forms",
             "purpose": "Vegetative growth and fruiting", "source": _SRC_TNAU_FRUIT_FERT,
             "notes": "TNAU gives this as a recurring bimonthly per-application dose, not a single annual "
                      "total - shown as documented rather than extrapolated to an annual figure. Not "
                      "converted to per-ha because no verified planting-density source was found."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Phosphorus (P)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 50, "unit_per_plant": "g/plant per application",
             "stage": "Bimonthly from the 3rd month after planting", "purpose": "Root and fruit development",
             "source": _SRC_TNAU_FRUIT_FERT, "notes": "See nitrogen note above."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Potassium (K)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 50, "unit_per_plant": "g/plant per application",
             "stage": "Bimonthly from the 3rd month after planting", "purpose": "Fruit quality",
             "source": _SRC_TNAU_FRUIT_FERT, "notes": "See nitrogen note above."},
        ],
        "fertilizer_note": "FYM 10 kg/plant is applied once as basal, in addition to the recurring "
                            "bimonthly N/P/K dose shown above. Figures are not converted to a total "
                            "annual or per-hectare amount to avoid extrapolating beyond what the source "
                            "states.",
        "plant_protection": _unavailable(
            "A specific, dated, crop-specific pest/disease advisory for papaya was not verified for "
            "this release."
        ),
        "sources": [_SRC_TNAU_FRUIT_FERT],
    },

    "pomegranate": {
        "region_scope": "National / TNAU (Tamil Nadu) - not AP/Telangana-specific",
        "last_verified": "2026-09",
        "duration": _unavailable(
            "Pomegranate is a perennial crop; a specific dated source for years-to-first-bearing was "
            "not verified for this release."
        ),
        "planting_material": _unavailable(
            "A specific, dated Indian source for recommended planting density/spacing for pomegranate "
            "was not verified for this release."
        ),
        "fertilizers": [
            {"status": "VERIFIED_SOURCE", "nutrient": "Nitrogen (N)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 600, "unit_per_plant": "g/plant/year (6th year onwards)",
             "stage": "Annual (bearing tree)", "purpose": "Vegetative growth and fruiting",
             "source": _SRC_TNAU_FRUIT_FERT,
             "notes": "TNAU gives an age progression per plant: 1st year 200 g N, 2nd-5th year 400 g, "
                      "6th year onwards 600 g (shown here). P follows 100/250/500 g and K follows "
                      "400/800/1200 g across the same age bands. Not converted to per-ha because no "
                      "verified planting-density source was found."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Phosphorus (P)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 500, "unit_per_plant": "g/plant/year (6th year onwards)",
             "stage": "Annual (bearing tree)", "purpose": "Root and fruit development",
             "source": _SRC_TNAU_FRUIT_FERT, "notes": "See nitrogen note above for the full age progression."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Potassium (K)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 1200, "unit_per_plant": "g/plant/year (6th year onwards)",
             "stage": "Annual (bearing tree)", "purpose": "Fruit quality and arils development",
             "source": _SRC_TNAU_FRUIT_FERT, "notes": "See nitrogen note above for the full age progression."},
        ],
        "fertilizer_note": "Figures are per plant/year for a bearing (6th year onwards) plant; younger "
                            "plants receive a smaller, age-scaled dose - see source. Not converted to "
                            "per-hectare because no verified planting-density source was found.",
        "plant_protection": _unavailable(
            "A specific, dated, crop-specific pest/disease advisory for pomegranate was not verified "
            "for this release."
        ),
        "sources": [_SRC_TNAU_FRUIT_FERT],
    },

    "apple": {
        "region_scope": "National / TNAU - not specific to any major apple-growing state "
                         "(Himachal Pradesh, Uttarakhand, J&K) and not AP/Telangana-relevant",
        "last_verified": "2026-09",
        "duration": _unavailable(
            "Apple is a perennial temperate tree crop; a specific dated source for years-to-first-bearing "
            "was not verified for this release."
        ),
        "planting_material": _unavailable(
            "A specific, dated source for recommended planting density/spacing was not verified for "
            "this release (spacing varies enormously by rootstock and training system)."
        ),
        "fertilizers": [
            {"status": "VERIFIED_SOURCE", "nutrient": "Nitrogen (N)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 500, "unit_per_plant": "g/tree/year (bearing tree)",
             "stage": "Annual", "purpose": "Vegetative growth and fruiting", "source": _SRC_TNAU_FRUIT_FERT,
             "notes": "Not converted to per-ha - no verified planting-density source was found, and apple "
                      "spacing varies widely by rootstock/training system."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Phosphorus (P)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 1000, "unit_per_plant": "g/tree/year (bearing tree)",
             "stage": "Annual", "purpose": "Root and fruit development", "source": _SRC_TNAU_FRUIT_FERT,
             "notes": "See nitrogen note above."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Potassium (K)", "quantity_per_ha": None, "unit": None,
             "quantity_per_plant": 1000, "unit_per_plant": "g/tree/year (bearing tree)",
             "stage": "Annual", "purpose": "Fruit quality", "source": _SRC_TNAU_FRUIT_FERT,
             "notes": "See nitrogen note above."},
        ],
        "fertilizer_note": "FYM 25 kg/tree is also applied annually (basal), in addition to the N/P/K "
                            "shown above. This crop is not relevant to Andhra Pradesh/Telangana growing "
                            "conditions - shown only because it is one of the 22 ML-dataset crops.",
        "plant_protection": _unavailable(
            "A specific, dated, crop-specific pest/disease advisory for apple was not verified for "
            "this release."
        ),
        "sources": [_SRC_TNAU_FRUIT_FERT],
    },

    "jute": {
        "region_scope": "National / ICAR-CRIJAF (jute is grown mainly in West Bengal/eastern India, not "
                         "AP/Telangana)",
        "last_verified": "2026-09",
        "duration": {
            "status": "VERIFIED_SOURCE",
            "min_days": 100,
            "max_days": 120,
            "description": "ICAR-CRIJAF field trials harvested the crop at 120 days after sowing (DAS); "
                            "commercial harvest is typically taken at the fibre-appropriate maturity stage "
                            "somewhat before this.",
            "source": _SRC_ICAR_CRIJAF_JUTE,
        },
        "planting_material": {
            "status": "VERIFIED_SOURCE",
            "type": "seed",
            "quantity_per_ha": 6.75,
            "unit": "kg",
            "quantity_range": "Conventional high-density sowing (broadcast): 6-7.5 kg/ha. ICAR-CRIJAF "
                               "research recommends a lower rate of 1.9-2.6 kg/ha of active seed (mixed "
                               "with inert material to total 6 kg/ha for even distribution) to reduce "
                               "labour cost without reducing fibre yield.",
            "spacing": "Broadcast or line-sown; low-density sowing aims for 3.0-3.5 lakh plants/ha at harvest "
                       "(vs. 4.5-5.0 lakh/ha under conventional high-density sowing)",
            "notes": "Figure shown (6.75 kg/ha) is the midpoint of the conventional high-density sowing "
                     "range. The lower-cost, research-recommended alternative is 1.9-2.6 kg/ha - see "
                     "quantity_range.",
            "source": _SRC_ICAR_CRIJAF_JUTE,
        },
        "fertilizers": [
            {"status": "VERIFIED_SOURCE", "nutrient": "Nitrogen (N)", "quantity_per_ha": 38.0, "unit": "kg N/ha",
             "stage": "Not specified (national average)", "purpose": "Vegetative growth and fibre yield",
             "source": _SRC_FAO_FERTUSE_INDIA,
             "notes": "This is a NATIONAL AVERAGE ACTUAL FERTILIZER USE figure (2003-04), not an explicit "
                      "current agronomic recommendation - shown because no more current, dated Indian "
                      "recommendation was verified for this release. Treat as a rough historical "
                      "reference only."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Phosphorus (P2O5)", "quantity_per_ha": 11.5, "unit": "kg P2O5/ha",
             "stage": "Not specified (national average)", "purpose": "Root development",
             "source": _SRC_FAO_FERTUSE_INDIA, "notes": "See nitrogen note above - a 2003-04 national average, not a current recommendation."},
            {"status": "VERIFIED_SOURCE", "nutrient": "Potassium (K2O)", "quantity_per_ha": 5.0, "unit": "kg K2O/ha",
             "stage": "Not specified (national average)", "purpose": "Fibre quality",
             "source": _SRC_FAO_FERTUSE_INDIA, "notes": "See nitrogen note above - a 2003-04 national average, not a current recommendation."},
        ],
        "fertilizer_note": "The N/P/K figures above are a 2003-04 NATIONAL AVERAGE of actual fertilizer "
                            "use, not a current agronomic recommendation - no more recent, dated Indian "
                            "recommendation was verified for this release. Treat with caution and confirm "
                            "with your local KVK.",
        "plant_protection": _unavailable(
            "A specific, dated, crop-specific pest/disease advisory for jute was not verified for this "
            "release."
        ),
        "sources": [_SRC_ICAR_CRIJAF_JUTE, _SRC_FAO_FERTUSE_INDIA],
    },

    "lentil": {
        "region_scope": "National / Directorate of Pulses Development + ICAR-IIPR (lentil is a rabi crop "
                         "grown mainly in north/central India, not AP/Telangana)",
        "last_verified": "2026-09",
        "duration": _unavailable(
            "A specific, dated source for days-to-maturity was not verified for this release."
        ),
        "planting_material": _unavailable(
            "A specific, dated ICAR/government source for recommended seed rate was not verified for "
            "this release (only lower-confidence commercial/extension-style sources were found, which "
            "were not used per this project's source-quality policy)."
        ),
        "fertilizers": [
            {"status": "VERIFIED_SOURCE", "nutrient": "Nitrogen (N)", "quantity_per_ha": 20, "unit": "kg N/ha",
             "stage": "Basal, at sowing", "purpose": "Starter dose (lentil is a nitrogen-fixing legume)",
             "source": _SRC_DPD_ICAR_IIPR_LENTIL},
            {"status": "VERIFIED_SOURCE", "nutrient": "Phosphorus (P)", "quantity_per_ha": 40, "unit": "kg P/ha",
             "stage": "Basal, at sowing", "purpose": "Root and nodule development",
             "source": _SRC_DPD_ICAR_IIPR_LENTIL},
            {"status": "VERIFIED_SOURCE", "nutrient": "Sulphur (S)", "quantity_per_ha": 20, "unit": "kg S/ha",
             "stage": "Basal, at sowing", "purpose": "Oil/protein quality and nodulation",
             "source": _SRC_DPD_ICAR_IIPR_LENTIL},
        ],
        "fertilizer_note": "Figures are for medium soils. Seed treatment with Rhizobium + PSB culture "
                            "(one packet each per 10 kg seed) is recommended.",
        "plant_protection": _unavailable(
            "A specific, dated, crop-specific pest/disease advisory for lentil was not verified for "
            "this release."
        ),
        "sources": [_SRC_DPD_ICAR_IIPR_LENTIL],
    },
}


# ---------------------------------------------------------------------------
# Crops with acknowledged UNAVAILABLE agronomy data in this release.
# Listed explicitly (rather than silently missing) so the API/UI can say
# "not yet available" instead of "unknown crop".
# ---------------------------------------------------------------------------
_NO_AGRONOMY_DATA_YET = [
    "coffee", "kidneybeans", "mothbeans", "muskmelon", "watermelon",
]

for _crop_id in _NO_AGRONOMY_DATA_YET:
    CROP_AGRONOMY[_crop_id] = {
        "region_scope": None,
        "last_verified": "2026-09",
        "duration": _unavailable(),
        "planting_material": _unavailable(),
        "fertilizers": [],
        "fertilizer_note": None,
        "plant_protection": _unavailable(),
        "sources": [],
        "no_data_yet": True,
    }


def has_agronomy_data(crop_id: str) -> bool:
    """Whether ANY agronomy fields (beyond the placeholder) exist for a crop."""
    entry = CROP_AGRONOMY.get(crop_id.lower())
    return bool(entry) and not entry.get("no_data_yet", False)


def get_crop_agronomy(crop_id: str) -> Optional[Dict]:
    """Get the raw agronomy registry entry for a crop id, or None if the
    crop id is not recognized at all (as opposed to recognized-but-unavailable)."""
    return CROP_AGRONOMY.get(crop_id.lower())
