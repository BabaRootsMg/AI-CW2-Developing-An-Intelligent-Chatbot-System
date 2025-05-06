import csv

def load_crs_codes(csv_path="crs_codes.csv"):
    mapping = {}
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapping[row["station_name"].strip().lower()] = row["crs_code"].strip().upper()
    return mapping
