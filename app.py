# app.py
# An e-commerce backend for Aro Bazzar with product and user management.
#
# To Run This Backend:
# 1. Activate virtual environment: source venv/bin/activate
# 2. Install dependencies: pip install Flask Flask-Cors Flask-Bcrypt Flask-JWT-Extended
# 3. Run from your terminal: python app.py
# 4. The server will start on http://127.0.0.1:5000

import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt         ## NEW ##
from flask_jwt_extended import create_access_token, jwt_required, JWTManager ## NEW ##
import os ## NEW ## for generating secret key

# --- App Setup ---
app = Flask(__name__)
# Allow requests from any origin - adjust for production if needed
CORS(app) 
# Provides better JSON error messages
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True 

# ## NEW ## - Configuration for JWT and Bcrypt
# A strong, secret key is required for JWT. 
# In a real production app, use a more secure method to generate and store this.
app.config["JWT_SECRET_KEY"] = os.urandom(24).hex()
bcrypt = Bcrypt(app)
jwt = JWTManager(app)


# --- Database Setup ---
DB_NAME = "aro_bazzar.db"

def get_db_connection():
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    print("Initializing database...")
    
    # Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            image_url TEXT
        )
    ''')

    # ## NEW ## - Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# --- ## NEW ## - Authentication API Endpoints ---

# [POST] /api/auth/register
# Creates a new user.
@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """Registers a new user."""
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password are required"}), 400

    username = data['username']
    password = data['password']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if user already exists
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Username already exists"}), 409 # 409 Conflict

    # Hash the password and create the new user
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
    conn.commit()
    conn.close()

    return jsonify({"message": f"User '{username}' registered successfully"}), 201

# [POST] /api/auth/login
# Authenticates a user and returns a JWT token.
@app.route('/api/auth/login', methods=['POST'])
def login_user():
    """Logs in a user and provides an access token."""
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password are required"}), 400
    
    username = data['username']
    password = data['password']

    conn = get_db_connection()
    user_row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    if user_row and bcrypt.check_password_hash(user_row['password_hash'], password):
        # Pass the user's identity (their ID or username) to create the token
        access_token = create_access_token(identity=user_row['id'])
        return jsonify(access_token=access_token), 200
    
    return jsonify({"error": "Invalid username or password"}), 401 # 401 Unauthorized


# --- Product API Endpoints (Now with Security) ---

# [GET] /api/products (Publicly accessible)
@app.route('/api/products', methods=['GET'])
def get_all_products():
    """Fetches all products from the database."""
    try:
        conn = get_db_connection()
        products_cursor = conn.execute('SELECT * FROM products').fetchall()
        conn.close()
        products = [dict(row) for row in products_cursor]
        return jsonify(products), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve products", "details": str(e)}), 500

# [GET] /api/products/<id> (Publicly accessible)
@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Fetches a single product by its ID."""
    try:
        conn = get_db_connection()
        product_cursor = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
        conn.close()
        if product_cursor is None:
            return jsonify({"error": "Product not found"}), 404
        return jsonify(dict(product_cursor)), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve product", "details": str(e)}), 500

# [POST] /api/products (Protected) ## NEW ## - Added @jwt_required()
@app.route('/api/products', methods=['POST'])
@jwt_required()
def create_product():
    """Creates a new product. Requires authentication."""
    new_product_data = request.get_json()
    if not new_product_data or 'name' not in new_product_data or 'price' not in new_product_data:
        return jsonify({"error": "Missing required fields: 'name' and 'price'."}), 400
    
    try:
        name = new_product_data['name']
        description = new_product_data.get('description', '')
        price = new_product_data['price']
        stock = new_product_data.get('stock', 0)
        image_url = new_product_data.get('image_url', '')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO products (name, description, price, stock, image_url) VALUES (?, ?, ?, ?, ?)',
            (name, description, price, stock, image_url)
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()

        created_product = { "id": new_id, "name": name, "description": description, "price": price, "stock": stock, "image_url": image_url }
        return jsonify(created_product), 201
    except Exception as e:
        return jsonify({"error": "Failed to create product", "details": str(e)}), 500

# [PUT] /api/products/<id> (Protected) ## NEW ## - Added @jwt_required()
@app.route('/api/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    """Updates an existing product's details. Requires authentication."""
    update_data = request.get_json()
    if not update_data:
        return jsonify({"error": "No update data provided."}), 400

    try:
        conn = get_db_connection()
        if conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "Product not found"}), 404

        set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
        values = list(update_data.values())
        values.append(product_id)
        
        conn.execute(f"UPDATE products SET {set_clause} WHERE id = ?", tuple(values))
        conn.commit()

        updated_product_cursor = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
        conn.close()
        
        return jsonify(dict(updated_product_cursor)), 200
    except Exception as e:
        return jsonify({"error": "Failed to update product", "details": str(e)}), 500

# [DELETE] /api/products/<id> (Protected) ## NEW ## - Added @jwt_required()
@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    """Deletes a product from the database. Requires authentication."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone() is None:
            conn.close()
            return jsonify({"error": "Product not found"}), 404
        
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        conn.close()
        
        return jsonify({"message": f"Product with ID {product_id} deleted successfully."}), 200
    except Exception as e:
        return jsonify({"error": "Failed to delete product", "details": str(e)}), 500


# --- Main Execution Block ---
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
