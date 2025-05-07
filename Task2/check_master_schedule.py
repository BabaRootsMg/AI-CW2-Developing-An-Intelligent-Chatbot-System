#!/usr/bin/env python3
"""
check_master_schedule.py

Performs data-quality and consistency checks on master_schedule.csv:
  1. Normalize date+time into true timestamps (handles overnight wrap-arounds)
  2. Missing-value counts per column
  3. Duplicate-row count
  4. Data types summary
  5. Delay computation and range spot-checks
"""

import sys
from pathlib import Path

import pandas as pd


def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        sys.exit(f"❌ File not found: {path}")
    # Read everything, avoid chunked inference warnings
    return pd.read_csv(path, low_memory=False)


def normalize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Combine date_of_service + scheduled/actual arrival into full datetimes,
    adjust for overnight wrap-around if actual < scheduled by >6 hours.
    """
    # Ensure date_of_service is datetime
    df['date_of_service'] = pd.to_datetime(df['date_of_service'], errors='coerce')

    # Build full timestamps
    df['sched_dt'] = pd.to_datetime(
        df['date_of_service'].dt.strftime('%Y-%m-%d') + ' ' +
        df['scheduled_arrival_time'],
        errors='coerce'
    )
    df['act_dt'] = pd.to_datetime(
        df['date_of_service'].dt.strftime('%Y-%m-%d') + ' ' +
        df['actual_arrival_time'],
        errors='coerce'
    )

    # If actual < scheduled by more than 6h, assume next day
    wrap_mask = (df['act_dt'] < df['sched_dt']) & (
        (df['sched_dt'] - df['act_dt']) > pd.Timedelta(hours=6)
    )
    df.loc[wrap_mask, 'act_dt'] += pd.Timedelta(days=1)

    return df


def check_missing(df: pd.DataFrame) -> None:
    print("\n1) Missing Values per Column")
    miss = df.isna().sum().sort_values(ascending=False)
    nonzero = miss[miss > 0]
    if not nonzero.empty:
        print(nonzero)
    else:
        print("✅ No missing values found")


def check_duplicates(df: pd.DataFrame) -> None:
    dup_count = df.duplicated().sum()
    print(f"\n2) Duplicate Rows: {dup_count}")
    if dup_count > 0:
        print("First duplicate row:")
        print(df[df.duplicated()].iloc[0])


def check_dtypes(df: pd.DataFrame) -> None:
    print("\n3) Data Types")
    print(df.dtypes)


def spot_check_delays(df: pd.DataFrame) -> None:
    print("\n4) Delay Computation & Range Spot-Checks")

    # Compute arrival delay in minutes
    df['arr_delay_min'] = (df['act_dt'] - df['sched_dt']).dt.total_seconds() / 60

    # Summary stats
    print("\n- Arrival-delay summary (minutes):")
    print(df['arr_delay_min'].describe().round(2))

    # Count early vs late vs on-time
    early = (df['arr_delay_min'] < 0).sum()
    on_time = (df['arr_delay_min'] == 0).sum()
    late = (df['arr_delay_min'] > 0).sum()
    total = len(df)
    print(f"\n  Early arrivals (<0 min): {early}")
    print(f"  On-time (0 min):        {on_time}")
    print(f"  Late arrivals (>0 min): {late}")
    print(f"  Total records:          {total}")

    # Show a few extreme cases
    print("\n  Example extreme early arrival:")
    print(df.nsmallest(1, 'arr_delay_min')[
        ['scheduled_arrival_time', 'actual_arrival_time', 'arr_delay_min']
    ])
    print("\n  Example extreme late arrival:")
    print(df.nlargest(1, 'arr_delay_min')[
        ['scheduled_arrival_time', 'actual_arrival_time', 'arr_delay_min']
    ])


def main():
    base_dir = Path.cwd()
    csv_path = base_dir / "master_schedule.csv"

    print(f"Loading {csv_path}...")
    df = load_data(csv_path)

    # 1) Normalize to real datetimes
    df = normalize_timestamps(df)

    # 2) Sanity checks
    check_missing(df)
    check_duplicates(df)
    check_dtypes(df)

    # 3) Delay spot-checks
    spot_check_delays(df)

    print("\n✅ All checks complete.")


if __name__ == "__main__":
    main()
