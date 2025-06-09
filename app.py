# app.py
# A simple e-commerce backend for Aro Bazzar using Flask.
#
# To Run This Backend:
# 1. Make sure you have Python installed.
# 2. Install Flask: pip install Flask
# 3. Save this code as 'app.py'.
# 4. Run from your terminal: python app.py
# 5. The server will start on http://127.0.0.1:5000
#
# You can then use a tool like Postman or curl to test the API endpoints.

import sqlite3
from flask_cors import CORS
from flask import Flask, request, jsonify

# --- App Setup ---
app = Flask(__name__)
# Provides better JSON error messages
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True 

# --- Database Setup ---
DB_NAME = "aro_bazzar.db"

def get_db_connection():
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    # This allows you to access columns by name (like a dictionary)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    """Initializes the database and creates the 'products' table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    print("Initializing database...")
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
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# --- API Endpoints (Routes) ---

# [GET] /api/products
# Retrieves a list of all products.
@app.route('/api/products', methods=['GET'])
def get_all_products():
    """Fetches all products from the database."""
    try:
        conn = get_db_connection()
        products_cursor = conn.execute('SELECT * FROM products').fetchall()
        conn.close()
        
        # Convert list of Row objects to a list of dictionaries
        products = [dict(row) for row in products_cursor]
        
        return jsonify(products), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve products", "details": str(e)}), 500

# [GET] /api/products/<id>
# Retrieves a single product by its ID.
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

# [POST] /api/products
# Creates a new product.
@app.route('/api/products', methods=['POST'])
def create_product():
    """Creates a new product from the incoming JSON data."""
    new_product_data = request.get_json()

    if not new_product_data or not 'name' in new_product_data or not 'price' in new_product_data:
        return jsonify({"error": "Missing required fields: 'name' and 'price' are mandatory."}), 400
    
    try:
        name = new_product_data['name']
        description = new_product_data.get('description', '') # Optional field
        price = new_product_data['price']
        stock = new_product_data.get('stock', 0) # Optional field, defaults to 0
        image_url = new_product_data.get('image_url', '') # Optional field

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO products (name, description, price, stock, image_url) VALUES (?, ?, ?, ?, ?)',
            (name, description, price, stock, image_url)
        )
        conn.commit()
        
        # Get the ID of the newly created product
        new_id = cursor.lastrowid
        conn.close()

        # Create the response object
        created_product = {
            "id": new_id,
            "name": name,
            "description": description,
            "price": price,
            "stock": stock,
            "image_url": image_url
        }

        return jsonify(created_product), 201 # 201 Created
    except Exception as e:
        return jsonify({"error": "Failed to create product", "details": str(e)}), 500

# [PUT] /api/products/<id>
# Updates an existing product.
@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Updates an existing product's details."""
    update_data = request.get_json()

    if not update_data:
        return jsonify({"error": "No update data provided."}), 400

    try:
        conn = get_db_connection()
        # First, check if the product exists
        product_cursor = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
        if product_cursor is None:
            conn.close()
            return jsonify({"error": "Product not found"}), 404

        # Dynamically build the SET part of the SQL query
        # This allows for updating only the fields that are sent in the request
        set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
        values = list(update_data.values())
        values.append(product_id) # For the WHERE clause
        
        query = f"UPDATE products SET {set_clause} WHERE id = ?"
        
        conn.execute(query, tuple(values))
        conn.commit()

        # Fetch the updated product to return it in the response
        updated_product_cursor = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
        conn.close()
        
        return jsonify(dict(updated_product_cursor)), 200

    except Exception as e:
        return jsonify({"error": "Failed to update product", "details": str(e)}), 500

# [DELETE] /api/products/<id>
# Deletes a product.
@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Deletes a product from the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if product exists before deleting
        cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if product is None:
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
    # Initialize the database when the server starts
    init_db()
    # Run the Flask app
    # debug=True enables auto-reloading when you save the file.
    app.run(debug=True, port=5000)

