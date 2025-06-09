# app.py
# A full e-commerce backend for Aro Bazzar with products, users, categories, and orders.
#
# To Run This Backend:
# 1. Activate virtual environment: source venv/bin/activate
# 2. Install dependencies: pip install Flask Flask-Cors Flask-Bcrypt Flask-JWT-Extended
# 3. Run from your terminal: python app.py
# 4. The server will start on http://127.0.0.1:5000

import sqlite3
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required, JWTManager, get_jwt, get_jwt_identity, verify_jwt_in_request
import os
from functools import wraps

# --- App Setup ---
app = Flask(__name__)
CORS(app) 
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True 
app.config["JWT_SECRET_KEY"] = os.urandom(24).hex()
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# --- Admin Required Decorator ---
def admin_required():
    """Custom decorator to protect routes that require admin privileges."""
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("is_admin"):
                return fn(*args, **kwargs)
            else:
                return jsonify({"error": "Administration rights required"}), 403
        return decorator
    return wrapper

# --- Database Setup ---
DB_NAME = "aro_bazzar.db"

def get_db_connection():
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    """Initializes the database and creates/updates tables and default admin."""
    conn = get_db_connection()
    cursor = conn.cursor()
    print("Initializing database...")
    
    # ## MODIFIED ## - Products Table with category_id
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT,
            price REAL NOT NULL, stock INTEGER NOT NULL DEFAULT 0, image_url TEXT,
            category_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')

    # Users Table with is_admin flag
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, is_admin INTEGER NOT NULL DEFAULT 0
        )
    ''')

    # ## NEW ## - Categories Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # ## NEW ## - Orders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            shipping_address TEXT NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'Pending',
            total_amount REAL NOT NULL
        )
    ''')
    
    # ## NEW ## - Order Items Table (Junction table)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price_at_purchase REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    # Create a default admin user if none exists
    cursor.execute("SELECT id FROM users WHERE is_admin = 1")
    if not cursor.fetchone():
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! No admin user found. Creating default admin...")
        username = "admin"
        password = "changethispassword"
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        cursor.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
            (username, password_hash)
        )
        print(f"!!! Default admin created with username: '{username}'")
        print(f"!!! Default admin password: '{password}'")
        print("!!! PLEASE LOG IN AND CHANGE THIS PASSWORD.")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# --- Auth & User Endpoints (Unchanged) ---
# [POST] /api/auth/login
@app.route('/api/auth/login', methods=['POST'])
def login_user():
    data = request.get_json()
    username = data['username']
    password = data['password']
    conn = get_db_connection()
    user_row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user_row and bcrypt.check_password_hash(user_row['password_hash'], password):
        additional_claims = {"is_admin": bool(user_row['is_admin'])}
        access_token = create_access_token(identity=user_row['id'], additional_claims=additional_claims)
        return jsonify(access_token=access_token), 200
    return jsonify({"error": "Invalid username or password"}), 401

# [POST] /api/users (Admin only)
@app.route('/api/users', methods=['POST'])
@admin_required()
def create_user_by_admin():
    data = request.get_json()
    username = data['username']
    password = data['password']
    is_admin = data.get('is_admin', False)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Username already exists"}), 409
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    cursor.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)", (username, password_hash, 1 if is_admin else 0))
    conn.commit()
    new_user_id = cursor.lastrowid
    conn.close()
    return jsonify({"id": new_user_id, "username": username, "is_admin": is_admin, "message": f"User '{username}' created"}), 201

# [GET] /api/users (Admin only)
@app.route('/api/users', methods=['GET'])
@admin_required()
def get_all_users():
    conn = get_db_connection()
    users_cursor = conn.execute('SELECT id, username, is_admin FROM users').fetchall()
    conn.close()
    return jsonify([dict(row) for row in users_cursor]), 200

# --- ## NEW ## - Category Management Endpoints ---
# [GET] /api/categories
@app.route('/api/categories', methods=['GET'])
def get_all_categories():
    conn = get_db_connection()
    categories_cursor = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    return jsonify([dict(row) for row in categories_cursor]), 200

# [POST] /api/categories (Admin only)
@app.route('/api/categories', methods=['POST'])
@admin_required()
def create_category():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Category name is required"}), 400
    name = data['name']
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return jsonify({"id": new_id, "name": name}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Category name already exists"}), 409

# [DELETE] /api/categories/<id> (Admin only)
@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
@admin_required()
def delete_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Optional: You might want to prevent deletion if products are using this category
    cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Category deleted"}), 200


# --- ## NEW ## - Order Management Endpoints ---
# [GET] /api/orders (Protected)
@app.route('/api/orders', methods=['GET'])
@jwt_required()
def get_all_orders():
    conn = get_db_connection()
    orders_cursor = conn.execute('SELECT * FROM orders ORDER BY order_date DESC').fetchall()
    conn.close()
    return jsonify([dict(row) for row in orders_cursor]), 200

# [GET] /api/orders/<id> (Protected)
@app.route('/api/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order_details(order_id):
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    items_cursor = conn.execute('''
        SELECT oi.quantity, oi.price_at_purchase, p.name 
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    ''', (order_id,)).fetchall()
    
    conn.close()
    order_details = dict(order)
    order_details['items'] = [dict(row) for row in items_cursor]
    return jsonify(order_details), 200

# [PUT] /api/orders/<id>/status (Admin only)
@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
@admin_required()
def update_order_status(order_id):
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({"error": "Status is required"}), 400
    
    new_status = data['status']
    # You might want to validate the status value
    conn = get_db_connection()
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Order {order_id} status updated to {new_status}"})


# --- ## MODIFIED ## - Product API Endpoints (with Category) ---

# [GET] /api/products (Publicly accessible)
@app.route('/api/products', methods=['GET'])
def get_all_products():
    conn = get_db_connection()
    # Join with categories to get category name
    products_cursor = conn.execute('''
        SELECT p.*, c.name as category_name 
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
    ''').fetchall()
    conn.close()
    return jsonify([dict(row) for row in products_cursor]), 200

# [POST] /api/products (Protected)
@app.route('/api/products', methods=['POST'])
@jwt_required()
def create_product():
    data = request.get_json()
    name = data['name']
    price = data['price']
    description = data.get('description', '')
    stock = data.get('stock', 0)
    image_url = data.get('image_url', '')
    category_id = data.get('category_id') # Can be null

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO products (name, description, price, stock, image_url, category_id) VALUES (?, ?, ?, ?, ?, ?)',
        (name, description, price, stock, image_url, category_id)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    # Fetch the created product to return it with all details
    # This is slightly inefficient but good for a consistent response
    return get_product(new_id)


# [GET] /api/products/<id>
@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    conn = get_db_connection()
    product_cursor = conn.execute('''
        SELECT p.*, c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.id = ?
    ''', (product_id,)).fetchone()
    conn.close()
    if product_cursor is None:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(dict(product_cursor)), 200

# [PUT] /api/products/<id> (Protected)
@app.route('/api/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No update data provided."}), 400

    conn = get_db_connection()
    if conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone() is None:
        conn.close()
        return jsonify({"error": "Product not found"}), 404

    # Handle nullable category_id
    if 'category_id' in data and data['category_id'] == '':
        data['category_id'] = None

    set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
    values = list(data.values())
    values.append(product_id)
    
    conn.execute(f"UPDATE products SET {set_clause} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return get_product(product_id)

# [DELETE] /api/products/<id> (Protected)
@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Product with ID {product_id} deleted"}), 200

# --- Main Execution Block ---
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
