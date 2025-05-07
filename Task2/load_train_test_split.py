
import sys
import re
import pandas as pd
from pathlib import Path

def load_train_test_splits(master_csv="master_schedule.csv"):
    # 1) Load
    path = Path(master_csv)
    if not path.exists():
        raise FileNotFoundError(f"Could not find {master_csv}")
    df = pd.read_csv(path, low_memory=False)

    # 2) Parse service date
    df['date_of_service'] = pd.to_datetime(
        df['date_of_service'],
        format="%Y-%m-%d",
        errors="coerce"
    )
    date_str = df['date_of_service'].dt.strftime("%Y-%m-%d")

    # 3) Normalize and parse full datetimes with strict format
    time_cols = [
        'scheduled_departure_time',
        'scheduled_arrival_time',
        'actual_departure_time',
        'actual_arrival_time'
    ]
    for col in time_cols:
        # a) Convert to string
        times = df[col].astype(str)
        # b) Pad any H:MM or HH:MM to HH:MM:SS
        mask = times.str.match(r'^\d{1,2}:\d{2}$')
        times.loc[mask] = times.loc[mask] + ':00'  # "6:5" → "6:5:00" or "06:22" → "06:22:00"
        # c) Ensure two-digit hours/minutes/seconds
        times = times.apply(lambda t: ":".join(f"{int(x):02d}" for x in t.split(":"))
                            if re.match(r'^\d{1,2}:\d{1,2}:\d{1,2}$', t) else t)
        # d) Parse with explicit format
        df[col] = pd.to_datetime(
            date_str + " " + times,
            format="%Y-%m-%d %H:%M:%S",
            errors="coerce"
        )

    # 4) Feature engineering
    df['dep_delay_mins'] = (
        df['actual_departure_time'] - df['scheduled_departure_time']
    ).dt.total_seconds() / 60
    df['sched_duration_mins'] = (
        df['scheduled_arrival_time'] - df['scheduled_departure_time']
    ).dt.total_seconds() / 60
    df['arr_delay_mins'] = (
        df['actual_arrival_time'] - df['scheduled_arrival_time']
    ).dt.total_seconds() / 60

    df['day_of_week'] = df['date_of_service'].dt.dayofweek
    df['month']       = df['date_of_service'].dt.month
    df['dep_hour']    = df['scheduled_departure_time'].dt.hour

    # 5) Drop incomplete rows
    df.dropna(subset=[
        'dep_delay_mins','sched_duration_mins','arr_delay_mins',
        'day_of_week','month','dep_hour'
    ], inplace=True)

    # 6) Build X, y
    df['direction_bin'] = df['direction'].map({'LON→NOR': 0, 'NOR→LON': 1})
    feature_cols = [
        'dep_delay_mins','sched_duration_mins',
        'day_of_week','month','dep_hour','direction_bin'
    ]
    X = df[feature_cols]
    y = df['arr_delay_mins']

    # 7) Chronological split
    train_mask = df['date_of_service'].dt.year < 2024
    X_train, X_test = X[train_mask], X[~train_mask]
    y_train, y_test = y[train_mask], y[~train_mask]

    return X_train, X_test, y_train, y_test


if __name__ == "__main__":
    X_train, X_test, y_train, y_test = load_train_test_splits()
    print("Train:", X_train.shape, "Test:", X_test.shape)
