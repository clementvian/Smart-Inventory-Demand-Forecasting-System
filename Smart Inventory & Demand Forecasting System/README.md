# Smart Inventory & Demand Forecasting System

A production-grade inventory management and forecasting intelligence suite built on top of MySQL, SQLAlchemy, Pandas, and Scikit-Learn.

This system creates a continuous daily history of sales, trains a dedicated Time-Series forecasting model for each product using a `RandomForestRegressor` and lag/rolling-mean features, generates a recursive 7-day future demand forecast, and calculates accuracy metrics (MAE, RMSE, MAPE) via date-split backtesting.

---

## Workspace Architecture

- **`schema.sql`**: MySQL schema DDL containing tables for `products`, `sales_transactions`, and `demand_forecasts`.
- **`src/db.py`**: Central engine helper utilizing SQLAlchemy and `python-dotenv` with a fallback configuration for local development.
- **`src/setup_database.py`**: Initializes the database and executes DDL scripts inside MySQL.
- **`src/seed_data.py`**: Generates a 30-day time-series of mock sales transactions with weekly seasonality, trends, and Gaussian noise.
- **`src/train_forecast.py`**: Processes sales data, trains forecasting models, and saves future predictions into MySQL.
- **`src/evaluate_model.py`**: Backtests forecasting accuracy using a train-test date split (first 23 days for training, last 7 days for testing) and displays product-level error metrics.

---

## Environment Setup & Configuration

### 1. Requirements Installation
Ensure that you are running in your virtual environment and install the required dependencies:
```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Configuration (`.env`)
Create a `.env` file in the root directory of the project to set up the connection details. A local development default file is provided:
```env
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
```
*(Note: If `DB_PASSWORD` is omitted, the configuration automatically falls back to `"your_password"`, which matches the password of the local MySQL service instance.)*

---

## Execution Guide

Run the following scripts sequentially inside the system workspace directory:

### Step 1: Database Setup
Build the database and construct the necessary tables:
```bash
.venv\Scripts\python.exe src/setup_database.py
```

### Step 2: Seed the Database
Seed the database with products and 30 days of sales transactions:
```bash
.venv\Scripts\python.exe src/seed_data.py --force
```
*(Passing the `--force` flag ensures any pre-existing records in these tables are wiped clean before insertion.)*

### Step 3: Run Demand Forecasting
Train the models and predict demand for the next 7 days:
```bash
.venv\Scripts\python.exe src/train_forecast.py
```
This generates and saves forecasts into the `demand_forecasts` table, where they can be queried by down-stream inventory and supply chain applications.

### Step 4: Evaluate Models
Evaluate prediction accuracy using a backtest window (training on the first 23 days of sales, testing on the last 7 days of sales):
```bash
.venv\Scripts\python.exe src/evaluate_model.py
```
This will print a formatted evaluation metrics table showing MAE (Mean Absolute Error), RMSE (Root Mean Squared Error), and MAPE (Mean Absolute Percentage Error) per product.