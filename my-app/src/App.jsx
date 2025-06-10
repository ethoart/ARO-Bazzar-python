import React, { useState, useEffect, useMemo } from 'react';
import './App.css';

// Helper function to format currency
const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
};

// Constants for user roles
const USER_ROLES = {
  ADMIN: 'admin',
  USER: 'user',
};

// SVG Icons (simple examples)
const PlusIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
    <path d="M8 0a1 1 0 0 1 1 1v6h6a1 1 0 1 1 0 2H9v6a1 1 0 1 1-2 0V9H1a1 1 0 0 1 0-2h6V1a1 1 0 0 1 1-1z"/>
  </svg>
);

const EditIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
    <path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5L13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V12h2.293L12.793 5.5z"/>
  </svg>
);

const DeleteIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
    <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>
    <path fillRule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4L4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
  </svg>
);


// Mock Firebase SDK (replace with actual Firebase integration)
const mockFirebase = {
  initializeApp: (config) => {
    console.log("Firebase initialized with config:", config);
    return {
      auth: () => ({
        onAuthStateChanged: (callback) => {
          // Simulate user login
          setTimeout(() => callback({ uid: 'test-user', email: 'user@example.com', role: USER_ROLES.ADMIN }), 1000);
          return () => {}; // Unsubscribe function
        },
        signInWithEmailAndPassword: (email, password) => {
          return new Promise((resolve, reject) => {
            if (email === 'admin@example.com' && password === 'password') {
              resolve({ user: { uid: 'test-admin', email: 'admin@example.com', role: USER_ROLES.ADMIN } });
            } else if (email === 'user@example.com' && password === 'password'){
              resolve({ user: { uid: 'test-user', email: 'user@example.com', role: USER_ROLES.USER } });
            }
            else {
              reject(new Error('Invalid credentials'));
            }
          });
        },
        signOut: () => Promise.resolve(),
      }),
      firestore: () => ({
        collection: (name) => ({
          doc: (id) => ({
            get: () => {
              if (name === 'users' && id === 'test-user') {
                return Promise.resolve({ exists: true, data: () => ({ role: USER_ROLES.USER, name: 'Test User' }) });
              }
              if (name === 'users' && id === 'test-admin') {
                return Promise.resolve({ exists: true, data: () => ({ role: USER_ROLES.ADMIN, name: 'Test Admin' }) });
              }
              return Promise.resolve({ exists: false });
            },
            set: (data) => {
                console.log(`Firestore: Set data for ${name}/${id}`, data);
                return Promise.resolve();
            }
          }),
          get: () => {
            if (name === 'products') {
              return Promise.resolve({
                docs: [
                  { id: 'prod1', data: () => ({ name: 'Laptop', price: 1200, stock: 50 }) },
                  { id: 'prod2', data: () => ({ name: 'Mouse', price: 25, stock: 200 }) },
                  { id: 'prod3', data: () => ({ name: 'Keyboard', price: 75, stock: 100 }) },
                ],
              });
            }
            if (name === 'orders') {
              return Promise.resolve({
                docs: [
                  { id: 'order1', data: () => ({ userId: 'test-user', items: [{productId: 'prod1', quantity: 1}], total: 1200, status: 'Pending' }) },
                  { id: 'order2', data: () => ({ userId: 'test-admin', items: [{productId: 'prod2', quantity: 2}], total: 50, status: 'Shipped' }) },
                ],
              });
            }
            return Promise.resolve({ docs: [] });
          },
          add: (data) => {
            console.log(`Firestore: Added data to ${name}`, data);
            const id = `new-${Date.now()}`;
            // Update mock data source if needed or rely on re-fetch for simplicity in mock
            return Promise.resolve({ id });
          },
          delete: (id) => {
            console.log(`Firestore: Deleted ${name}/${id}`);
            return Promise.resolve();
          }
        }),
      }),
    };
  }
};


