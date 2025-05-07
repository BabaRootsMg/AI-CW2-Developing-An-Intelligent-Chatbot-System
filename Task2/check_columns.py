from pathlib import Path
import pandas as pd
import sys

# 1. Locate the script folder and the data subfolder
script_dir = Path(__file__).resolve().parent
data_dir   = script_dir / "data"

if not data_dir.exists():
    sys.exit(f"❌ data folder not found: {data_dir}\n"
             "Please create a 'data' folder next to this script and copy your CSVs into it.")

# 2. List your six files by name (they must live in data_dir)
filenames = [
    "2022_service_details_London_to_Norwich.csv",
    "2022_service_details_Norwich_to_London.csv",
    "2023_service_details_London_to_Norwich.csv",
    "2023_service_details_Norwich_to_London.csv",
    "2024_service_details_London_to_Norwich.csv",
    "2024_service_details_Norwich_to_London.csv",
]

# 3. Build full paths and ensure they exist
files = []
for name in filenames:
    p = data_dir / name
    if not p.exists():
        sys.exit(f"❌ Missing file: {p}")
    files.append(p)

# 4. Read only the headers from each CSV
column_sets = {}
for path in files:
    df = pd.read_csv(path, nrows=0)
    column_sets[path.name] = set(df.columns)

# 5. Compute union and intersection
all_columns    = set().union(*column_sets.values())
common_columns = set.intersection(*column_sets.values())

print(f"\nUnion of all columns ({len(all_columns)}):\n{sorted(all_columns)}\n")
print(f"Intersection of all columns ({len(common_columns)}):\n{sorted(common_columns)}\n")

# 6. Report per-file differences
for fname, cols in column_sets.items():
    missing = all_columns - cols
    extra   = cols - common_columns
    print(f"---\nFile: {fname}")
    if missing:
        print(f"  Missing columns ({len(missing)}): {sorted(missing)}")
    else:
        print("  No missing columns.")
    if extra:
        print(f"  Extra columns ({len(extra)}):   {sorted(extra)}")
    else:
        print("  No extra columns.")
