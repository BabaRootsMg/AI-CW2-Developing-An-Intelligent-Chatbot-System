#!/usr/bin/env python3
"""
check_training_data.py

Performs data-quality checks on training_data.csv:
  1. Missing values in target ('arr_delay_min')
  2. Duplicate-row count
  3. Row count sanity check (expected minimum)
  4. Target distribution summary and bounds check
  5. Feature completeness for key columns
"""

import sys
from pathlib import Path
import pandas as pd

# Configuration
MIN_EXPECTED_ROWS = 10000  # minimum acceptable rows
TARGET_COLUMN = 'arr_delay_min'
KEY_FEATURES = ['year', 'direction', 'location', 'sched_dt']


def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        sys.exit(f"❌ File not found: {path}")
    return pd.read_csv(path, low_memory=False)


def check_missing_target(df: pd.DataFrame) -> None:
    missing = df[TARGET_COLUMN].isna().sum()
    print(f"1) Missing '{TARGET_COLUMN}': {missing}")
    if missing > 0:
        sys.exit(f"❌ {missing} missing values in target column '{TARGET_COLUMN}'")


def check_duplicates(df: pd.DataFrame) -> None:
    dup = df.duplicated().sum()
    print(f"2) Duplicate rows: {dup}")
    if dup > 0:
        sys.exit(f"❌ Found {dup} duplicate rows in dataset")


def check_row_count(df: pd.DataFrame) -> None:
    count = len(df)
    print(f"3) Total rows: {count}")
    if count < MIN_EXPECTED_ROWS:
        sys.exit(f"❌ Only {count} rows found; expected at least {MIN_EXPECTED_ROWS}")


def check_target_distribution(df: pd.DataFrame) -> None:
    stats = df[TARGET_COLUMN].describe()
    print(f"4) Target distribution ({TARGET_COLUMN}):")
    print(stats.round(2))
    min_val = stats['min']
    max_val = stats['max']
    # reasonable bounds: -60 to +180 minutes
    if min_val < -60 or max_val > 180:
        print(f"⚠️  '{TARGET_COLUMN}' outside expected bounds (-60 to 180): min={min_val}, max={max_val}")


def check_feature_completeness(df: pd.DataFrame) -> None:
    print("5) Feature completeness: missing counts")
    missing_feats = df[KEY_FEATURES].isna().sum()
    print(missing_feats)
    if missing_feats.any():
        sys.exit("❌ Some key feature columns have missing values. Please investigate.")


def main():
    base = Path.cwd()
    file_path = base / 'training_data.csv'

    print(f"Loading training data from {file_path}...")
    df = load_data(file_path)

    check_missing_target(df)
    check_duplicates(df)
    check_row_count(df)
    check_target_distribution(df)
    check_feature_completeness(df)

    print("\n✅ All training-data checks passed. Dataset is ready for modeling.")


if __name__ == '__main__':
    main()