// Hook to initialize Firebase (or mock)
const useFirebase = () => {
  const [db, setDb] = useState(null); // db state was missing, added based on usage
  const [auth, setAuth] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [isAuthReady, setIsAuthReady] = useState(false);
  const [error, setError] = useState(null);
  // Removed `loading` state as `isAuthReady` handles the initial user data loading signal

  useEffect(() => {
    // This firebaseConfig should ideally be defined outside the hook or passed as a prop.
    // For this fix, it's hardcoded as it was in the search block.
    const firebaseConfig = {
      apiKey: "AIzaSyD2gT5p_0Bvz6wA4FUL4GVwP8yWL3czitk",
      authDomain: "arobazzar-fa1d1.firebaseapp.com",
      projectId: "arobazzar-fa1d1",
      storageBucket: "arobazzar-fa1d1.firebasestorage.app",
      messagingSenderId: "138031032851",
      appId: "1:138031032851:web:ee41a64cd88b0dbc82ede6",
      measurementId: "G-L05S3N8RGK"
    };
    const app = mockFirebase.initializeApp(firebaseConfig);
    const authInstance = app.auth();
    const firestoreDb = app.firestore(); // Renamed to avoid conflict with db state variable

    setAuth(authInstance);
    setDb(firestoreDb); // Set the db state

    const unsubAuth = authInstance.onAuthStateChanged((user) => {
      let unsubUserDoc = () => {}; // Initialize an empty unsubscribe function for the user document

      if (user) {
        // Path: /artifacts/${appId}/public/data/users/${user.uid}
        // Using the mock Firebase structure, this translates to nested collections and docs:
        const userDocRef = firestoreDb
          .collection('artifacts')
          .doc(firebaseConfig.appId) // appId from firebaseConfig
          .collection('public')
          .doc('data')
          .collection('users')
          .doc(user.uid);

        unsubUserDoc = userDocRef.onSnapshot(
          (docSnap) => {
            if (docSnap.exists()) { // Make sure mock docSnap has exists()
              setCurrentUser({ uid: user.uid, email: user.email, ...docSnap.data() });
            } else {
              setCurrentUser({ uid: user.uid, email: user.email, role: null });
            }
            setIsAuthReady(true);
          },
          (err) // Renamed from 'error' to 'err' to avoid conflict with 'error' state
          ) => {
            console.error("Error listening to user document:", err);
            setCurrentUser(null); // Set currentUser to null on error
            setIsAuthReady(true);
          }
        );
        return unsubUserDoc; // Return cleanup func for user doc listener from onAuthStateChanged
      } else {
        // User is null (logged out)
        setCurrentUser(null);
        setIsAuthReady(true);
      }
      // If user is null, unsubUserDoc remains the initial empty function,
      // which is fine as there's nothing to unsubscribe from.
      // The previous unsubUserDoc (if any from a previous auth state) would have been called
      // at the beginning of onAuthStateChanged if it were structured to do so,
      // but the current instructions are to return it from here.
      return unsubUserDoc;
    });

    // The main cleanup function for useEffect
    return () => {
      unsubAuth();
      // unsubUserDoc is handled by being returned from onAuthStateChanged,
      // and Firebase SDK manages calling it when onAuthStateChanged itself is cleaned up (by unsubAuth).
    };
  }, []); // Empty dependency array means this runs once on mount

  // Return db, auth, currentUser, isAuthReady, error, and appId
  return { db, auth, currentUser, isAuthReady, error, appId: firebaseConfig.appId };
};


// Hook for fetching data from Firestore
const useFirestoreData = (db, collectionName, filterFn = () => true) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!db) return;
    setLoading(true);
    const unsubscribe = db.collection(collectionName).onSnapshot(
        (snapshot) => {
            const fetchedData = snapshot.docs
                .map(doc => ({ id: doc.id, ...doc.data() }))
                .filter(filterFn);
            setData(fetchedData);
            setLoading(false);
        },
        (err) => {
            console.error(`Error fetching ${collectionName}:`, err);
            setError(err);
            setLoading(false);
        }
    );
    // Fallback for mock data if onSnapshot is not available or for initial load
     const fetchData = async () => {
        try {
            const snapshot = await db.collection(collectionName).get();
            const fetchedData = snapshot.docs
                .map(doc => ({ id: doc.id, ...doc.data() }))
                .filter(filterFn);
            setData(fetchedData);
        } catch (err) {
            console.error(`Error fetching ${collectionName} (fallback):`, err);
            setError(err);
        } finally {
            setLoading(false);
        }
    };

    // If using the mock which doesn't have real-time onSnapshot, call fetchData
    if (db.collection(collectionName).onSnapshot === undefined || !db.collection(collectionName).onSnapshot) {
         fetchData();
         return () => {}; // No real unsubscribe for mock get()
    }


    return () => unsubscribe && unsubscribe();
  }, [db, collectionName, filterFn]);

  return { data, loading, error, setData }; // Allow manual update of data for optimistic UI
};


