
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict

import pandas as pd

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
RENAME_MAP: Dict[str, str] = {
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

MASTER_COLUMNS: List[str] = [
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

# ----------------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Rebuild and save master_schedule.csv from raw service CSVs"
    )
    parser.add_argument(
        "-i", "--input-dir",
        type=Path,
        default=Path.cwd() / "data",
        help="Path to folder containing raw CSV files",
    )
    parser.add_argument(
        "-o", "--output-file",
        type=Path,
        default=Path.cwd() / "master_schedule.csv",
        help="Where to save the merged schedule",
    )
    return parser.parse_args()


def setup_logging():
    """
    Configure the logging format and level.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def find_csv_files(input_dir: Path) -> List[Path]:
    """
    Generate expected filenames for years 2022–2024 and both travel directions.
    """
    files: List[Path] = []
    for year in range(2022, 2025):
        for src, dst in [("London", "Norwich"), ("Norwich", "London")]:
            fname = f"{year}_service_details_{src}_to_{dst}.csv"
            files.append(input_dir / fname)
    return files


def load_and_standardize(path: Path) -> pd.DataFrame:
    """
    Load a CSV, rename columns, add missing ones, and tag year + direction.
    """
    df = pd.read_csv(path)
    df = df.rename(columns=RENAME_MAP)
    # Drop any accidental duplicate columns
    df = df.loc[:, ~df.columns.duplicated()]

    # Extract year and direction
    year = int(path.stem.split('_')[0])
    direction = (
        "LON→NOR" if "London_to_Norwich" in path.name
        else "NOR→LON"
    )
    df['year'] = year
    df['direction'] = direction

    # Ensure all master columns are present
    for col in MASTER_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # Return only the columns we care about, in order
    return df[MASTER_COLUMNS]

# ----------------------------------------------------------------------------
# Main Execution
# ----------------------------------------------------------------------------

def main():
    args = parse_args()
    setup_logging()

    input_dir = args.input_dir
    output_file = args.output_file

    if not input_dir.is_dir():
        logging.error(f"Data directory not found: {input_dir}")
        sys.exit(1)

    csv_paths = find_csv_files(input_dir)
    data_frames: List[pd.DataFrame] = []

    for path in csv_paths:
        if not path.exists():
            logging.error(f"Missing file: {path.name}")
            sys.exit(1)

        logging.info(f"Loading {path.name}")
        df = load_and_standardize(path)
        data_frames.append(df)

    # Concatenate all years and directions
    master_df = pd.concat(data_frames, ignore_index=True)

    # Save to CSV
    master_df.to_csv(output_file, index=False)
    logging.info(f"✅ Master schedule successfully saved to: {output_file}")


if __name__ == "__main__":
    main()
