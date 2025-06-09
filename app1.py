                                                                                                                                                                                                                                                                # app.py
# A full e-commerce backend for Aro Bazzar with products, users, categories, and orders.
# This version includes the fix for the 422 error on the dashboard.
#
# To Run This Backend:
# 1. Activate virtual environment: source venv/bin/activate
# 2. Install dependencies: pip install Flask Flask-Cors Flask-Bcrypt Flask-JWT-Extended
# 3. Save this entire code as 'app.py'.
# 4. Run on your server: python3 app.py
# 5. The server will start on http://0.0.0.0:5000

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
# Allow requests from any origin - for production, you might want to restrict this.
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
    conn = sqlite3.connect(DB_NAME, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    """Initializes the database and creates/updates tables and default admin."""
    conn = get_db_connection()
    cursor = conn.cursor()
    print("Initializing database...")
    
    # Products Table with category_id
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

    # Categories Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # Orders Table
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
    
    # Order Items Table (Junction table)
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

# --- Auth & User Endpoints ---
@app.route('/api/auth/login', methods=['POST'])
def login_user():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password are required"}), 400
    
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

@app.route('/api/users', methods=['POST'])
@admin_required()
def create_user_by_admin():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
         return jsonify({"error": "Username and password are required"}), 400

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

@app.route('/api/users', methods=['GET'])
@admin_required()
def get_all_users():
    conn = get_db_connection()
    users_cursor = conn.execute('SELECT id, username, is_admin FROM users').fetchall()
    conn.close()
    return jsonify([dict(row) for row in users_cursor]), 200

# --- Category Management Endpoints ---
@app.route('/api/categories', methods=['GET'])
def get_all_categories():
    conn = get_db_connection()
    categories_cursor = conn.execute('SELECT * FROM categories').fetchall()
    conn.close()
    return jsonify([dict(row) for row in categories_cursor]), 200

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

@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
@admin_required()
def delete_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM categories WHERE id = ?', (category_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Category deleted"}), 200


# --- Order Management Endpoints ---
@app.route('/api/orders', methods=['GET'])
@jwt_required()
def get_all_orders():
    # ## THIS IS THE CORRECTED FUNCTION ##
    try:
        conn = get_db_connection()
        orders_cursor = conn.execute('SELECT * FROM orders ORDER BY order_date DESC').fetchall()
        conn.close()
        
        # Manually build the list of orders to ensure correct data types
        orders = []
        for row in orders_cursor:
            orders.append({
                "id": row["id"],
                "customer_name": row["customer_name"],
                "customer_email": row["customer_email"],
                "shipping_address": row["shipping_address"],
                # Convert the datetime object to a standard ISO string
                "order_date": row["order_date"].isoformat() if row["order_date"] else None,
                "status": row["status"],
                "total_amount": row["total_amount"],
            })
            
        return jsonify(orders), 200
    except Exception as e:
        print(f"Error fetching orders: {e}") # Log the error to your server console
        return jsonify({"error": "Failed to retrieve orders", "details": str(e)}), 500

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
@admin_required()
def update_order_status(order_id):
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({"error": "Status is required"}), 400
    
    new_status = data['status']
    conn = get_db_connection()
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Order {order_id} status updated to {new_status}"})


# --- Product API Endpoints ---
@app.route('/api/products', methods=['GET'])
def get_all_products():
    conn = get_db_connection()
    products_cursor = conn.execute('''
        SELECT p.*, c.name as category_name 
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
    ''').fetchall()
    conn.close()
    return jsonify([dict(row) for row in products_cursor]), 200

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

@app.route('/api/products', methods=['POST'])
@jwt_required()
def create_product():
    data = request.get_json()
    name = data.get('name')
    price = data.get('price')
    if not name or price is None:
        return jsonify({"error": "Name and price are required fields."}), 400

    description = data.get('description', '')
    stock = data.get('stock', 0)
    image_url = data.get('image_url', '')
    category_id = data.get('category_id')

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
    return get_product(new_id)

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

    if 'category_id' in data and data['category_id'] == '':
        data['category_id'] = None

    set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
    values = list(data.values())
    values.append(product_id)
    
    conn.execute(f"UPDATE products SET {set_clause} WHERE id = ?", tuple(values))
    conn.commit()
    conn.close()
    return get_product(product_id)

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
    # Initialize the database when the server starts
    init_db()
    # Run the Flask app on all available network interfaces
    app.run(host='0.0.0.0', port=5000, debug=True)0
