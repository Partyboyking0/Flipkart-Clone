import React, { Component, useEffect, useMemo, useState } from "react";
import { api } from "./api";

const BUYER_ID = 1;
const SELLER_ID = 2;
const emptyCart = { items: [], summary: { mrp_total: 0, subtotal: 0, discount: 0, delivery_fee: 0, total: 0 } };

const money = (value) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value || 0);

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <main className="fatal-error">
          <h1>Frontend error</h1>
          <p>{this.state.error.message}</p>
        </main>
      );
    }
    return this.props.children;
  }
}

function Header({ query, setQuery, cartCount, page, go, activeRole, setActiveRole, currentUser }) {
  return (
    <header className="topbar">
      <button className="brand" onClick={() => go("home")} aria-label="Go home">
        <span>Flipkart</span>
        <small>Explore Plus</small>
      </button>
      <label className="search">
        <span>Search</span>
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search for products, brands and more" disabled={page === "seller"} />
      </label>
      <nav className="nav-actions">
        <button onClick={() => setActiveRole(activeRole === "buyer" ? "seller" : "buyer")}>Switch to {activeRole === "buyer" ? "Seller" : "Buyer"}</button>
        <button onClick={() => go(activeRole === "buyer" ? "buyer" : "seller")}>{currentUser?.name || "User"}</button>
        <button onClick={() => go(activeRole === "buyer" ? "orders" : "seller")}>{activeRole === "buyer" ? "Orders" : "Seller Orders"}</button>
        <button onClick={() => go("cart")}>Cart ({cartCount})</button>
      </nav>
    </header>
  );
}

function UserPanel({ user }) {
  if (!user) return null;
  return (
    <section className="user-panel">
      <div>
        <h2>{user.role === "seller" ? user.store_name : user.name}</h2>
        <p>{user.email}</p>
      </div>
      <div>
        <span>{user.phone}</span>
        <strong>{user.city}, {user.state} - {user.pincode}</strong>
      </div>
    </section>
  );
}

function ProductCard({ product, openProduct }) {
  const discount = Math.round(((product.mrp - product.price) / product.mrp) * 100);
  return (
    <article className="product-card" onClick={() => openProduct(product.id)}>
      <div className="product-image">
        <img src={product.images[0]?.url} alt={product.images[0]?.alt || product.title} />
      </div>
      <h3>{product.title}</h3>
      <div className="rating-row">
        <span className="rating">{product.rating} *</span>
        <span>({product.reviews.toLocaleString("en-IN")})</span>
      </div>
      <div className="price-row">
        <strong>{money(product.price)}</strong>
        <span>{money(product.mrp)}</span>
        <em>{discount}% off</em>
      </div>
      <p>{product.assured ? "Assured delivery" : "Standard delivery"}</p>
    </article>
  );
}

function HomePage({ products, categories, selectedCategory, setSelectedCategory, openProduct, loading, buyer }) {
  return (
    <main className="page-shell">
      <aside className="filters">
        <h2>Filters</h2>
        <button className={selectedCategory === "all" ? "active" : ""} onClick={() => setSelectedCategory("all")}>All Categories</button>
        {categories.map((category) => (
          <button key={category.id} className={selectedCategory === category.slug ? "active" : ""} onClick={() => setSelectedCategory(category.slug)}>
            {category.name}
          </button>
        ))}
      </aside>
      <section className="listing">
        <UserPanel user={buyer} />
        <div className="listing-title">
          <h1>Top Deals For You</h1>
          <span>{products.length} products</span>
        </div>
        {loading ? (
          <div className="empty-state">Loading products...</div>
        ) : products.length ? (
          <div className="grid">{products.map((product) => <ProductCard key={product.id} product={product} openProduct={openProduct} />)}</div>
        ) : (
          <div className="empty-state">No products matched your search.</div>
        )}
      </section>
    </main>
  );
}

