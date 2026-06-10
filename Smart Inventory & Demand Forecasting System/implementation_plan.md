# Smart Inventory & Demand Forecasting System - Database Connection & Full System Implementation

This plan resolves the connection issue ("No active connection found!" / access denied errors) and fully implements the Smart Inventory & Demand Forecasting System. Currently, all project files except the basic connection helper (`db.py`) are empty. We will build out a robust, production-grade system with database setup, realistic seed data, demand forecasting models, and evaluation routines.

## User Review Required

> [!IMPORTANT]
> The local MySQL server on port `3306` requires the password `"your_password"`. We will set this as the default local development fallback password in our configuration and support `.env` files for production overrides.
> 
> We will implement a Time-Series forecasting approach using `scikit-learn` (Random Forest Regressor) with lag features, rolling averages, and calendar features (day of week) to project 7-day demand forecasts for each product.

## Proposed Changes

### Configuration and Dependencies

---

#### [MODIFY] [requirements.txt](file:///c:/Users/cleme/Smart%20Inventory%20&%20Demand%20Forecasting%20System/requirements.txt)
- List all required Python packages for database operations, data processing, and machine learning:
  - `sqlalchemy`
  - `pymysql`
  - `cryptography`
  - `pandas`
  - `numpy`
  - `scikit-learn`
  - `python-dotenv`

#### [MODIFY] [db.py](file:///c:/Users/cleme/Smart%20Inventory%20&%20Demand%20Forecasting%20System/src/db.py)
- Import `dotenv` and call `load_dotenv()` to support environment variables from a `.env` file.
- Update `DB_PASSWORD` to fallback to `"your_password"` (the working password for the local MySQL instance) when `DB_PASSWORD` environment variable is not defined or is empty.

#### [NEW] [.env](file:///c:/Users/cleme/Smart%20Inventory%20&%20Demand%20Forecasting%20System/.env)
- Create a template/default `.env` file containing local MySQL configuration parameters:
  ```env
  DB_USER=root
  DB_PASSWORD=your_password
  DB_HOST=localhost
  DB_PORT=3306
  ```

### Database Schema and Initialization

---

#### [NEW] [schema.sql](file:///c:/Users/cleme/Smart%20Inventory%20&%20Demand%20Forecasting%20System/schema.sql)
- Define the relational database schema:
  - `products`: product_id, product_name, category
  - `sales_transactions`: transaction_id, product_id, quantity_sold, sale_date
  - `demand_forecasts`: forecast_id, product_id, forecast_date, predicted_demand, generated_at

#### [MODIFY] [setup_database.py](file:///c:/Users/cleme/Smart%20Inventory%20&%20Demand%20Forecasting%20System/src/setup_database.py)
- Connect to the core MySQL server.
- Run `CREATE DATABASE IF NOT EXISTS smart_inventory_db;`.
- Connect directly to the `smart_inventory_db` database.
- Read and parse `schema.sql` to execute schema table creation queries.

#### [MODIFY] [seed_data.py](file:///c:/Users/cleme/Smart%20Inventory%20&%20Demand%20Forecasting%20System/src/seed_data.py)
- Seed the database with realistic inventory data:
  - Populate 10 products across Electronics, Accessories, and Office Supplies.
  - Generate historical daily sales data for the last 30 days (from May 12, 2026 to June 10, 2026) using normal distribution with trend and weekly seasonality.
  - Safely write data to tables only if they are currently empty.

### Machine Learning and Forecast Pipeline

---

#### [MODIFY] [train_forecast.py](file:///c:/Users/cleme/Smart%20Inventory%20&%20Demand%20Forecasting%20System/src/train_forecast.py)
- Fetch product and daily sales transactions from the database.
- Process and format data into daily sales time-series for each product.
- Engineer time-series features:
  - Lag features (e.g., sales from 1, 2, 7 days ago).
  - Rolling average features (e.g., 3-day and 7-day rolling mean).
  - Calendar/date features (e.g., day of week).
- Train a `RandomForestRegressor` model for each product.
- Predict demand for the next 7 days (June 11, 2026 to June 17, 2026).
- Clear old forecasts for this future window and insert the new forecasts into `demand_forecasts` with a single generation timestamp.

#### [MODIFY] [evaluate_model.py](file:///c:/Users/cleme/Smart%20Inventory%20&%20Demand%20Forecasting%20System/src/evaluate_model.py)
- Implement a train-test split evaluation (training on the first 23 days of sales data, testing on the last 7 days of sales data).
- Train the model and make predictions on the test set.
- Calculate and report metrics: Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and Mean Absolute Percentage Error (MAPE) per product and overall averages.

#### [MODIFY] [README.md](file:///c:/Users/cleme/Smart%20Inventory%20&%20Demand%20Forecasting%20System/README.md)
- Write documentation detailing the workspace structure, how database credentials are set up, how to configure the environment, and step-by-step commands to run database setup, seeding, training, and evaluation.

## Verification Plan

### Automated Tests
- Run `.venv\Scripts\python.exe src/setup_database.py` to verify schema creation.
- Run `.venv\Scripts\python.exe src/seed_data.py` to populate data.
- Run `.venv\Scripts\python.exe src/train_forecast.py` to train and generate predictions.
- Run `.venv\Scripts\python.exe src/evaluate_model.py` to evaluate the model performance and view printed metrics.

### Manual Verification
- Execute custom SQL queries using Python/SQLAlchemy to check that rows are properly updated in `demand_forecasts`, `sales_transactions`, and `products`.
