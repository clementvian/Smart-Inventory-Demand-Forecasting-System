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
    """
    Convert raw sales data into a continuous daily time-series per product,
    filling days with zero sales.
    """
    # Get range of dates
    min_date = df["sale_date"].min()
    date_idx = pd.date_range(start=min_date, end=last_date, freq="D")
    
    product_series = {}
    
    # Process each product individually
    for product_id in df["product_id"].unique():
        prod_df = df[df["product_id"] == product_id]
        
        # Group by date and sum quantity (just in case there are multiple transactions)
        daily_sales = prod_df.groupby("sale_date")["quantity_sold"].sum()
        
        # Reindex to fill missing dates with 0 sales
        daily_sales = daily_sales.reindex(date_idx, fill_value=0)
        product_series[product_id] = daily_sales
        
    return product_series


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


def train_and_forecast():
    engine = get_db_engine()
    
    # 1. Fetch sales data
    sales_df = fetch_sales_data(engine)
    if sales_df.empty:
        print("No sales transactions found in the database. Please run seed_data.py first.")
        return
        
    last_date = sales_df["sale_date"].max()
    print(f"Latest sale date in database: {last_date.date()}")
    
    # 2. Reindex and fill missing days
    product_series = prepare_time_series(sales_df, last_date)
    
    forecast_duration = 7
    forecast_start = last_date + timedelta(days=1)
    forecast_dates = pd.date_range(start=forecast_start, periods=forecast_duration, freq="D")
    
    generation_time = datetime.now()
    all_forecasts = []
    
    # 3. Train a model and predict for each product
    for product_id, series in product_series.items():
        # Build features dataframe
        feat_df = create_features(series)
        
        # Drop rows with NaNs (due to lags and rolling windows)
        train_df = feat_df.dropna()
        
        if len(train_df) < 5:
            print(f"Product {product_id} has insufficient historical data to train a model.")
            continue
            
        X_train = train_df[["lag_1", "lag_2", "lag_7", "roll_3", "roll_7", "day_of_week"]]
        y_train = train_df["sales"]
        
        # Train RandomForestRegressor
        model = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
        model.fit(X_train, y_train)
        
        # Recursive forecasting for the next 7 days
        # We start with the tail of the historical sales series
        history = list(series.values)
        predictions = []
        
        for step in range(forecast_duration):
            # Compute lags for the current step
            lag_1 = history[-1]
            lag_2 = history[-2]
            lag_7 = history[-7]
            
            # Compute rolling averages
            roll_3 = np.mean(history[-3:])
            roll_7 = np.mean(history[-7:])
            
            # Day of week for forecast date
            forecast_date = forecast_dates[step]
            day_of_week = forecast_date.dayofweek
            
            # Construct features array
            features = np.array([[lag_1, lag_2, lag_7, roll_3, roll_7, day_of_week]])
            
            # Predict
            pred = model.predict(features)[0]
            # Post-process: demand must be non-negative and integer
            pred_int = int(round(max(0, pred)))
            
            predictions.append(pred_int)
            # Append prediction to history so it is used in subsequent lag computations
            history.append(pred_int)
            
            all_forecasts.append({
                "product_id": int(product_id),
                "forecast_date": forecast_date.date(),
                "predicted_demand": pred_int,
                "generated_at": generation_time
            })
            
        print(f"Product {product_id} Forecasted: {predictions}")
        
    # 4. Save forecasts to database
    with engine.connect() as conn:
        print("Clearing any conflicting future demand forecasts...")
        conn.execute(
            text("DELETE FROM demand_forecasts WHERE forecast_date >= :start_date"),
            {"start_date": forecast_start.date()}
        )
        conn.commit()
        
        print(f"Writing {len(all_forecasts)} demand forecasts to database...")
        for forecast in all_forecasts:
            conn.execute(
                text(
                    "INSERT INTO demand_forecasts (product_id, forecast_date, predicted_demand, generated_at) "
                    "VALUES (:product_id, :forecast_date, :predicted_demand, :generated_at)"
                ),
                forecast
            )
        conn.commit()
        
    print("Forecasting successfully completed and saved to the database!")


if __name__ == "__main__":
    train_and_forecast()