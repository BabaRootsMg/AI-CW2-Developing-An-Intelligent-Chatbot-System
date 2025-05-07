from pathlib import Path
import pandas as pd
import sys

# 1) Determine where this script lives
script_dir = Path(__file__).resolve().parent

# 2) Expect a "data" folder alongside your script
data_dir = script_dir / "data"
if not data_dir.is_dir():
    sys.exit(f"❌ Cannot find data folder: {data_dir}\n"
             "Please create it and put your CSVs there.")

# 3) List your six filenames (inside that data folder)
filenames = [
    "2022_service_details_London_to_Norwich.csv",
    "2022_service_details_Norwich_to_London.csv",
    "2023_service_details_London_to_Norwich.csv",
    "2023_service_details_Norwich_to_London.csv",
    "2024_service_details_London_to_Norwich.csv",
    "2024_service_details_Norwich_to_London.csv",
]

# 4) Build full paths and verify existence
files = []
for fname in filenames:
    p = data_dir / fname
    if not p.exists():
        sys.exit(f"❌ Missing file: {p}")
    files.append(p)

# 5) Read just the headers to compare schemas
column_sets = {}
for path in files:
    df = pd.read_csv(path, nrows=0)
    column_sets[path.name] = set(df.columns)

# 6) Union and intersection
all_columns    = set().union(*column_sets.values())
common_columns = set.intersection(*column_sets.values())

print(f"\nUnion of all columns ({len(all_columns)}):\n{sorted(all_columns)}\n")
print(f"Intersection of all columns ({len(common_columns)}):\n{sorted(common_columns)}\n")

# 7) Print per-file differences
for fname, cols in column_sets.items():
    missing = all_columns - cols
    extra   = cols - common_columns
    print(f"---\nFile: {fname}")
    print(f"  Missing: {sorted(missing)}" if missing else "  No missing columns.")
    print(f"  Extra:   {sorted(extra)}"   if extra   else "  No extra columns.")