function ProductDetail({ product, onBack, addToCart, buyNow }) {
  const [imageIndex, setImageIndex] = useState(0);
  if (!product) return null;
  const image = product.images[imageIndex] || product.images[0];
  const discount = Math.round(((product.mrp - product.price) / product.mrp) * 100);

  return (
    <main className="detail-page">
      <button className="back-link" onClick={onBack}>Back to products</button>
      <section className="detail-layout">
        <div className="gallery">
          <div className="thumbs">
            {product.images.map((item, index) => (
              <button key={item.id} className={index === imageIndex ? "selected" : ""} onClick={() => setImageIndex(index)}>
                <img src={item.url} alt={item.alt} />
              </button>
            ))}
          </div>
          <div className="hero-image"><img src={image?.url} alt={image?.alt || product.title} /></div>
        </div>
        <div className="detail-info">
          <p className="brand-name">{product.brand}</p>
          <h1>{product.title}</h1>
          <div className="rating-row">
            <span className="rating">{product.rating} *</span>
            <span>{product.reviews.toLocaleString("en-IN")} Ratings & Reviews</span>
          </div>
          <div className="detail-price">
            <strong>{money(product.price)}</strong>
            <span>{money(product.mrp)}</span>
            <em>{discount}% off</em>
          </div>
          <p className={product.stock > 0 ? "stock in" : "stock out"}>{product.stock > 0 ? `${product.stock} in stock` : "Out of stock"}</p>
          <p className="description">{product.description}</p>
          <div className="detail-actions">
            <button onClick={() => addToCart(product.id)} disabled={product.stock === 0}>Add to Cart</button>
            <button className="buy" onClick={() => buyNow(product.id)} disabled={product.stock === 0}>Buy Now</button>
          </div>
          <section className="specs">
            <h2>Specifications</h2>
            {product.specs.map((spec) => <div key={spec.id}><span>{spec.name}</span><strong>{spec.value}</strong></div>)}
          </section>
        </div>
      </section>
    </main>
  );
}

function PriceBox({ summary, action, label }) {
  const mrpTotal = summary.mrp_total ?? summary.subtotal + summary.discount;
  return (
    <aside className="price-box">
      <h2>Price Details</h2>
      <div><span>Total MRP</span><strong>{money(mrpTotal)}</strong></div>
      <div><span>Discount</span><strong className="green">-{money(summary.discount)}</strong></div>
      <div><span>Selling Price</span><strong>{money(summary.subtotal)}</strong></div>
      <div><span>Delivery Charges</span><strong>{summary.delivery_fee ? money(summary.delivery_fee) : "Free"}</strong></div>
      <div className="total"><span>Total Amount</span><strong>{money(summary.total)}</strong></div>
      {summary.discount > 0 && <p>You will save {money(summary.discount)} on this order</p>}
      {action && <button onClick={action}>{label}</button>}
    </aside>
  );
}

function CartPage({ cart, updateCart, removeCart, go }) {
  return (
    <main className="cart-page">
      <section className="cart-items">
        <h1>My Cart ({cart.items.length})</h1>
        {cart.items.length ? cart.items.map((item) => (
          <article className="cart-line" key={item.id}>
            <img src={item.product.images[0]?.url} alt={item.product.title} />
            <div>
              <h2>{item.product.title}</h2>
              <p>{item.product.brand}</p>
              <strong>{money(item.product.price)}</strong>
              <div className="quantity">
                <button onClick={() => updateCart(item.id, Math.max(1, item.quantity - 1))}>-</button>
                <span>{item.quantity}</span>
                <button onClick={() => updateCart(item.id, Math.min(10, item.product.stock, item.quantity + 1))}>+</button>
                <button className="remove" onClick={() => removeCart(item.id)}>Remove</button>
              </div>
            </div>
          </article>
        )) : <div className="empty-state">Your cart is empty. Add something worth unboxing.</div>}
      </section>
      <PriceBox summary={cart.summary} action={cart.items.length ? () => go("checkout") : null} label="Continue to Checkout" />
    </main>
  );
}

function CheckoutPage({ cart, buyer, setCheckoutAddress, go }) {
  const [form, setForm] = useState({
    customer_name: buyer?.name || "",
    phone: buyer?.phone || "",
    address_line: buyer?.address_line || "",
    city: buyer?.city || "",
    state: buyer?.state || "",
    pincode: buyer?.pincode || "",
  });
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  return (
    <main className="checkout-page">
      <section className="checkout-form">
        <h1>Delivery Address</h1>
        <form onSubmit={(event) => { event.preventDefault(); setCheckoutAddress(form); go("payment"); }}>
          <input required placeholder="Full name" value={form.customer_name} onChange={(event) => update("customer_name", event.target.value)} />
          <input required placeholder="Mobile number" value={form.phone} onChange={(event) => update("phone", event.target.value)} />
          <textarea required placeholder="Address" value={form.address_line} onChange={(event) => update("address_line", event.target.value)} />
          <input required placeholder="City" value={form.city} onChange={(event) => update("city", event.target.value)} />
          <input required placeholder="State" value={form.state} onChange={(event) => update("state", event.target.value)} />
          <input required placeholder="Pincode" value={form.pincode} onChange={(event) => update("pincode", event.target.value)} />
          <button type="submit">Continue to Payment</button>
          <button type="button" className="secondary" onClick={() => go("cart")}>Back to Cart</button>
        </form>
      </section>
      <OrderReview cart={cart} />
    </main>
  );
}

