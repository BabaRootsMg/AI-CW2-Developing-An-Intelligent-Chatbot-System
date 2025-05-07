#!/usr/bin/env python3
"""
prepare_training_data.py

Reads master_schedule.csv, normalizes timestamps, filters to complete records,
calculates arrival-delay in minutes, and writes out training_data.csv.
"""

import sys
from pathlib import Path
import pandas as pd


def load_master(path: Path) -> pd.DataFrame:
    if not path.exists():
        sys.exit(f"❌ master_schedule.csv not found at {path}")
    return pd.read_csv(path, low_memory=False)


def normalize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    # Ensure date_of_service is datetime
    df['date_of_service'] = pd.to_datetime(df['date_of_service'], errors='coerce')

    # Combine date + scheduled arrival time
    df['sched_dt'] = pd.to_datetime(
        df['date_of_service'].dt.strftime('%Y-%m-%d') + ' ' + df['scheduled_arrival_time'],
        errors='coerce'
    )
    # Combine date + actual arrival time
    df['act_dt'] = pd.to_datetime(
        df['date_of_service'].dt.strftime('%Y-%m-%d') + ' ' + df['actual_arrival_time'],
        errors='coerce'
    )
    # Handle overnight wrap-around: if actual < scheduled by >6h, add one day
    mask = (df['act_dt'] < df['sched_dt']) & (
        (df['sched_dt'] - df['act_dt']) > pd.Timedelta(hours=6)
    )
    df.loc[mask, 'act_dt'] = df.loc[mask, 'act_dt'] + pd.Timedelta(days=1)
    return df


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    # Normalize timestamps
    df = normalize_timestamps(df)
    # Filter to complete rows and explicitly make a copy to avoid SettingWithCopyWarning
    df = df.dropna(subset=['sched_dt', 'act_dt', 'location', 'direction', 'year']).copy()
    # Compute arrival delay in minutes using .loc to avoid chained assignment
    df.loc[:, 'arr_delay_min'] = (
        df['act_dt'] - df['sched_dt']
    ).dt.total_seconds() / 60
    # Convert categorical fields safely
    df.loc[:, 'direction'] = df['direction'].astype('category')
    return df


def save_training_data(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)
    print(f"✅ training_data.csv created at {path}")


def main():
    base = Path.cwd()
    master_path = base / 'master_schedule.csv'
    out_path = base / 'training_data.csv'

    print(f"Loading master schedule from {master_path}...")
    master_df = load_master(master_path)

    print("Preparing training data...")
    train_df = prepare(master_df)

    print(f"Saving training data to {out_path}...")
    save_training_data(train_df, out_path)

    print("Done.")


if __name__ == '__main__':
    main()