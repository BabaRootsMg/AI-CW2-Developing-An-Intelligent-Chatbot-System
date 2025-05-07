#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd
from math import sqrt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

# 1) Load consolidated data
csv_path = Path("training_data.csv.csv")
if not csv_path.exists():
    sys.exit(f"❌ Cannot find {csv_path} here.")

df = pd.read_csv(csv_path, low_memory=False)

# 2) Parse service date
df['date_of_service'] = pd.to_datetime(df['date_of_service'], format="%Y-%m-%d", errors="coerce")

# 3) Build full datetimes by normalizing times to HH:MM:SS,
#    then parsing with an explicit format.
date_str = df['date_of_service'].dt.strftime("%Y-%m-%d")

for col in [
    'scheduled_departure_time',
    'scheduled_arrival_time',
    'actual_departure_time',
    'actual_arrival_time'
]:
    # 3a) Convert to string and pad missing seconds
    time_str = df[col].astype(str)
    no_secs = time_str.str.match(r'^\d{1,2}:\d{2}$')  # e.g. "06:22"
    time_str.loc[no_secs] = time_str.loc[no_secs] + ':00'  # → "06:22:00"

    # 3b) Now parse with a fixed format
    df[col] = pd.to_datetime(
        date_str + ' ' + time_str,
        format="%Y-%m-%d %H:%M:%S",
        errors='coerce'
    )

# 4) Feature engineering
df['dep_delay_mins'] = (df['actual_departure_time'] - df['scheduled_departure_time']).dt.total_seconds() / 60
df['sched_duration_mins'] = (df['scheduled_arrival_time'] - df['scheduled_departure_time']).dt.total_seconds() / 60
df['arr_delay_mins'] = (df['actual_arrival_time'] - df['scheduled_arrival_time']).dt.total_seconds() / 60

# 5) Temporal features
df['day_of_week'] = df['date_of_service'].dt.dayofweek
df['month']       = df['date_of_service'].dt.month
df['dep_hour']    = df['scheduled_departure_time'].dt.hour

# 6) Drop rows missing core features
df = df.dropna(subset=[
    'dep_delay_mins',
    'sched_duration_mins',
    'arr_delay_mins',
    'day_of_week',
    'month',
    'dep_hour'
])

# 7) Prepare X/y
df['direction_bin'] = df['direction'].map({'LON→NOR': 0, 'NOR→LON': 1})
feature_cols = ['dep_delay_mins','sched_duration_mins','day_of_week','month','dep_hour','direction_bin']
X = df[feature_cols]
y = df['arr_delay_mins']

# 8) Chronological split
train_mask = df['date_of_service'].dt.year < 2024
X_train, X_test = X[train_mask], X[~train_mask]
y_train, y_test = y[train_mask], y[~train_mask]

print(f"Train rows: {len(X_train)}, Test rows: {len(X_test)}")
if len(X_train)==0 or len(X_test)==0:
    sys.exit("❌ No data to train/test on—check your dates.")

# 9) Train & evaluate
model = LinearRegression()
model.fit(X_train, y_train)
y_pred = model.predict(X_test)

mae  = mean_absolute_error(y_test, y_pred)
mse  = mean_squared_error(y_test, y_pred)
rmse = sqrt(mse)

print("\nBaseline Linear Regression Results:")
print(f"  MAE  = {mae:.2f} minutes")
print(f"  RMSE = {rmse:.2f} minutes")
