import os
from flask import Flask, render_template, jsonify, session, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from src.db import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "smart-inventory-secret-key-123")
app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_recycle": 280}
db = SQLAlchemy(app)

class Product(db.Model):
    __tablename__ = "products"
    product_id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))
    current_stock = db.Column(db.Integer, default=0)
    unit_price = db.Column(db.Numeric(10, 2), default=0.0)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class DemandForecast(db.Model):
    __tablename__ = "demand_forecasts"
    forecast_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.product_id"))
    forecast_date = db.Column(db.Date, nullable=False)
    predicted_demand = db.Column(db.Integer, nullable=False)
    generated_at = db.Column(db.DateTime, default=db.func.current_timestamp())

@app.route("/")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    products = db.session.scalars(db.select(Product)).all()
    forecasts = db.session.scalars(db.select(DemandForecast)).all()

    product_data = [
        {
            "id": p.product_id,
            "name": p.product_name,
            "category": p.category,
            "current_stock": p.current_stock,
            "unit_price": float(p.unit_price) if p.unit_price else 0.0
        }
        for p in products
    ]

    forecast_data = [
        {
            "product_id": f.product_id,
            "date": f.forecast_date.strftime("%Y-%m-%d"),
            "predicted_demand": f.predicted_demand,
            "generated_at": f.generated_at.strftime("%Y-%m-%d %H:%M:%S") if f.generated_at else None
        }
        for f in forecasts
    ]

    return render_template(
        "smart-inventory-dashboard.html",
        products=product_data,
        forecasts=forecast_data
    )

@app.route("/api/products")
def api_products():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    products = db.session.scalars(db.select(Product)).all()
    return jsonify([
        {
            "id": p.product_id,
            "name": p.product_name,
            "category": p.category,
            "current_stock": p.current_stock,
            "unit_price": float(p.unit_price) if p.unit_price else 0.0
        } for p in products
    ])

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "admin":
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password."
            
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)