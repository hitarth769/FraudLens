def normalize_location(location: str) -> str:
    """
    Deterministic location normalization for baseline comparison.
    Handles whitespace, casing, and common country representations.
    """
    if not location or location == "Unknown":
        return "unknown"

    # Basic cleaning
    loc = location.strip().lower()

    # Common country mapping (Simplified for synthetic data)
    mapping = {
        "india": "in",
        "singapore": "sg",
        "united states": "us",
        "united kingdom": "gb",
        "germany": "de"
    }

    # Split by comma (City, Country)
    parts = [p.strip() for p in loc.split(",")]

    if len(parts) >= 2:
        city, country = parts[0], parts[1]
        # Normalize country if it's in our mapping or if it's a long name
        country = mapping.get(country, country)
        return f"{city}|{country}"

    return loc
