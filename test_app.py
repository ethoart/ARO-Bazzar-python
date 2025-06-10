import unittest
import json
import sqlite3 # Make sure to import sqlite3
from app import app as flask_app, init_db, get_db_connection, bcrypt # Import bcrypt from app
import app as app_module # Import the app module itself
import os
import datetime # Add this import at the top of test_app.py

class AppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_db_name = app_module.DB_NAME  # Store original DB_NAME from app.py
        app_module.DB_NAME = "test_aro_bazzar.db"   # Override DB_NAME in the imported app module

        flask_app.config['TESTING'] = True
        flask_app.config['JWT_SECRET_KEY'] = 'test_secret_key'
        cls.client = flask_app.test_client()

        # init_db() will now use the overridden app_module.DB_NAME
        # No need to pass db_name to init_db if it uses the global app_module.DB_NAME

    @classmethod
    def tearDownClass(cls):
        app_module.DB_NAME = cls.original_db_name # Restore original DB_NAME
        if os.path.exists("test_aro_bazzar.db"): # Path to remove is "test_aro_bazzar.db"
            os.remove("test_aro_bazzar.db")

    def setUp(self):
        # Now init_db uses the overridden app_module.DB_NAME for the test DB
        init_db() # This creates tables in "test_aro_bazzar.db"

        # Create default admin and regular user for tests
        with flask_app.app_context(): # Use flask_app here
            conn = get_db_connection() # This will use the overridden app_module.DB_NAME
            cursor = conn.cursor()

            # Admin user for testing admin-only endpoints
            cursor.execute("SELECT id FROM users WHERE username = ?", ('testadmin',))
            if not cursor.fetchone():
                # Use bcrypt from the app module
                password_hash = bcrypt.generate_password_hash('testpassword').decode('utf-8')
                cursor.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)", ('testadmin', password_hash))

            # Regular user for testing non-admin and general authenticated endpoints
            cursor.execute("SELECT id FROM users WHERE username = ?", ('testuser',))
            if not cursor.fetchone():
                # Use bcrypt from the app module
                password_hash = bcrypt.generate_password_hash('testpassword').decode('utf-8')
                cursor.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 0)", ('testuser', password_hash))

            conn.commit()
            conn.close()

    def tearDown(self):
        # Connect to the test DB and drop all tables to ensure test isolation
        conn = get_db_connection() # Uses overridden app.DB_NAME
        cursor = conn.cursor()
        # Order of dropping matters due to foreign key constraints
        cursor.execute("DROP TABLE IF EXISTS order_items")
        cursor.execute("DROP TABLE IF EXISTS orders")
        cursor.execute("DROP TABLE IF EXISTS products")
        cursor.execute("DROP TABLE IF EXISTS categories")
        cursor.execute("DROP TABLE IF EXISTS users")
        conn.commit()
        conn.close()

    def _get_admin_token(self):
        response = self.client.post('/api/auth/login', json={'username': 'testadmin', 'password': 'testpassword'})
        data = json.loads(response.data.decode())
        self.assertIn('access_token', data, "Failed to get admin token") # Add assert message
        return data['access_token']

    def _get_user_token(self):
        response = self.client.post('/api/auth/login', json={'username': 'testuser', 'password': 'testpassword'})
        data = json.loads(response.data.decode())
        self.assertIn('access_token', data, "Failed to get user token") # Add assert message
        return data['access_token']

    # --- Test Cases Start Here ---

    def test_001_admin_login(self):
        response = self.client.post('/api/auth/login', json={'username': 'testadmin', 'password': 'testpassword'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode())
        self.assertIn('access_token', data)

    def test_002_user_login(self):
        response = self.client.post('/api/auth/login', json={'username': 'testuser', 'password': 'testpassword'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode())
        self.assertIn('access_token', data)

    def test_003_login_invalid_credentials(self):
        response = self.client.post('/api/auth/login', json={'username': 'wronguser', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data.decode())
        self.assertEqual(data['error'], 'Invalid username or password')

    def test_004_get_all_users_as_admin(self):
        admin_token = self._get_admin_token()
        response = self.client.get('/api/users', headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode())
        self.assertIsInstance(data, list)
        # At least the admin and regular user we created should be there
        self.assertTrue(len(data) >= 2)
        usernames = [user['username'] for user in data]
        self.assertIn('testadmin', usernames)
        self.assertIn('testuser', usernames)

    def test_005_get_all_users_as_non_admin(self):
        user_token = self._get_user_token()
        response = self.client.get('/api/users', headers={'Authorization': f'Bearer {user_token}'})
        self.assertEqual(response.status_code, 403) # Forbidden
        data = json.loads(response.data.decode())
        self.assertEqual(data['error'], 'Administration rights required')

    def test_006_create_user_by_admin(self):
        admin_token = self._get_admin_token()
        new_user_data = {'username': 'newlycreateduser', 'password': 'newpassword123', 'is_admin': False}
        response = self.client.post('/api/users', json=new_user_data, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode())
        self.assertEqual(data['username'], 'newlycreateduser')
        self.assertFalse(data['is_admin'])

        # Verify user is in the database
        conn = get_db_connection() # Connects to test_aro_bazzar.db
        user_row = conn.execute("SELECT * FROM users WHERE username = ?", ('newlycreateduser',)).fetchone()
        conn.close()
        self.assertIsNotNone(user_row)
        self.assertEqual(user_row['username'], 'newlycreateduser')
        self.assertEqual(user_row['is_admin'], 0)

    def test_007_create_user_by_admin_username_exists(self):
        admin_token = self._get_admin_token()
        existing_user_data = {'username': 'testuser', 'password': 'newpassword123'}
        response = self.client.post('/api/users', json=existing_user_data, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 409) # Conflict
        data = json.loads(response.data.decode())
        self.assertEqual(data['error'], 'Username already exists')

    def test_008_create_user_by_non_admin(self):
        user_token = self._get_user_token()
        new_user_data = {'username': 'anotheruser', 'password': 'password123'}
        response = self.client.post('/api/users', json=new_user_data, headers={'Authorization': f'Bearer {user_token}'})
        self.assertEqual(response.status_code, 403) # Forbidden

    # --- Category Management Tests ---
    def test_009_get_all_categories_no_auth(self):
        response = self.client.get('/api/categories')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode())
        self.assertIsInstance(data, list)

    def test_010_create_category_as_admin(self):
        admin_token = self._get_admin_token()
        new_category_data = {'name': 'Electronics'}
        response = self.client.post('/api/categories', json=new_category_data, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode())
        self.assertEqual(data['name'], 'Electronics')
        self.assertIn('id', data)

        # Verify category is in the database
        conn = get_db_connection()
        category_row = conn.execute("SELECT * FROM categories WHERE name = ?", ('Electronics',)).fetchone()
        conn.close()
        self.assertIsNotNone(category_row)
        self.assertEqual(category_row['name'], 'Electronics')

    def test_011_create_category_as_non_admin(self):
        user_token = self._get_user_token()
        new_category_data = {'name': 'Books'}
        response = self.client.post('/api/categories', json=new_category_data, headers={'Authorization': f'Bearer {user_token}'})
        self.assertEqual(response.status_code, 403) # Forbidden

    def test_012_create_category_name_exists(self):
        admin_token = self._get_admin_token()
        # First, create a category
        self.client.post('/api/categories', json={'name': 'Apparel'}, headers={'Authorization': f'Bearer {admin_token}'})
        # Then, attempt to create it again
        response = self.client.post('/api/categories', json={'name': 'Apparel'}, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 409) # Conflict
        data = json.loads(response.data.decode())
        self.assertEqual(data['error'], 'Category name already exists')

    def test_013_create_category_missing_name(self):
        admin_token = self._get_admin_token()
        response = self.client.post('/api/categories', json={}, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 400) # Bad Request
        data = json.loads(response.data.decode())
        self.assertEqual(data['error'], 'Category name is required')

    def test_014_delete_category_as_admin(self):
        admin_token = self._get_admin_token()
        # First, create a category to delete
        cat_response = self.client.post('/api/categories', json={'name': 'ToDelete'}, headers={'Authorization': f'Bearer {admin_token}'})
        category_id = json.loads(cat_response.data.decode())['id']

        delete_response = self.client.delete(f'/api/categories/{category_id}', headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(delete_response.status_code, 200)
        data = json.loads(delete_response.data.decode())
        self.assertEqual(data['message'], 'Category deleted')

        # Verify category is removed from the database
        conn = get_db_connection()
        category_row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        conn.close()
        self.assertIsNone(category_row)

    def test_015_delete_category_as_non_admin(self):
        admin_token = self._get_admin_token()
        user_token = self._get_user_token()
        # First, create a category
        cat_response = self.client.post('/api/categories', json={'name': 'NoDeletePermission'}, headers={'Authorization': f'Bearer {admin_token}'})
        category_id = json.loads(cat_response.data.decode())['id']

        delete_response = self.client.delete(f'/api/categories/{category_id}', headers={'Authorization': f'Bearer {user_token}'})
        self.assertEqual(delete_response.status_code, 403) # Forbidden

    def test_016_delete_non_existent_category(self):
        admin_token = self._get_admin_token()
        response = self.client.delete('/api/categories/9999', headers={'Authorization': f'Bearer {admin_token}'}) # Assuming 9999 does not exist
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data.decode())
        self.assertEqual(data['error'], 'Category not found')

    # --- Product Management Tests ---
    def _create_sample_category(self, name="Sample Category"):
        admin_token = self._get_admin_token()
        response = self.client.post('/api/categories', json={'name': name}, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 201, "Failed to create sample category for product tests")
        return json.loads(response.data.decode())['id']

    def test_017_get_all_products_no_auth(self):
        response = self.client.get('/api/products')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode())
        self.assertIsInstance(data, list)

    def test_018_get_one_product_no_auth(self):
        admin_token = self._get_admin_token()
        category_id = self._create_sample_category()
        product_data = {'name': 'Test Laptop', 'price': 1200.00, 'description': 'A good laptop', 'stock': 10, 'category_id': category_id}
        create_response = self.client.post('/api/products', json=product_data, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(create_response.status_code, 200) # create_product returns 200 with product details
        product_id = json.loads(create_response.data.decode())['id']

        response = self.client.get(f'/api/products/{product_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode())
        self.assertEqual(data['name'], 'Test Laptop')

    def test_019_get_non_existent_product(self):
        response = self.client.get('/api/products/99999') # Assuming 99999 does not exist
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data.decode())
        self.assertEqual(data['error'], 'Product not found')

    def test_020_create_product_as_admin(self):
        admin_token = self._get_admin_token()
        category_id = self._create_sample_category(name="Tech Gadgets")
        product_data = {'name': 'Super Phone', 'price': 799.99, 'description': 'Latest model', 'stock': 50, 'category_id': category_id}
        response = self.client.post('/api/products', json=product_data, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 200) # create_product now returns 200 with the product
        data = json.loads(response.data.decode())
        self.assertEqual(data['name'], 'Super Phone')
        self.assertEqual(data['category_id'], category_id)
        self.assertEqual(data['category_name'], "Tech Gadgets") # Check category_name join

    def test_021_create_product_as_non_admin(self):
        user_token = self._get_user_token()
        category_id = self._create_sample_category(name="Books Category")
        product_data = {'name': 'Bestseller Novel', 'price': 19.99, 'category_id': category_id}
        response = self.client.post('/api/products', json=product_data, headers={'Authorization': f'Bearer {user_token}'})
        self.assertEqual(response.status_code, 403) # Forbidden due to @admin_required

    def test_022_create_product_missing_name_or_price(self):
        admin_token = self._get_admin_token()
        category_id = self._create_sample_category()
        # Missing name
        product_data_no_name = {'price': 9.99, 'category_id': category_id}
        response_no_name = self.client.post('/api/products', json=product_data_no_name, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response_no_name.status_code, 400)
        data_no_name = json.loads(response_no_name.data.decode())
        self.assertEqual(data_no_name['error'], 'Name and price are required fields.')
        # Missing price
        product_data_no_price = {'name': 'Cheap Item', 'category_id': category_id}
        response_no_price = self.client.post('/api/products', json=product_data_no_price, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response_no_price.status_code, 400)
        data_no_price = json.loads(response_no_price.data.decode())
        self.assertEqual(data_no_price['error'], 'Name and price are required fields.')

    def test_023_update_product_as_admin(self):
        admin_token = self._get_admin_token()
        category_id = self._create_sample_category()
        product_data = {'name': 'Old Name', 'price': 10.00, 'category_id': category_id}
        create_response = self.client.post('/api/products', json=product_data, headers={'Authorization': f'Bearer {admin_token}'})
        product_id = json.loads(create_response.data.decode())['id']

        update_data = {'name': 'New Name', 'price': 12.50}
        response = self.client.put(f'/api/products/{product_id}', json=update_data, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode())
        self.assertEqual(data['name'], 'New Name')
        self.assertEqual(data['price'], 12.50)

    def test_024_update_product_as_non_admin(self):
        admin_token = self._get_admin_token()
        user_token = self._get_user_token()
        category_id = self._create_sample_category()
        product_data = {'name': 'Another Product', 'price': 5.00, 'category_id': category_id}
        create_response = self.client.post('/api/products', json=product_data, headers={'Authorization': f'Bearer {admin_token}'})
        product_id = json.loads(create_response.data.decode())['id']

        update_data = {'name': 'Attempted Update Name'}
        response = self.client.put(f'/api/products/{product_id}', json=update_data, headers={'Authorization': f'Bearer {user_token}'})
        self.assertEqual(response.status_code, 403) # Forbidden

    def test_025_update_non_existent_product(self):
        admin_token = self._get_admin_token()
        update_data = {'name': 'No Product Here'}
        response = self.client.put('/api/products/99999', json=update_data, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data.decode())
        self.assertEqual(data['error'], 'Product not found')

    def test_026_update_product_clear_category(self):
        admin_token = self._get_admin_token()
        category_id = self._create_sample_category(name="Initial Category")
        product_data = {'name': 'Product With Category', 'price': 25.00, 'category_id': category_id}
        create_response = self.client.post('/api/products', json=product_data, headers={'Authorization': f'Bearer {admin_token}'})
        product_id = json.loads(create_response.data.decode())['id']
        self.assertEqual(json.loads(create_response.data.decode())['category_id'], category_id)

        update_data = {'category_id': ''} # Sending empty string to clear category
        response = self.client.put(f'/api/products/{product_id}', json=update_data, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode())
        self.assertIsNone(data['category_id'])
        self.assertIsNone(data['category_name'])


    def test_027_delete_product_as_admin(self):
        admin_token = self._get_admin_token()
        category_id = self._create_sample_category()
        product_data = {'name': 'Product to Delete', 'price': 1.00, 'category_id': category_id}
        create_response = self.client.post('/api/products', json=product_data, headers={'Authorization': f'Bearer {admin_token}'})
        product_id = json.loads(create_response.data.decode())['id']

        response = self.client.delete(f'/api/products/{product_id}', headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode())
        self.assertEqual(data['message'], f'Product with ID {product_id} deleted')

        # Verify product is removed
        get_response = self.client.get(f'/api/products/{product_id}')
        self.assertEqual(get_response.status_code, 404)

    def test_028_delete_product_as_non_admin(self):
        admin_token = self._get_admin_token()
        user_token = self._get_user_token()
        category_id = self._create_sample_category()
        product_data = {'name': 'Protected Product', 'price': 1.00, 'category_id': category_id}
        create_response = self.client.post('/api/products', json=product_data, headers={'Authorization': f'Bearer {admin_token}'})
        product_id = json.loads(create_response.data.decode())['id']

        response = self.client.delete(f'/api/products/{product_id}', headers={'Authorization': f'Bearer {user_token}'})
        self.assertEqual(response.status_code, 403) # Forbidden

    def test_029_delete_non_existent_product(self):
        admin_token = self._get_admin_token()
        response = self.client.delete('/api/products/99999', headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data.decode())
        self.assertEqual(data['error'], 'Product not found')

    def _create_sample_order(self, customer_name="Test Customer", total_amount=100.00, status="Pending"):
        # Note: Orders are not created via API in the current app.py, so we'll insert directly for testing.
        # This helper assumes an admin might want to create an order or it's done via a different process.
        # For testing get_all_orders and update_order_status, we need orders in the DB.
        conn = get_db_connection()
        cursor = conn.cursor()
        # Using a specific datetime object for testing the isoformat conversion
        order_date = datetime.datetime(2023, 1, 15, 10, 30, 0)
        cursor.execute(
            "INSERT INTO orders (customer_name, customer_email, shipping_address, order_date, status, total_amount) VALUES (?, ?, ?, ?, ?, ?)",
            (customer_name, f"{customer_name.replace(' ', '').lower()}@example.com", "123 Test St", order_date, status, total_amount)
        )
        conn.commit()
        order_id = cursor.lastrowid
        conn.close()
        return order_id, order_date

    # --- Order Management Tests ---
    def test_030_get_all_orders_as_admin(self):
        admin_token = self._get_admin_token()
        _, order_date = self._create_sample_order(customer_name="Admin Order Test")

        response = self.client.get('/api/orders', headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode())
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)
        # Check for the specific order and correct date formatting
        found_order = next((order for order in data if order['customer_name'] == "Admin Order Test"), None)
        self.assertIsNotNone(found_order)
        self.assertEqual(found_order['order_date'], order_date.isoformat())

    def test_031_get_all_orders_as_user(self):
        user_token = self._get_user_token()
        self._create_sample_order(customer_name="User Order Test") # Create an order to ensure list is not empty

        response = self.client.get('/api/orders', headers={'Authorization': f'Bearer {user_token}'})
        self.assertEqual(response.status_code, 200) # @jwt_required allows any authenticated user
        data = json.loads(response.data.decode())
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)

    def test_032_get_all_orders_no_auth(self):
        response = self.client.get('/api/orders')
        self.assertEqual(response.status_code, 401) # Unauthorized, @jwt_required

    def test_033_update_order_status_as_admin(self):
        admin_token = self._get_admin_token()
        order_id, _ = self._create_sample_order(status="Pending")

        update_data = {'status': 'Shipped'}
        response = self.client.put(f'/api/orders/{order_id}/status', json=update_data, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode())
        self.assertEqual(data['message'], f"Order {order_id} status updated to Shipped")

        # Verify status in database
        conn = get_db_connection()
        order_row = conn.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
        conn.close()
        self.assertEqual(order_row['status'], 'Shipped')

    def test_034_update_order_status_as_non_admin(self):
        admin_token = self._get_admin_token() # To create order
        user_token = self._get_user_token()
        order_id, _ = self._create_sample_order(status="Pending") # Admin creates order

        update_data = {'status': 'Processing'}
        response = self.client.put(f'/api/orders/{order_id}/status', json=update_data, headers={'Authorization': f'Bearer {user_token}'})
        self.assertEqual(response.status_code, 403) # Forbidden

    def test_035_update_status_non_existent_order(self):
        admin_token = self._get_admin_token()
        update_data = {'status': 'Cancelled'}
        response = self.client.put('/api/orders/99999/status', json=update_data, headers={'Authorization': f'Bearer {admin_token}'}) # Assuming 99999 does not exist
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data.decode())
        self.assertEqual(data['error'], 'Order not found')

    def test_036_update_order_status_missing_status(self):
        admin_token = self._get_admin_token()
        order_id, _ = self._create_sample_order(status="Pending")

        response = self.client.put(f'/api/orders/{order_id}/status', json={}, headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 400) # Bad Request
        data = json.loads(response.data.decode())
        self.assertEqual(data['error'], 'Status is required')

    def test_037_get_all_orders_datetime_conversion_check(self):
        # This test specifically verifies the fix for the 422 error (datetime conversion)
        admin_token = self._get_admin_token()
        # Create an order with a known datetime object
        conn = get_db_connection()
        cursor = conn.cursor()
        specific_datetime = datetime.datetime(2024, 3, 10, 14, 45, 30)
        cursor.execute(
            "INSERT INTO orders (customer_name, customer_email, shipping_address, order_date, status, total_amount) VALUES (?, ?, ?, ?, ?, ?)",
            ("Datetime Test User", "dt@example.com", "422 Fix St", specific_datetime, "Completed", 50.00)
        )
        conn.commit()
        conn.close()

        response = self.client.get('/api/orders', headers={'Authorization': f'Bearer {admin_token}'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode())

        found_order = next((order for order in data if order['customer_name'] == "Datetime Test User"), None)
        self.assertIsNotNone(found_order, "Order for datetime conversion test not found.")
        # Ensure the order_date string is a valid ISO format of the original datetime
        self.assertEqual(found_order['order_date'], specific_datetime.isoformat())

if __name__ == '__main__':
    unittest.main()