// --- Components ---

// Loading Spinner Component
const LoadingSpinner = () => (
  <div className="spinner-container">
    <div className="spinner"></div>
    <p>Loading...</p>
  </div>
);

// Error Message Component
const ErrorMessage = ({ message }) => (
  <div className="error-message">
    <p>Error: {message}</p>
  </div>
);


// Login Component
const LoginPage = ({ auth }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await auth.signInWithEmailAndPassword(email, password);
      // Auth state change will handle redirect or UI update
    } catch (err) {
      setError(err.message);
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <h2>Login</h2>
      <form onSubmit={handleLogin}>
        <div>
          <label>Email:</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label>Password:</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        {error && <p className="error-message">{error}</p>}
        <button type="submit" disabled={loading}>{loading ? 'Logging in...' : 'Login'}</button>
      </form>
       <p>Demo Admin: admin@example.com / password</p>
       <p>Demo User: user@example.com / password</p>
    </div>
  );
};

// Navigation Bar Component
const Navbar = ({ currentUser, onLogout }) => {
  if (!currentUser) return null;

  return (
    <nav className="navbar">
      <span>Welcome, {currentUser.name || currentUser.email} ({currentUser.role})</span>
      <button onClick={onLogout}>Logout</button>
    </nav>
  );
};

// Product Management Component (Admin only)
const ProductManagement = ({ db, productsData, setProductsData }) => {
  const [name, setName] = useState('');
  const [price, setPrice] = useState('');
  const [stock, setStock] = useState('');
  const [editingProduct, setEditingProduct] = useState(null); // null or product object
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');


  const handleAddProduct = async (e) => {
    e.preventDefault();
    if (!name || !price || !stock) {
        setError("All fields are required.");
        return;
    }
    setIsLoading(true);
    setError('');
    try {
      const newProduct = { name, price: parseFloat(price), stock: parseInt(stock) };
      const docRef = await db.collection('products').add(newProduct);
      setProductsData(prev => [...prev, { id: docRef.id, ...newProduct }]); // Optimistic update
      setName(''); setPrice(''); setStock('');
    } catch (err) {
      console.error("Error adding product:", err);
      setError("Failed to add product.");
    } finally {
        setIsLoading(false);
    }
  };

  const handleDeleteProduct = async (productId) => {
    setIsLoading(true);
    setError('');
    try {
        await db.collection('products').doc(productId).delete();
        setProductsData(prev => prev.filter(p => p.id !== productId)); // Optimistic update
    } catch (err) {
        console.error("Error deleting product:", err);
        setError("Failed to delete product.");
    } finally {
        setIsLoading(false);
    }
  };

  const handleEditProduct = (product) => {
    setEditingProduct(product);
    setName(product.name);
    setPrice(product.price.toString());
    setStock(product.stock.toString());
  };

  const handleUpdateProduct = async (e) => {
    e.preventDefault();
    if (!editingProduct) return;
    setIsLoading(true);
    setError('');
    try {
        const updatedProduct = { name, price: parseFloat(price), stock: parseInt(stock) };
        await db.collection('products').doc(editingProduct.id).set(updatedProduct, { merge: true });
        setProductsData(prev => prev.map(p => p.id === editingProduct.id ? { ...p, ...updatedProduct } : p));
        setEditingProduct(null);
        setName(''); setPrice(''); setStock('');
    } catch (err) {
        console.error("Error updating product:", err);
        setError("Failed to update product.");
    } finally {
        setIsLoading(false);
    }
  };


  return (
    <div className="admin-section product-management">
      <h3>{editingProduct ? "Edit Product" : "Add New Product"}</h3>
      {error && <p className="error-message">{error}</p>}
      <form onSubmit={editingProduct ? handleUpdateProduct : handleAddProduct}>
        <div>
          <label>Name:</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div>
          <label>Price ($):</label>
          <input type="number" value={price} onChange={(e) => setPrice(e.target.value)} required min="0.01" step="0.01" />
        </div>
        <div>
          <label>Stock:</label>
          <input type="number" value={stock} onChange={(e) => setStock(e.target.value)} required min="0" step="1"/>
        </div>
        <button type="submit" disabled={isLoading}>
            {isLoading ? (editingProduct ? 'Updating...' : 'Adding...') : (editingProduct ? 'Update Product' : 'Add Product')}
             <PlusIcon />
        </button>
        {editingProduct && <button type="button" onClick={() => { setEditingProduct(null); setName(''); setPrice(''); setStock('');}} disabled={isLoading}>Cancel Edit</button>}
      </form>

      <h4>Existing Products</h4>
      {productsData.loading && <LoadingSpinner />}
      {productsData.error && <ErrorMessage message={productsData.error.message} />}
      {!productsData.loading && !productsData.error && (
        <ul className="product-list">
          {productsData.data.map(product => (
            <li key={product.id}>
              <span>{product.name} - {formatCurrency(product.price)} (Stock: {product.stock})</span>
              <div>
                <button onClick={() => handleEditProduct(product)} disabled={isLoading}><EditIcon /></button>
                <button onClick={() => handleDeleteProduct(product.id)} disabled={isLoading}><DeleteIcon /></button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};


// User Dashboard Component
const UserDashboard = ({ db, currentUser, products }) => {
  const [cart, setCart] = useState({}); // { productId: quantity }
  const [feedback, setFeedback] = useState(''); // For order success/error

  const handleAddToCart = (productId, availableStock) => {
    setCart(prevCart => {
      const currentQuantity = prevCart[productId] || 0;
      if (currentQuantity < availableStock) {
        return { ...prevCart, [productId]: currentQuantity + 1 };
      }
      setFeedback(`Cannot add more ${products.find(p=>p.id === productId)?.name}; stock limit reached.`);
      return prevCart; // Return previous cart if stock limit reached
    });
  };

  const handleRemoveFromCart = (productId) => {
    setCart(prevCart => {
      const newCart = { ...prevCart };
      if (newCart[productId] > 1) {
        newCart[productId]--;
      } else {
        delete newCart[productId];
      }
      return newCart;
    });
  };

  const calculateTotal = useMemo(() => {
    return Object.entries(cart).reduce((total, [productId, quantity]) => {
      const product = products.find(p => p.id === productId);
      return total + (product ? product.price * quantity : 0);
    }, 0);
  }, [cart, products]);

  const handlePlaceOrder = async () => {
    if (Object.keys(cart).length === 0) {
      setFeedback("Your cart is empty.");
      return;
    }
    setFeedback('Placing order...');
    try {
      const orderItems = Object.entries(cart).map(([productId, quantity]) => ({
        productId,
        quantity,
        priceAtPurchase: products.find(p => p.id === productId)?.price // Store price at time of order
      }));
      const orderTotal = calculateTotal;

      // Basic validation: Check stock before placing order (server should re-validate)
      for (const item of orderItems) {
          const product = products.find(p => p.id === item.productId);
          if (!product || product.stock < item.quantity) {
              setFeedback(`Not enough stock for ${product?.name || 'item'}. Order not placed.`);
              return;
          }
      }


      await db.collection('orders').add({
        userId: currentUser.uid,
        items: orderItems,
        total: orderTotal,
        status: 'Pending', // Initial order status
        createdAt: new Date().toISOString(), // mockFirebase.firestore.FieldValue.serverTimestamp(), // Use server timestamp in real Firebase
      });

      // Deduct stock (highly simplified, needs to be transactional in real app)
      for (const item of orderItems) {
        const product = products.find(p => p.id === item.productId);
        if (product) {
            // This is a mock update. In a real app, use Firestore transactions.
            const newStock = product.stock - item.quantity;
            await db.collection('products').doc(item.productId).set({ stock: newStock }, { merge: true });
            // Note: This mock won't auto-update the products list in UI without a re-fetch or manual state update
        }
      }

      setCart({});
      setFeedback('Order placed successfully!');
      // Potentially trigger a re-fetch of products to show updated stock
    } catch (error) {
      console.error("Error placing order:", error);
      setFeedback(`Error placing order: ${error.message}`);
    }
  };

  if (products.loading) return <LoadingSpinner />;
  if (products.error) return <ErrorMessage message={products.error.message} />;

  return (
    <div className="user-dashboard">
      <h3>Our Products</h3>
      <div className="product-grid">
        {products.data.map(product => (
          <div key={product.id} className="product-card">
            <h4>{product.name}</h4>
            <p>{formatCurrency(product.price)}</p>
            <p>Stock: {product.stock > 0 ? product.stock : "Out of stock"}</p>
            {product.stock > 0 && (
                 <button onClick={() => handleAddToCart(product.id, product.stock)} disabled={ (cart[product.id] || 0) >= product.stock}>
                    Add to Cart {cart[product.id] ? `(${cart[product.id]})` : ''}
                </button>
            )}
             {(cart[product.id] || 0) >= product.stock && product.stock > 0 && <p className="warning-text">Max stock in cart</p>}
          </div>
        ))}
      </div>

      <h3>Your Cart</h3>
      {Object.keys(cart).length === 0 ? (
        <p>Your cart is empty.</p>
      ) : (
        <>
          <ul className="cart-items">
            {Object.entries(cart).map(([productId, quantity]) => {
              const product = products.data.find(p => p.id === productId);
              return (
                <li key={productId}>
                  {product?.name || 'Unknown Product'} - Quantity: {quantity}
                  <button onClick={() => handleRemoveFromCart(productId)}><DeleteIcon/></button>
                </li>
              );
            })}
          </ul>
          <p>Total: {formatCurrency(calculateTotal)}</p>
          <button onClick={handlePlaceOrder} disabled={Object.keys(cart).length === 0 || feedback === 'Placing order...'}>
            Place Order
          </button>
          {feedback && <p>{feedback}</p>}
        </>
      )}
    </div>
  );
};


// Admin Dashboard Component
const AdminDashboard = ({ db, productsData, setProductsData, ordersData }) => {
  // For simplicity, passing productsData and setProductsData down
  // ordersData is fetched here or passed if fetched higher up
  if (ordersData.loading) return <LoadingSpinner message="Loading orders..." />;
  if (ordersData.error) return <ErrorMessage message={`Error loading orders: ${ordersData.error.message}`} />;

  const updateOrderStatus = async (orderId, newStatus) => {
    try {
        await db.collection('orders').doc(orderId).set({ status: newStatus }, { merge: true });
        // Optimistically update UI or rely on listener if data is live
        ordersData.setData(prev => prev.map(o => o.id === orderId ? {...o, status: newStatus} : o));
    } catch (error) {
        console.error("Error updating order status:", error);
        // Handle error display to admin
    }
  };


  return (
    <div className="admin-dashboard">
      <h2>Admin Dashboard</h2>
      <ProductManagement db={db} productsData={productsData} setProductsData={setProductsData} />

      <div className="admin-section order-management">
        <h3>Order Management</h3>
        {ordersData.data.length === 0 ? <p>No orders yet.</p> : (
          <ul className="order-list">
            {ordersData.data.map(order => (
              <li key={order.id}>
                <p>Order ID: {order.id}</p>
                <p>User ID: {order.userId}</p>
                <p>Total: {formatCurrency(order.total)}</p>
                <p>Status: {order.status}</p>
                {/* Add more order details if needed */}
                <div>
                    <select value={order.status} onChange={(e) => updateOrderStatus(order.id, e.target.value)}>
                        <option value="Pending">Pending</option>
                        <option value="Processing">Processing</option>
                        <option value="Shipped">Shipped</option>
                        <option value="Delivered">Delivered</option>
                        <option value="Cancelled">Cancelled</option>
                    </select>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};


// Main App Component
function App() {
  // `authLoading` (which was `loading` from useFirebase) is no longer returned by useFirebase.
  // `isAuthReady` is the primary signal for auth status.
  const { db, auth, currentUser, isAuthReady, error: authError, appId } = useFirebase();

  // Fetch products - could be context or prop-drilled for small apps
  const { data: products, loading: productsLoading, error: productsError, setData: setProducts } = useFirestoreData(db, 'products');
  const ordersFilter = useMemo(() => {
    if (!currentUser || currentUser.role === null) return () => false; // No user or role not determined, no orders
    if (currentUser.role === USER_ROLES.ADMIN) return () => true;
    return (order) => order.userId === currentUser.uid;
  }, [currentUser]);
  const { data: orders, loading: ordersLoading, error: ordersError, setData: setOrders } = useFirestoreData(db, 'orders', ordersFilter);

  const handleLogout = async () => {
    if (auth) {
      try {
        await auth.signOut();
      } catch (error) {
        console.error("Logout Error:", error);
      }
    }
  };

  // Loading condition is exactly: !isAuthReady || (currentUser && currentUser.role === null)
  if (!isAuthReady || (currentUser && currentUser.role === null)) {
    // The existing LoadingSpinner is used. If "Loading User Data..." text is required,
    // the LoadingSpinner component itself would need to be modified or replaced here.
    // For this task, we stick to the exact condition and rely on the existing spinner.
    return <LoadingSpinner />;
  }

  // Error handling and other logic remain unchanged as per instructions
  if (authError) {
    return <ErrorMessage message={`Authentication Error: ${authError.message}`} />;
  }
  if (productsError) {
    return <ErrorMessage message={`Error loading products: ${productsError.message}`} />;
  }
  if (ordersError && currentUser && currentUser.role !== null) { // Ensure currentUser and role are checked for order errors
    return <ErrorMessage message={`Error loading orders: ${ordersError.message}`} />;
  }

  if (!currentUser) { // This check is after the loading condition.
    return <LoginPage auth={auth} />;
  }

  // Pass necessary data to components.
  // For a larger app, consider React Context for state management.
  const productsData = { data: products, loading: productsLoading, error: productsError };
  const ordersData = { data: orders, loading: ordersLoading, error: ordersError, setData: setOrders };


  return (
    <div className="App">
      <Navbar currentUser={currentUser} onLogout={handleLogout} />
      <main>
        {currentUser.role === USER_ROLES.ADMIN ? (
          <AdminDashboard db={db} productsData={productsData} setProductsData={setProducts} ordersData={ordersData} />
        ) : (
          <UserDashboard db={db} currentUser={currentUser} products={productsData} />
        )}
        {/* Example of showing orders for a regular user */}
        {currentUser.role === USER_ROLES.USER && <OrdersPage db={db} appId={appId} products={products} currentUser={currentUser} />}
      </main>
    </div>
  );
}

export default App;


// Simple Orders Page for Users (can be expanded)
const OrdersPage = ({ db, appId, products, currentUser }) => {
    // This hook will re-fetch orders specifically for this component,
    // filtered by the current user's ID.
    // This demonstrates fetching data within a component rather than passing all data down.
    const userOrderFilter = useMemo(() => (order) => order.userId === currentUser.uid, [currentUser.uid]);
    const { data: userOrders, loading, error } = useFirestoreData(db, 'orders', userOrderFilter);

    if (loading) return <LoadingSpinner />;
    if (error) return <ErrorMessage message={`Error loading your orders: ${error.message}`} />;

    return (
        <div className="user-orders-page">
            <h3>Your Orders</h3>
            {userOrders.length === 0 ? (
                <p>You have no orders yet.</p>
            ) : (
                <ul className="order-list">
                    {userOrders.map(order => (
                        <li key={order.id}>
                            <p>Order ID: {order.id}</p>
                            <p>Date: {new Date(order.createdAt).toLocaleDateString()}</p>
                            <p>Total: {formatCurrency(order.total)}</p>
                            <p>Status: {order.status}</p>
                            <h4>Items:</h4>
                            <ul>
                                {order.items.map((item, index) => {
                                    const productDetails = products.find(p => p.id === item.productId);
                                    return (
                                        <li key={index}>
                                            {productDetails ? productDetails.name : 'Unknown Product'} -
                                            Quantity: {item.quantity} -
                                            Price: {formatCurrency(item.priceAtPurchase)}
                                        </li>
                                    );
                                })}
                            </ul>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};
