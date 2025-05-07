#!/usr/bin/env python3
"""
train_and_evaluate.py

Loads `training_data.csv`, engineers features (including year tag), splits chronologically,
trains regression models, and reports MAE/RMSE.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


def load_and_prepare(path: Path) -> pd.DataFrame:
    # 1) Load
    if not path.exists():
        sys.exit(f"❌ File not found: {path}")
    df = pd.read_csv(path, low_memory=False)

    # 2) Parse service date and extract year
    df['date_of_service'] = pd.to_datetime(df['date_of_service'], errors='coerce')
    df['year'] = df['date_of_service'].dt.year

    # 3) Helper to parse time cols into full datetime
    def parse_datetime(col):
        times = df[col].astype(str)
        # pad seconds if missing
        mask = times.str.match(r'^\d{1,2}:\d{2}$')
        times.loc[mask] = times.loc[mask] + ':00'
        dt = pd.to_datetime(
            df['date_of_service'].dt.strftime('%Y-%m-%d') + ' ' + times,
            format='%Y-%m-%d %H:%M:%S',
            errors='coerce'
        )
        return dt

    # 4) Parse and normalize departure & arrival datetimes
    df['scheduled_departure_dt'] = parse_datetime('scheduled_departure_time')
    df['actual_departure_dt']    = parse_datetime('actual_departure_time')
    df['scheduled_arrival_dt']   = parse_datetime('scheduled_arrival_time')
    df['actual_arrival_dt']      = parse_datetime('actual_arrival_time')
    # handle overnight wrap-around (>6h)
    wrap_arr = (df['actual_arrival_dt'] < df['scheduled_arrival_dt']) & (
        (df['scheduled_arrival_dt'] - df['actual_arrival_dt']) > pd.Timedelta(hours=6)
    )
    df.loc[wrap_arr, 'actual_arrival_dt'] += pd.Timedelta(days=1)
    wrap_dep = (df['actual_departure_dt'] < df['scheduled_departure_dt']) & (
        (df['scheduled_departure_dt'] - df['actual_departure_dt']) > pd.Timedelta(hours=6)
    )
    df.loc[wrap_dep, 'actual_departure_dt'] += pd.Timedelta(days=1)

    # 5) Feature engineering
    df['dep_delay_mins']       = (df['actual_departure_dt'] - df['scheduled_departure_dt']).dt.total_seconds() / 60
    df['sched_duration_mins']  = (df['scheduled_arrival_dt'] - df['scheduled_departure_dt']).dt.total_seconds() / 60
    df['arr_delay_mins']       = (df['actual_arrival_dt'] - df['scheduled_arrival_dt']).dt.total_seconds() / 60
    df['day_of_week']          = df['date_of_service'].dt.dayofweek
    df['month']                = df['date_of_service'].dt.month
    df['dep_hour']             = df['scheduled_departure_dt'].dt.hour
    df['direction_bin']        = df['direction'].map({'LON→NOR': 0, 'NOR→LON': 1})

    # 6) Drop any remaining nulls and unrealistic delays
    df = df.dropna(subset=[
        'dep_delay_mins','sched_duration_mins','arr_delay_mins',
        'day_of_week','month','dep_hour','year','direction_bin'
    ])
    df = df[(df['arr_delay_mins'] >= -60) & (df['arr_delay_mins'] <= 180)]

    return df


def split_data(df: pd.DataFrame):
    # Chronological split by year
    train = df[df['year'] < 2024]
    test  = df[df['year'] >= 2024]
    feature_cols = [
        'dep_delay_mins','sched_duration_mins',
        'day_of_week','month','dep_hour','direction_bin','year'
    ]
    X_train = train[feature_cols]
    y_train = train['arr_delay_mins']
    X_test  = test[feature_cols]
    y_test  = test['arr_delay_mins']
    return X_train, X_test, y_train, y_test


def train_and_evaluate(csv_path: str = 'training_data.csv'):
    base = Path(csv_path)
    df = load_and_prepare(base)
    X_train, X_test, y_train, y_test = split_data(df)
    print(f"Data shapes → X_train: {X_train.shape}, X_test: {X_test.shape}")

    # Scale numeric features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)

    # Models to evaluate
    models = {
        'LinearRegression': LinearRegression(),
        'RandomForest': RandomForestRegressor(n_estimators=100, random_state=42)
    }

    for name, model in models.items():
        model.fit(X_train_scaled, y_train)
        preds = model.predict(X_test_scaled)
        mae  = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        print(f"{name}: MAE = {mae:.2f} min, RMSE = {rmse:.2f} min")


if __name__ == '__main__':
    train_and_evaluate()