function PaymentPage({ cart, checkoutAddress, placeOrder, go }) {
  const [payment, setPayment] = useState({ method: "UPI", payer_name: checkoutAddress?.customer_name || "", upi_id: "", card_last4: "" });
  const update = (key, value) => setPayment((current) => ({ ...current, [key]: value }));
  const actionLabel = payment.method === "COD" ? "Place Order" : `Pay ${money(cart.summary.total)} and Place Order`;

  return (
    <main className="checkout-page">
      <section className="checkout-form">
        <h1>Payment</h1>
        <form onSubmit={(event) => {
          event.preventDefault();
          const payload = { method: payment.method, payer_name: payment.payer_name };
          if (payment.method === "UPI") payload.upi_id = payment.upi_id;
          if (payment.method === "CARD") payload.card_last4 = payment.card_last4;
          placeOrder(payload);
        }}>
          <select value={payment.method} onChange={(event) => update("method", event.target.value)}>
            <option value="UPI">UPI</option>
            <option value="CARD">Debit/Credit Card</option>
            <option value="COD">Cash on Delivery</option>
          </select>
          <input required placeholder="Payer name" value={payment.payer_name} onChange={(event) => update("payer_name", event.target.value)} />
          {payment.method === "UPI" && <input required placeholder="UPI ID" value={payment.upi_id} onChange={(event) => update("upi_id", event.target.value)} />}
          {payment.method === "CARD" && <input required maxLength="4" placeholder="Last 4 card digits" value={payment.card_last4} onChange={(event) => update("card_last4", event.target.value.replace(/\D/g, ""))} />}
          <button type="submit">{actionLabel}</button>
          <button type="button" className="secondary" onClick={() => go("checkout")}>Back to Address</button>
        </form>
      </section>
      <OrderReview cart={cart} />
    </main>
  );
}

function OrderReview({ cart }) {
  return (
    <section className="order-review">
      <h2>Order Summary</h2>
      {cart.items.map((item) => <div className="review-line" key={item.id}><span>{item.product.title}</span><strong>{item.quantity} x {money(item.product.price)}</strong></div>)}
      <PriceBox summary={cart.summary} />
    </section>
  );
}

function OrdersPage({ orders, buyer, go }) {
  return (
    <main className="dashboard-page">
      <UserPanel user={buyer} />
      <section className="dashboard-card">
        <h1>Past Orders</h1>
        {orders.length ? orders.map((order) => (
          <article className="order-card" key={order.id}>
            <div>
              <h2>{order.order_number}</h2>
              <p>{order.status} | {order.payment_method} | {order.payment_status}</p>
            </div>
            <strong>{money(order.total_amount)}</strong>
            <div className="order-items">{order.items.map((item) => <span key={item.id}>{item.quantity} x {item.title}</span>)}</div>
          </article>
        )) : <div className="empty-state">No orders yet.</div>}
        <button className="wide-action" onClick={() => go("home")}>Continue Shopping</button>
      </section>
    </main>
  );
}

function SellerPage({ dashboard }) {
  if (!dashboard) return <main className="dashboard-page"><div className="empty-state">Loading seller dashboard...</div></main>;
  return (
    <main className="dashboard-page">
      <UserPanel user={dashboard.seller} />
      <section className="seller-stats">
        <div><span>Products</span><strong>{dashboard.stats.product_count}</strong></div>
        <div><span>Units Sold</span><strong>{dashboard.stats.units_sold}</strong></div>
        <div><span>Revenue</span><strong>{money(dashboard.stats.revenue)}</strong></div>
        <div><span>Orders</span><strong>{dashboard.stats.order_count}</strong></div>
      </section>
      <section className="dashboard-card">
        <h1>Seller Inventory</h1>
        <div className="seller-table">
          {dashboard.products.map((product) => <div key={product.id}><span>{product.title}</span><strong>{product.stock} left</strong><em>{money(product.price)}</em></div>)}
        </div>
      </section>
      <section className="dashboard-card">
        <h1>Orders Containing Your Products</h1>
        {dashboard.orders.length ? dashboard.orders.map((order) => (
          <article className="order-card" key={order.id}>
            <div><h2>{order.order_number}</h2><p>{order.customer_name}, {order.city} | {order.payment_status}</p></div>
            <strong>{money(order.total_amount)}</strong>
          </article>
        )) : <div className="empty-state">No seller orders yet.</div>}
      </section>
    </main>
  );
}

