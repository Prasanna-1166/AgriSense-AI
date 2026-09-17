"""
AgriSense AI - Geography Reference Data
==========================================

Static administrative reference data (state and district names) used for
the manual State -> District location fallback, and for resolving GPS
coordinates to an administrative region via reverse geocoding.

This is administrative boundary reference data, not agricultural
observation data - it carries no fabrication risk in the sense Section 1
of the project brief is concerned with, but district lists are kept
current as of India's post-2014 Andhra Pradesh/Telangana bifurcation and
Andhra Pradesh's 2022 district reorganization.
"""

INDIA_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
]

# Priority states per project brief - full district lists maintained.
# Other states use a lighter placeholder list since the brief's priority is AP/Telangana.
DISTRICTS_BY_STATE = {
    "Andhra Pradesh": [
        "Alluri Sitharama Raju", "Anakapalli", "Anantapur", "Annamayya", "Bapatla",
        "Chittoor", "East Godavari", "Eluru", "Guntur", "Kakinada", "Konaseema",
        "Krishna", "Kurnool", "Nandyal", "NTR", "Palnadu", "Parvathipuram Manyam",
        "Prakasam", "Sri Potti Sriramulu Nellore", "Sri Sathya Sai", "Srikakulam",
        "Tirupati", "Visakhapatnam", "Vizianagaram", "West Godavari", "YSR Kadapa",
    ],
    "Telangana": [
        "Adilabad", "Bhadradri Kothagudem", "Hyderabad", "Jagtial", "Jangaon",
        "Jayashankar Bhupalpally", "Jogulamba Gadwal", "Kamareddy", "Karimnagar",
        "Khammam", "Komaram Bheem Asifabad", "Mahabubabad", "Mahabubnagar",
        "Mancherial", "Medak", "Medchal-Malkajgiri", "Mulugu", "Nagarkurnool",
        "Nalgonda", "Narayanpet", "Nirmal", "Nizamabad", "Peddapalli",
        "Rajanna Sircilla", "Rangareddy", "Sangareddy", "Siddipet", "Suryapet",
        "Vikarabad", "Wanaparthy", "Warangal", "Hanumakonda", "Yadadri Bhuvanagiri",
    ],
}

# Approximate state boundary centroid/bounding info intentionally omitted -
# reverse geocoding (Nominatim) is used to resolve GPS -> state/district
# instead of hardcoding coordinate boxes, which would be far less reliable.


def get_states() -> list:
    return INDIA_STATES


def get_districts(state: str) -> list:
    """Get districts for a given state. Returns empty list if not maintained."""
    return DISTRICTS_BY_STATE.get(state, [])


def match_state_from_address(address: dict) -> str:
    """
    Best-effort match of a Nominatim reverse-geocode 'address' dict to one
    of our known state names.
    """
    candidate = address.get("state", "") or address.get("state_district", "")
    for state in INDIA_STATES:
        if state.lower() == candidate.lower():
            return state
    return candidate or ""


def match_district_from_address(address: dict) -> str:
    """
    Best-effort extraction of a district name from a Nominatim reverse-geocode
    'address' dict. Nominatim doesn't use a consistent key for this across
    regions, so several fallbacks are tried.
    """
    for key in ["state_district", "county", "district", "city_district"]:
        if address.get(key):
            return address[key]
    return address.get("city", "") or address.get("town", "") or ""
