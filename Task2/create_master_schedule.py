#!/usr/bin/env python3
"""
Script to rebuild and save master_schedule.csv
from six raw service detail CSVs in a local data/ folder.
"""

import sys
from pathlib import Path
import pandas as pd

# 1) Set up paths
base_dir = Path.cwd()
data_dir = base_dir / "data"
if not data_dir.is_dir():
    sys.exit(f"❌ 'data/' folder not found at {data_dir}\n"
             "Please create a 'data' folder next to this script and copy the six CSV files into it.")

# 2) Raw filenames
filenames = [
    "2022_service_details_London_to_Norwich.csv",
    "2022_service_details_Norwich_to_London.csv",
    "2023_service_details_London_to_Norwich.csv",
    "2023_service_details_Norwich_to_London.csv",
    "2024_service_details_London_to_Norwich.csv",
    "2024_service_details_Norwich_to_London.csv",
]

# 3) Column‐name mapping
rename_map = {
    "gbtt_ptd": "scheduled_departure_time",
    "planned_departure_time": "scheduled_departure_time",
    "gbtt_pta": "scheduled_arrival_time",
    "planned_arrival_time": "scheduled_arrival_time",
    "actual_td": "actual_departure_time",
    "actual_departure_time": "actual_departure_time",
    "actual_ta": "actual_arrival_time",
    "actual_arrival_time": "actual_arrival_time",
    "late_canc_reason": "late_cancellation_reason",
    "late_canc_reason.1": "late_cancellation_reason",
    "date_of_service": "date_of_service",
    "location": "location",
    "rid": "rid",
    "toc_code": "toc_code",
}

# 4) Desired master columns (including new 'year' field)
master_cols = [
    "rid",
    "date_of_service",
    "location",
    "scheduled_departure_time",
    "scheduled_arrival_time",
    "actual_departure_time",
    "actual_arrival_time",
    "late_cancellation_reason",
    "toc_code",
    "year",
    "direction",
]

# 5) Load, standardize, and collect DataFrames
dfs = []
for fname in filenames:
    path = data_dir / fname
    if not path.exists():
        sys.exit(f"❌ Missing file: {path}")

    df = pd.read_csv(path)
    # Rename columns to master names
    df = df.rename(columns=rename_map)
    # Remove any duplicate columns created by renaming
    df = df.loc[:, ~df.columns.duplicated()]

    # Extract year from filename and add as column
    file_year = int(fname.split('_')[0])
    df['year'] = file_year

    # Ensure all master columns exist
    for col in master_cols:
        if col not in df.columns:
            df[col] = pd.NA

    # Keep only the master columns (except 'direction', which we'll add next)
    df = df[[c for c in master_cols if c != 'direction']]

    # Add direction based on filename
    df['direction'] = 'LON→NOR' if 'London_to_Norwich' in fname else 'NOR→LON'
    dfs.append(df)

# 6) Concatenate and save
master_df = pd.concat(dfs, ignore_index=True)
out_path = base_dir / "master_schedule.csv"
master_df.to_csv(out_path, index=False)

print(f"✅ master_schedule.csv successfully created at:\n   {out_path}")
