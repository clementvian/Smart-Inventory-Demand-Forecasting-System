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

class SalesTransaction(db.Model):
    __tablename__ = "sales_transactions"
    transaction_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.product_id"))
    quantity_sold = db.Column(db.Integer, nullable=False)
    sale_date = db.Column(db.Date, nullable=False)

@app.route("/")
def dashboard():
    # If logged in as admin, redirect to admin dashboard
    if session.get("logged_in") and session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
        
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
        forecasts=forecast_data,
        role=session.get("role", "guest"),
        logged_in=session.get("logged_in", False)
    )

@app.route("/admin")
def admin_dashboard():
    if not session.get("logged_in") or session.get("role") != "admin":
        return redirect(url_for("login", next="/admin"))
        
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
        forecasts=forecast_data,
        role="admin",
        logged_in=True
    )

@app.route("/api/products")
def api_products():
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

@app.route("/api/forecasts")
def api_forecasts():
    forecasts = db.session.scalars(db.select(DemandForecast)).all()
    return jsonify([
        {
            "product_id": f.product_id,
            "date": f.forecast_date.strftime("%Y-%m-%d"),
            "predicted_demand": f.predicted_demand,
            "generated_at": f.generated_at.strftime("%Y-%m-%d %H:%M:%S") if f.generated_at else None
        } for f in forecasts
    ])

@app.route("/api/checkout", methods=["POST"])
def api_checkout():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized. Please login to complete checkout."}), 401
    
    if session.get("role") not in ["customer", "admin"]:
        return jsonify({"error": "Forbidden. Customer role required."}), 403

    data = request.get_json()
    if not data or "items" not in data:
        return jsonify({"error": "Invalid request payload. 'items' is required."}), 400
    
    items = data["items"]
    if not items:
        return jsonify({"error": "Cart is empty."}), 400
        
    try:
        from datetime import date
        today = date.today()
        
        products_to_update = []
        transactions_to_add = []
        
        for item in items:
            p_id = item.get("product_id")
            qty = item.get("quantity")
            if not p_id or qty is None or qty <= 0:
                return jsonify({"error": "Invalid item fields. Each item must have product_id and positive quantity."}), 400
                
            product = db.session.get(Product, p_id)
            if not product:
                return jsonify({"error": f"Product with ID {p_id} not found."}), 404
            if product.current_stock < qty:
                return jsonify({"error": f"Insufficient stock for '{product.product_name}'. Available: {product.current_stock}, requested: {qty}."}), 400
                
            products_to_update.append((product, qty))
            transactions_to_add.append(
                SalesTransaction(product_id=p_id, quantity_sold=qty, sale_date=today)
            )
            
        for product, qty in products_to_update:
            product.current_stock -= qty
            
        for transaction in transactions_to_add:
            db.session.add(transaction)
            
        db.session.commit()
        return jsonify({"success": True, "message": "Checkout completed successfully."})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/api/admin/restock", methods=["POST"])
def api_restock():
    if not session.get("logged_in") or session.get("role") != "admin":
        return jsonify({"error": "Forbidden. Admin access required."}), 403
        
    data = request.get_json()
    if not data or "product_id" not in data or "quantity" not in data:
        return jsonify({"error": "Invalid request payload. 'product_id' and 'quantity' are required."}), 400
        
    p_id = data["product_id"]
    qty = data["quantity"]
    
    if not p_id or qty is None or qty <= 0:
        return jsonify({"error": "Invalid fields. Provide valid product_id and positive quantity."}), 400
        
    try:
        product = db.session.get(Product, p_id)
        if not product:
            return jsonify({"error": f"Product with ID {p_id} not found."}), 404
            
        product.current_stock += qty
        db.session.commit()
        return jsonify({"success": True, "message": f"Successfully restocked {qty} units of '{product.product_name}'."})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("dashboard"))
    
    error = None
    next_page = request.args.get("next") or request.form.get("next")
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username == "admin" and password == "admin":
            session["logged_in"] = True
            session["role"] = "admin"
            if next_page:
                return redirect(next_page)
            return redirect(url_for("admin_dashboard"))
            
        elif username == "customer" and password == "customer":
            session["logged_in"] = True
            session["role"] = "customer"
            if next_page:
                return redirect(next_page)
            return redirect(url_for("dashboard"))
            
        else:
            error = "Invalid username or password."
            
    return render_template("login.html", error=error, next=next_page)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)