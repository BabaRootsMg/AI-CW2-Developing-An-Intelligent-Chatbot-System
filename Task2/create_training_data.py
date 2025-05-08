#!/usr/bin/env python3
"""
prepare_training_data.py

Reads a master schedule CSV, normalizes timestamps, filters for complete records,
calculates arrival delays in minutes, and writes out a training_data CSV.

Usage:
    python prepare_training_data.py \
        --input master_schedule.csv \
        --output training_data.csv
"""

import sys
import argparse
import logging
from pathlib import Path

import pandas as pd


# ----------------------------------------------------------------------------
# Argument Parsing and Logging Setup
# ----------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for input and output file paths.
    """
    parser = argparse.ArgumentParser(
        description="Generate training data from master schedule"
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=Path.cwd() / "master_schedule.csv",
        help="Path to the master_schedule.csv file",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path.cwd() / "training_data.csv",
        help="Path where training_data.csv will be saved",
    )
    return parser.parse_args()


def setup_logging():
    """
    Configure logging with a timestamped INFO format.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ----------------------------------------------------------------------------
# Core Processing Functions
# ----------------------------------------------------------------------------

def load_master(path: Path) -> pd.DataFrame:
    """
    Load the master schedule CSV into a DataFrame.
    Exits if the file is not found.
    """
    if not path.exists():
        logging.error(f"Master schedule not found: {path}")
        sys.exit(1)
    logging.info(f"Loading master schedule from {path}")
    return pd.read_csv(path, low_memory=False)


def normalize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert date and time columns to datetime objects and adjust for overnight arrivals.
    """
    # Parse service dates
    df['date_of_service'] = pd.to_datetime(df['date_of_service'], errors='coerce')

    # Build full datetime for scheduled and actual arrivals
    base_date = df['date_of_service'].dt.strftime('%Y-%m-%d')
    df['sched_dt'] = pd.to_datetime(
        base_date + ' ' + df['scheduled_arrival_time'],
        errors='coerce'
    )
    df['act_dt'] = pd.to_datetime(
        base_date + ' ' + df['actual_arrival_time'],
        errors='coerce'
    )

    # Adjust for services running past midnight (arrival earlier than scheduled by >6h)
    overnight = (df['act_dt'] < df['sched_dt']) & (
        (df['sched_dt'] - df['act_dt']) > pd.Timedelta(hours=6)
    )
    if overnight.any():
        logging.info("Adjusting overnight arrivals by adding one day to actual times")
        df.loc[overnight, 'act_dt'] += pd.Timedelta(days=1)
    return df


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter complete records and compute arrival delay in minutes.
    Returns a DataFrame ready for model training.
    """
    df = normalize_timestamps(df)

    # Keep only rows with valid timestamps and required metadata
    required = ['sched_dt', 'act_dt', 'location', 'direction', 'year']
    df = df.dropna(subset=required).copy()

    # Calculate delay in minutes
    df['arr_delay_min'] = (
        df['act_dt'] - df['sched_dt']
    ).dt.total_seconds().div(60)

    # Ensure direction is a categorical type
    df['direction'] = df['direction'].astype('category')

    logging.info(
        f"Prepared {len(df)} records with computed arrival delays"
    )
    return df


def save_training_data(df: pd.DataFrame, path: Path) -> None:
    """
    Save the prepared training DataFrame to CSV.
    """
    df.to_csv(path, index=False)
    logging.info(f"Training data saved to {path}")


# ----------------------------------------------------------------------------
# Main Execution
# ----------------------------------------------------------------------------

def main():
    args = parse_args()
    setup_logging()

    master_df = load_master(args.input)
    train_df = prepare_data(master_df)
    save_training_data(train_df, args.output)

    logging.info("All done.")


if __name__ == '__main__':
    main()
