import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import text
from sklearn.ensemble import RandomForestRegressor
from db import get_db_engine


def fetch_sales_data(engine):
    """Fetch all products and sales transactions from the database."""
    query = """
        SELECT s.product_id, p.product_name, s.quantity_sold, s.sale_date
        FROM sales_transactions s
        JOIN products p ON s.product_id = p.product_id
        ORDER BY s.sale_date ASC
    """
    df = pd.read_sql(query, engine)
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    return df


def prepare_time_series(df, last_date):
    """Convert raw sales data into a continuous daily time-series per product."""
    min_date = df["sale_date"].min()
    date_idx = pd.date_range(start=min_date, end=last_date, freq="D")
    
    product_series = {}
    product_names = {}
    
    for product_id in df["product_id"].unique():
        prod_df = df[df["product_id"] == product_id]
        product_names[product_id] = prod_df["product_name"].iloc[0]
        
        daily_sales = prod_df.groupby("sale_date")["quantity_sold"].sum()
        daily_sales = daily_sales.reindex(date_idx, fill_value=0)
        product_series[product_id] = daily_sales
        
    return product_series, product_names


def create_features(series):
    """Create lagged and rolling window features from a pandas Series."""
    df = pd.DataFrame(index=series.index)
    df["sales"] = series.values
    
    # Lag features
    df["lag_1"] = series.shift(1)
    df["lag_2"] = series.shift(2)
    df["lag_7"] = series.shift(7)
    
    # Rolling mean features (shifted to avoid data leakage)
    df["roll_3"] = series.shift(1).rolling(window=3).mean()
    df["roll_7"] = series.shift(1).rolling(window=7).mean()
    
    # Calendar features
    df["day_of_week"] = df.index.dayofweek
    
    return df


def calculate_metrics(actual, predicted):
    """Calculate MAE, RMSE, and MAPE."""
    actual = np.array(actual)
    predicted = np.array(predicted)
    
    mae = np.mean(np.abs(actual - predicted))
    rmse = np.sqrt(np.mean((actual - predicted) ** 2))
    
    # Avoid division by zero in MAPE
    mask = actual > 0
    if np.sum(mask) > 0:
        mape = np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100
    else:
        mape = 0.0
        
    return mae, rmse, mape


def evaluate():
    engine = get_db_engine()
    
    # 1. Fetch sales data
    sales_df = fetch_sales_data(engine)
    if sales_df.empty:
        print("No sales transactions found in the database. Please run seed_data.py first.")
        return
        
    last_date = sales_df["sale_date"].max()
    product_series, product_names = prepare_time_series(sales_df, last_date)
    
    # 2. Define train-test split boundaries
    # Historical data covers 30 days. Test window is the last 7 days (e.g., June 4 to June 10, 2026)
    test_duration = 7
    train_end_date = last_date - timedelta(days=test_duration)
    test_start_date = train_end_date + timedelta(days=1)
    
    print("\n" + "="*60)
    print("BACKTEST EVALUATION DETAILS")
    print(f"Total Date Range: {sales_df['sale_date'].min().date()} to {last_date.date()}")
    print(f"Training Range:   {sales_df['sale_date'].min().date()} to {train_end_date.date()}")
    print(f"Testing Range:    {test_start_date.date()} to {last_date.date()}")
    print("="*60 + "\n")
    
    product_evaluations = []
    
    # 3. Evaluate each product
    for product_id, series in product_series.items():
        prod_name = product_names[product_id]
        
        # Build features on full series
        feat_df = create_features(series)
        
        # Split features based on dates
        train_feat_df = feat_df.loc[:train_end_date].dropna()
        test_feat_df = feat_df.loc[test_start_date:]
        
        if len(train_feat_df) < 5:
            print(f"Skipping product '{prod_name}' (ID: {product_id}) - insufficient training data.")
            continue
            
        # Fit model on training data
        X_train = train_feat_df[["lag_1", "lag_2", "lag_7", "roll_3", "roll_7", "day_of_week"]]
        y_train = train_feat_df["sales"]
        
        model = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
        model.fit(X_train, y_train)
        
        # Recursive forecast on test set (to avoid using future actual sales as lags)
        # We start our prediction history with the data up to the end of training
        history = list(series.loc[:train_end_date].values)
        actual_sales = list(series.loc[test_start_date:].values)
        predicted_sales = []
        
        test_dates = pd.date_range(start=test_start_date, periods=test_duration, freq="D")
        
        for step in range(test_duration):
            lag_1 = history[-1]
            lag_2 = history[-2]
            lag_7 = history[-7]
            
            roll_3 = np.mean(history[-3:])
            roll_7 = np.mean(history[-7:])
            
            day_of_week = test_dates[step].dayofweek
            
            features = np.array([[lag_1, lag_2, lag_7, roll_3, roll_7, day_of_week]])
            pred = model.predict(features)[0]
            pred_int = int(round(max(0, pred)))
            
            predicted_sales.append(pred_int)
            history.append(pred_int)
            
        # Compute metrics
        mae, rmse, mape = calculate_metrics(actual_sales, predicted_sales)
        
        product_evaluations.append({
            "product_id": product_id,
            "product_name": prod_name,
            "actuals": actual_sales,
            "predictions": predicted_sales,
            "mae": mae,
            "rmse": rmse,
            "mape": mape
        })
        
    # 4. Display results in a structured table
    print(f"{'Product Name':<30} | {'MAE':<8} | {'RMSE':<8} | {'MAPE (%)':<10}")
    print("-"*65)
    
    total_mae = 0.0
    total_rmse = 0.0
    total_mape = 0.0
    count = len(product_evaluations)
    
    for eval_item in product_evaluations:
        mae, rmse, mape = eval_item["mae"], eval_item["rmse"], eval_item["mape"]
        total_mae += mae
        total_rmse += rmse
        total_mape += mape
        
        print(f"{eval_item['product_name']:<30} | {mae:<8.2f} | {rmse:<8.2f} | {mape:<10.2f}%")
        
    print("-"*65)
    print(f"{'Overall Average':<30} | {total_mae/count:<8.2f} | {total_rmse/count:<8.2f} | {total_mape/count:<10.2f}%")
    print("="*65 + "\n")


if __name__ == "__main__":
    evaluate()