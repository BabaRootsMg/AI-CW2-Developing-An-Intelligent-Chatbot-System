# File: stations_loader.py
import csv
from pathlib import Path

def load_station_dict(csv_path: Path) -> dict[str, str]:
    """
    Load a CSV of UK stations and build a mapping from station name variants
    (official name, long name, alias) to their 3-letter station codes.

    The CSV is expected to have rows with at least five fields:
      official_name, long_name, name_alias, alpha3, tiploc

    - alpha3: the primary 3-letter code
    - tiploc: fallback code if alpha3 is missing


    Returns:
        station_map: Dict mapping lowercased station names to their code.
    """
    station_map: dict[str, str] = {}
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Stations CSV not found: {csv_path}")

    with csv_path.open(newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            # Skip rows that don't have the expected columns
            if len(row) < 5:
                continue
            official, longname, alias, alpha3, tiploc = row
            # Choose alpha3 if available, else tiploc
            code = alpha3.strip() or tiploc.strip()
            if not code or code == "\\N":
                continue
            # Normalize and add each name variant
            for key in (official, longname, alias):
                if key and key != "\\N":
                    station_map[key.lower()] = code
    return station_map
