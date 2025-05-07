#!/usr/bin/env python3
"""
harden_model.py

Performs feature engineering on training_data.csv, hyperparameter tuning on RandomForestRegressor
using time-based CV, trains the final model on the full train set, evaluates on a held-out test set,
and serializes the best model for deployment.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df['date_of_service'] = pd.to_datetime(df['date_of_service'], errors='coerce')

    def parse_dt(date_series, time_series):
        times = time_series.astype(str).copy()
        mask = times.str.match(r'^\d{1,2}:\d{2}$')
        times.loc[mask] = times.loc[mask] + ':00'
        return pd.to_datetime(
            date_series.dt.strftime('%Y-%m-%d') + ' ' + times,
            format='%Y-%m-%d %H:%M:%S',
            errors='coerce'
        )

    df['scheduled_departure_dt'] = parse_dt(df['date_of_service'], df['scheduled_departure_time'])
    df['actual_departure_dt']    = parse_dt(df['date_of_service'], df['actual_departure_time'])
    df['scheduled_arrival_dt']   = parse_dt(df['date_of_service'], df['scheduled_arrival_time'])
    df['actual_arrival_dt']      = parse_dt(df['date_of_service'], df['actual_arrival_time'])

    arr_wrap = (
        df['actual_arrival_dt'] < df['scheduled_arrival_dt']) & \
        ((df['scheduled_arrival_dt'] - df['actual_arrival_dt']) > pd.Timedelta(hours=6))
    df.loc[arr_wrap, 'actual_arrival_dt'] += pd.Timedelta(days=1)
    dep_wrap = (
        df['actual_departure_dt'] < df['scheduled_departure_dt']) & \
        ((df['scheduled_departure_dt'] - df['actual_departure_dt']) > pd.Timedelta(hours=6))
    df.loc[dep_wrap, 'actual_departure_dt'] += pd.Timedelta(days=1)

    df['dep_delay_mins']      = (df['actual_departure_dt'] - df['scheduled_departure_dt']).dt.total_seconds() / 60
    df['sched_duration_mins'] = (df['scheduled_arrival_dt'] - df['scheduled_departure_dt']).dt.total_seconds() / 60
    if 'arr_delay_min' not in df.columns:
        df['arr_delay_min'] = (df['actual_arrival_dt'] - df['scheduled_arrival_dt']).dt.total_seconds() / 60
    df['day_of_week'] = df['date_of_service'].dt.dayofweek
    df['month']       = df['date_of_service'].dt.month
    df['dep_hour']    = df['scheduled_departure_dt'].dt.hour
    df['direction_bin'] = df['direction'].map({'LON→NOR': 0, 'NOR→LON': 1})

    feature_cols = [
        'dep_delay_mins', 'sched_duration_mins', 'arr_delay_min',
        'day_of_week', 'month', 'dep_hour', 'direction_bin', 'year'
    ]
    df = df.dropna(subset=feature_cols)
    return df


def split_train_test(df: pd.DataFrame):
    train = df[df['year'] < 2024]
    test  = df[df['year'] >= 2024]
    feature_cols = [
        'dep_delay_mins', 'sched_duration_mins',
        'day_of_week', 'month', 'dep_hour', 'direction_bin', 'year'
    ]
    X_train = train[feature_cols]
    y_train = train['arr_delay_min']
    X_test  = test[feature_cols]
    y_test  = test['arr_delay_min']
    return X_train, y_train, X_test, y_test


def main():
    base = Path.cwd()
    data_path = base / 'training_data.csv'
    if not data_path.exists():
        sys.exit(f"❌ training_data.csv not found at {data_path}")

    print(f"Loading training data from {data_path}...")
    df = pd.read_csv(data_path, low_memory=False)

    print("Engineering features...")
    df = engineer_features(df)

    df = df[(df['arr_delay_min'] >= -60) & (df['arr_delay_min'] <= 180)].copy()

    X_train, y_train, X_test, y_test = split_train_test(df)
    print(f"Data split → train: {X_train.shape}, test: {X_test.shape}")

    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('rf', RandomForestRegressor(random_state=42))
    ])

    param_dist = {
        'rf__n_estimators': [100, 200, 300],
        'rf__max_depth': [None, 10, 20, 30],
        'rf__min_samples_split': [2, 5, 10],
        'rf__min_samples_leaf': [1, 2, 4],
        'rf__max_features': [None, 'sqrt', 'log2']
    }

    tscv = TimeSeriesSplit(n_splits=3)

    search = RandomizedSearchCV(
        pipeline,
        param_distributions=param_dist,
        n_iter=20,
        cv=tscv,
        scoring='neg_mean_absolute_error',
        n_jobs=-1,
        random_state=42,
        verbose=1
    )

    print("Starting hyperparameter tuning...")
    search.fit(X_train, y_train)

    print(f"Best parameters: {search.best_params_}")
    best_model = search.best_estimator_

    preds = best_model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    print(f"Test MAE = {mae:.2f} min, RMSE = {rmse:.2f} min")

    model_path = base / 'arrival_delay_model.joblib'
    joblib.dump(best_model, model_path)
    print(f"✅ Model saved to {model_path}")


if __name__ == '__main__':
    main()
