import sys
import argparse
from datetime import datetime, timedelta
import random
import numpy as np
import pandas as pd
from sqlalchemy import text
from db import get_db_engine

# Define 10 sample products with prices and stock levels
PRODUCTS = [
    {"product_id": 1, "product_name": "Wireless Mouse", "category": "Electronics", "base_sales": 15, "trend": 0.1, "seasonality": 3.0, "price": 1299.00, "stock": 150},
    {"product_id": 2, "product_name": "Mechanical Keyboard", "category": "Electronics", "base_sales": 8, "trend": 0.05, "seasonality": 1.5, "price": 6999.00, "stock": 80},
    {"product_id": 3, "product_name": "USB-C Hub", "category": "Accessories", "base_sales": 12, "trend": 0.08, "seasonality": 2.0, "price": 2499.00, "stock": 120},
    {"product_id": 4, "product_name": "External SSD", "category": "Electronics", "base_sales": 6, "trend": 0.03, "seasonality": 1.0, "price": 9499.00, "stock": 60},
    {"product_id": 5, "product_name": "HDMI Cable", "category": "Accessories", "base_sales": 20, "trend": 0.12, "seasonality": 4.0, "price": 799.00, "stock": 250},
    {"product_id": 6, "product_name": "Ergonomic Chair", "category": "Office Supplies", "base_sales": 2, "trend": 0.01, "seasonality": 0.5, "price": 14999.00, "stock": 15},
    {"product_id": 7, "product_name": "Standing Desk", "category": "Office Supplies", "base_sales": 1, "trend": 0.005, "seasonality": 0.2, "price": 32999.00, "stock": 10},
    {"product_id": 8, "product_name": "LED Desk Lamp", "category": "Office Supplies", "base_sales": 5, "trend": 0.02, "seasonality": 1.0, "price": 1899.00, "stock": 90},
    {"product_id": 9, "product_name": "Noise Cancelling Headphones", "category": "Electronics", "base_sales": 4, "trend": 0.04, "seasonality": 0.8, "price": 16999.00, "stock": 40},
    {"product_id": 10, "product_name": "Laptop Stand", "category": "Accessories", "base_sales": 7, "trend": 0.03, "seasonality": 1.2, "price": 2199.00, "stock": 75},
]


def seed(force=False):
    engine = get_db_engine()

    with engine.connect() as conn:
        # Check if products already exist
        product_count = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
        if product_count > 0 and not force:
            print(f"Products table already has {product_count} rows. Merging/updating dynamic stock and price details...")
            for p in PRODUCTS:
                # Add random variation: Stock +/- 20%, Price +/- 5%
                random_stock = int(p["stock"] * random.uniform(0.8, 1.2))
                random_price = round(p["price"] * random.uniform(0.95, 1.05), 2)
                conn.execute(
                    text(
                        "UPDATE products SET current_stock = :current_stock, unit_price = :unit_price "
                        "WHERE product_id = :product_id"
                    ),
                    {
                        "product_id": p["product_id"],
                        "current_stock": random_stock,
                        "unit_price": random_price
                    }
                )
            conn.commit()
            print("Stock and price details dynamically merged/updated in the database!")
            return

        print("Clearing existing data...")
        # Clean existing tables in order due to foreign keys
        conn.execute(text("DELETE FROM demand_forecasts"))
        conn.execute(text("DELETE FROM sales_transactions"))
        conn.execute(text("DELETE FROM products"))
        conn.commit()

        # Insert products
        print("Inserting 10 products with randomized stock and price...")
        for p in PRODUCTS:
            random_stock = int(p["stock"] * random.uniform(0.8, 1.2))
            random_price = round(p["price"] * random.uniform(0.95, 1.05), 2)
            conn.execute(
                text(
                    "INSERT INTO products (product_id, product_name, category, current_stock, unit_price) "
                    "VALUES (:product_id, :product_name, :category, :current_stock, :unit_price)"
                ),
                {
                    "product_id": p["product_id"],
                    "product_name": p["product_name"],
                    "category": p["category"],
                    "current_stock": random_stock,
                    "unit_price": random_price
                }
            )
        conn.commit()

        # Generate sales transactions for the last 30 days
        # Ending on 2026-06-10 (current date matching system state)
        end_date = datetime(2026, 6, 10).date()
        start_date = end_date - timedelta(days=29)
        
        print(f"Generating daily sales transactions from {start_date} to {end_date}...")
        
        # We want to generate realistic data
        # np.random.seed(42)  # For reproducible seeding
        
        transactions_inserted = 0
        date_range = pd.date_range(start=start_date, end=end_date)
        
        for p in PRODUCTS:
            pid = p["product_id"]
            base = p["base_sales"]
            trend = p["trend"]
            seas_amp = p["seasonality"]
            
            for day_idx, current_date in enumerate(date_range):
                # Day of week seasonality: sales dip on weekends (Saturday=5, Sunday=6)
                dow = current_date.dayofweek
                if dow >= 5:
                    seasonality_factor = -seas_amp * 1.5
                else:
                    seasonality_factor = seas_amp * (1.0 + np.sin(2 * np.pi * dow / 5.0))
                
                # Add trend
                trend_factor = trend * day_idx
                
                # Random noise
                noise = np.random.normal(0, max(1, base * 0.15))
                
                # Calculate quantity
                qty = int(round(base + trend_factor + seasonality_factor + noise))
                qty = max(0, qty)
                
                # Don't log transactions if quantity is 0 (realistic)
                if qty > 0:
                    conn.execute(
                        text(
                            "INSERT INTO sales_transactions (product_id, quantity_sold, sale_date) "
                            "VALUES (:product_id, :quantity_sold, :sale_date)"
                        ),
                        {
                            "product_id": pid,
                            "quantity_sold": qty,
                            "sale_date": current_date.date()
                        }
                    )
                    transactions_inserted += 1
                    
        conn.commit()
        print(f"Database successfully seeded! Inserted {len(PRODUCTS)} products and {transactions_inserted} sales transactions.")


def main():
    parser = argparse.ArgumentParser(description="Seed database with mock inventory and sales data.")
    parser.add_argument("--force", action="store_true", help="Force clear and re-seed tables.")
    args = parser.parse_args()
    
    seed(force=args.force)


if __name__ == "__main__":
    main()