function ConfirmationPage({ order, go }) {
  return (
    <main className="confirmation">
      <div>
        <span className="success-mark">OK</span>
        <h1>Order placed successfully</h1>
        <p>Your order ID is <strong>{order?.order_number}</strong>.</p>
        <p>Payment: <strong>{order?.payment_method}</strong> | {order?.payment_status}</p>
        <button onClick={() => go("orders")}>View Order Summary</button>
      </div>
    </main>
  );
}

export default function App() {
  const [page, setPage] = useState("home");
  const [activeRole, setActiveRole] = useState("buyer");
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [cart, setCart] = useState(emptyCart);
  const [users, setUsers] = useState([]);
  const [orders, setOrders] = useState([]);
  const [sellerDashboard, setSellerDashboard] = useState(null);
  const [checkoutAddress, setCheckoutAddress] = useState(null);
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");

  const buyer = users.find((user) => user.id === BUYER_ID);
  const seller = users.find((user) => user.id === SELLER_ID);
  const currentUser = activeRole === "buyer" ? buyer : seller;
  const cartCount = useMemo(() => cart.items.reduce((total, item) => total + item.quantity, 0), [cart.items]);

  const refreshOrders = () => api.orders().then(setOrders).catch((error) => setNotice(error.message));
  const refreshSeller = () => api.sellerDashboard(SELLER_ID).then(setSellerDashboard).catch((error) => setNotice(error.message));

  useEffect(() => {
    api.users().then(setUsers).catch((error) => setNotice(error.message));
    api.categories().then(setCategories).catch((error) => setNotice(error.message));
    api.cart().then(setCart).catch(() => setCart(emptyCart));
    refreshOrders();
    refreshSeller();
  }, []);

  useEffect(() => {
    setLoading(true);
    const timeout = setTimeout(() => {
      api.products({ search: query, category: selectedCategory })
        .then(setProducts)
        .catch((error) => setNotice(error.message))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(timeout);
  }, [query, selectedCategory]);

  useEffect(() => {
    if (activeRole === "seller") setPage("seller");
    if (activeRole === "buyer" && page === "seller") setPage("home");
  }, [activeRole]);

  const go = (nextPage) => {
    if (nextPage === "orders") refreshOrders();
    if (nextPage === "seller") refreshSeller();
    if (nextPage === "payment" && !checkoutAddress) {
      setNotice("Please add delivery address first");
      setPage("checkout");
      return;
    }
    setPage(nextPage);
  };

  const openProduct = async (id) => {
    try {
      setSelectedProduct(await api.product(id));
      setPage("detail");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const addToCart = async (productId) => {
    try {
      setCart(await api.addToCart(productId));
      setNotice("Added to cart");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const buyNow = async (productId) => {
    try {
      setCart(await api.addToCart(productId));
      setPage("checkout");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const placeOrder = async (payment) => {
    try {
      if (!checkoutAddress) {
        setNotice("Please add delivery address first");
        setPage("checkout");
        return;
      }
      const placed = await api.placeOrder({ address: checkoutAddress, payment });
      setOrder(placed);
      setCart(emptyCart);
      setCheckoutAddress(null);
      refreshOrders();
      refreshSeller();
      setPage("confirmation");
    } catch (error) {
      setNotice(error.message);
    }
  };

  return (
    <ErrorBoundary>
      <Header query={query} setQuery={setQuery} cartCount={cartCount} page={page} go={go} activeRole={activeRole} setActiveRole={setActiveRole} currentUser={currentUser} />
      {notice && <button className="toast" onClick={() => setNotice("")}>{notice}</button>}
      {page === "home" && <HomePage products={products} categories={categories} selectedCategory={selectedCategory} setSelectedCategory={setSelectedCategory} openProduct={openProduct} loading={loading} buyer={buyer} />}
      {page === "buyer" && <OrdersPage orders={orders} buyer={buyer} go={go} />}
      {page === "orders" && <OrdersPage orders={orders} buyer={buyer} go={go} />}
      {page === "seller" && <SellerPage dashboard={sellerDashboard} />}
      {page === "detail" && <ProductDetail product={selectedProduct} onBack={() => setPage("home")} addToCart={addToCart} buyNow={buyNow} />}
      {page === "cart" && <CartPage cart={cart} updateCart={(itemId, quantity) => api.updateCart(itemId, quantity).then(setCart)} removeCart={(itemId) => api.removeCart(itemId).then(setCart)} go={go} />}
      {page === "checkout" && <CheckoutPage cart={cart} buyer={buyer} setCheckoutAddress={setCheckoutAddress} go={go} />}
      {page === "payment" && <PaymentPage cart={cart} checkoutAddress={checkoutAddress} placeOrder={placeOrder} go={go} />}
      {page === "confirmation" && <ConfirmationPage order={order} go={go} />}
    </ErrorBoundary>
  );
}
