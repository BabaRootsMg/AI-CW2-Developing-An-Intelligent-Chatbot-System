from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.neighbors      import KNeighborsRegressor
from sklearn.ensemble       import ExtraTreesRegressor, HistGradientBoostingRegressor
from Task2.load_train_test_split import load_train_test_splits
from sklearn.linear_model import LinearRegression
from math import sqrt
from sklearn.metrics import mean_squared_error
from sklearn.ensemble import RandomForestRegressor


# 1) Load your train/test splits
#    Ensure master_schedule.csv is in the same directory as this file,
#    or give the correct relative path.
X_train, X_test, y_train, y_test = load_train_test_splits("training_data.csv")

print(f"Loaded X_train: {X_train.shape}, X_test: {X_test.shape}")

# 2) Define and train models
lr = LinearRegression()
lr.fit(X_train, y_train)

rf = RandomForestRegressor(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)

# 3) Evaluate
for name, model in [("LinearRegression", lr), ("RandomForest", rf)]:
    preds = model.predict(X_test)
    mae  = mean_absolute_error(y_test, preds)
    rmse = sqrt(mean_squared_error(y_test, preds))
    print(f"{name} → MAE: {mae:.2f} min, RMSE: {rmse:.2f} min")

# 2) Define models and their small hyper-grids
models = {
    "KNN": {
        "est": KNeighborsRegressor(),
        "params": {"n_neighbors": [5, 10, 20]}
    },
    "RandomForest": {
        "est": RandomForestRegressor(random_state=42),
        "params": {"n_estimators": [50, 100], "max_depth": [10, 20]}
    },
    "ExtraTrees": {
        "est": ExtraTreesRegressor(random_state=42),
        "params": {"n_estimators": [50, 100], "max_depth": [10, 20]}
    },
    "HistGB": {
        "est": HistGradientBoostingRegressor(random_state=42),
        "params": {"max_iter": [50, 100], "max_depth": [3, 7]}
    }
}

# 3) TimeSeriesSplit for date-ordered CV
tscv = TimeSeriesSplit(n_splits=5)

# 4) Loop through and run a quick GridSearchCV for each
best_models = {}
for name, cfg in models.items():
    gs = GridSearchCV(
        cfg["est"],
        cfg["params"],
        cv=tscv,
        scoring="neg_mean_absolute_error",
        n_jobs=-1
    )
    gs.fit(X_train, y_train)
    best_models[name] = gs

    print(f"{name} best MAE: {-gs.best_score_:.2f} "
          f"params: {gs.best_params_}")


for name, gs in best_models.items():
    best_est = gs.best_estimator_
    y_pred = best_est.predict(X_test)
    mae  = mean_absolute_error(y_test, y_pred)
    rmse = sqrt(mean_squared_error(y_test, y_pred))
    print(f"{name} on 2024 → MAE={mae:.2f}, RMSE={rmse:.2f}")