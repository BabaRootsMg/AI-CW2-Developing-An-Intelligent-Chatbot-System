import pandas as pd
import glob
import os

# 1. Locate all CSV files in the data directory
data_dir = '/mnt/data'
csv_files = glob.glob(os.path.join(data_dir, '*service_details*.csv'))

# 2. Load and concatenate into a single DataFrame
df_list = []
for file in csv_files:
    df = pd.read_csv(file, parse_dates=['scheduled_arrival', 'actual_arrival'])
    df_list.append(df)
data = pd.concat(df_list, ignore_index=True)

# 3. Compute delay in minutes (actual - scheduled)
data['delay_minutes'] = (data['actual_arrival'] - data['scheduled_arrival']).dt.total_seconds() / 60

# 4. Extract features
#    a. Scheduled arrival as datetime (already parsed)
#    b. Time of day (hour)
data['arrival_hour'] = data['scheduled_arrival'].dt.hour

#    c. Previous delay: group by service identifier (e.g., 'service_id') and date
#       then shift delay_minutes
if 'service_id' in data.columns:
    data = data.sort_values(['service_id', 'date', 'scheduled_arrival'])
    data['prev_delay'] = data.groupby('service_id')['delay_minutes'].shift(1)
else:
    # Fallback: overall previous delay
    data = data.sort_values('scheduled_arrival')
    data['prev_delay'] = data['delay_minutes'].shift(1)

# Fill NaNs in prev_delay with 0 (first service of the day or unknown)
data['prev_delay'].fillna(0, inplace=True)

# 5. Define X (features) and y (target)
feature_cols = ['scheduled_arrival', 'arrival_hour', 'prev_delay']
X = data[feature_cols]
y = data['delay_minutes']

# Display the shapes of X and y
print(f"Features (X) shape: {X.shape}")
print(f"Target (y) shape:   {y.shape}")

# Optional: preview the first few rows
print("\nSample features:")
print(X.head())

# If you plan to use datetime directly, consider converting scheduled_arrival
# to numeric (e.g., timestamp) before feeding into most ML models:
X_numeric = X.copy()
X_numeric['scheduled_arrival'] = X_numeric['scheduled_arrival'].astype(int) // 10**9
print("\nNumeric features preview:")
print(X_numeric.head())
