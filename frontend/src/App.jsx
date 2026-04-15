import React, { Component, useEffect, useMemo, useState } from "react";
import { api } from "./api";

const BUYER_ID = 1;
const SELLER_ID = 2;
const emptyCart = { items: [], summary: { mrp_total: 0, subtotal: 0, discount: 0, delivery_fee: 0, total: 0 } };

const money = (value) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value || 0);

const rzpInput = {
  width: "100%", padding: "10px 12px", border: "1px solid #ddd",
  borderRadius: 6, fontSize: 14, outline: "none", boxSizing: "border-box",
};
const rzpPayBtn = {
  width: "100%", padding: "12px", background: "#072654", color: "#fff",
  border: "none", borderRadius: 6, fontWeight: 700, fontSize: 15,
  cursor: "pointer", marginTop: 4,
};

class ErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  render() {
    if (this.state.error) return <main className="fatal-error"><h1>Frontend error</h1><p>{this.state.error.message}</p></main>;
    return this.props.children;
  }
}

function Header({ query, setQuery, cartCount, page, go, activeRole, setActiveRole, currentUser }) {
  const isAdmin = currentUser?.role === "admin";
  return (
    <header className="topbar">
      <button className="brand" onClick={() => go("home")} aria-label="Go home">
        <span>Flipkart</span><small>Explore Plus</small>
      </button>
      <label className="search">
        <span>Search</span>
        <input value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for products, brands and more"
          disabled={page === "seller" || page === "admin"} />
      </label>
      <nav className="nav-actions">
        {!isAdmin && (
          <button onClick={() => setActiveRole(activeRole === "buyer" ? "seller" : "buyer")}>
            Switch to {activeRole === "buyer" ? "Seller" : "Buyer"}
          </button>
        )}
        <button onClick={() => go(currentUser ? (isAdmin ? "admin" : activeRole === "buyer" ? "buyer" : "seller") : "auth")}>
          {currentUser?.name || "Login"}
        </button>
        {isAdmin
          ? <button onClick={() => go("admin")}>Admin Panel</button>
          : <button onClick={() => go(activeRole === "buyer" ? "orders" : "seller")}>{activeRole === "buyer" ? "Orders" : "Seller Orders"}</button>
        }
        <button onClick={() => go("cart")}>Cart ({cartCount})</button>
      </nav>
    </header>
  );
}

function UserPanel({ user }) {
  if (!user) return null;
  return (
    <section className="user-panel">
      <div><h2>{user.role === "seller" ? user.store_name : user.name}</h2><p>{user.email}</p></div>
      <div><span>{user.phone}</span><strong>{user.city}, {user.state} - {user.pincode}</strong></div>
    </section>
  );
}

function ProductCard({ product, openProduct, wished, toggleWishlist }) {
  const discount = Math.round(((product.mrp - product.price) / product.mrp) * 100);
  return (
    <article className="product-card" onClick={() => openProduct(product.id)}>
      <button className={wished ? "wish-button wished" : "wish-button"}
        onClick={(e) => { e.stopPropagation(); toggleWishlist(product.id); }}>
        {wished ? "Wishlisted" : "Wishlist"}
      </button>
      <div className="product-image">
        <img src={product.images[0]?.url} alt={product.images[0]?.alt || product.title} />
      </div>
      <h3>{product.title}</h3>
      <div className="rating-row">
        <span className="rating">{product.rating} ★</span>
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

function HomePage({ products, categories, filters, setFilters, openProduct, loading, buyer, wishlistIds, toggleWishlist }) {
  const updateFilter = (key, value) => setFilters((c) => ({ ...c, [key]: value }));
  return (
    <main className="page-shell">
      <aside className="filters">
        <h2>Filters</h2>
        <button className={filters.category === "all" ? "active" : ""} onClick={() => updateFilter("category", "all")}>All Categories</button>
        {categories.map((cat) => (
          <button key={cat.id} className={filters.category === cat.slug ? "active" : ""} onClick={() => updateFilter("category", cat.slug)}>{cat.name}</button>
        ))}
        <label>Max Price<input type="number" value={filters.max_price} onChange={(e) => updateFilter("max_price", e.target.value)} placeholder="50000" /></label>
        <label>Min Rating
          <select value={filters.min_rating} onChange={(e) => updateFilter("min_rating", e.target.value)}>
            <option value="">Any</option><option value="4">4+</option><option value="4.5">4.5+</option>
          </select>
        </label>
      </aside>
      <section className="listing">
        <UserPanel user={buyer} />
        <div className="listing-title"><h1>Top Deals For You</h1><span>{products.length} products</span></div>
        {loading ? <div className="empty-state">Loading products...</div>
          : products.length
            ? <div className="grid">{products.map((p) => <ProductCard key={p.id} product={p} openProduct={openProduct} wished={wishlistIds.includes(p.id)} toggleWishlist={toggleWishlist} />)}</div>
            : <div className="empty-state">No products matched your search.</div>}
      </section>
    </main>
  );
}

function ProductDetail({ product, onBack, addToCart, buyNow, reviews, addReview }) {
  const [imageIndex, setImageIndex] = useState(0);
  const [reviewForm, setReviewForm] = useState({ rating: 5, comment: "" });
  if (!product) return null;
  const image = product.images[imageIndex] || product.images[0];
  const discount = Math.round(((product.mrp - product.price) / product.mrp) * 100);
  return (
    <main className="detail-page">
      <button className="back-link" onClick={onBack}>← Back to products</button>
      <section className="detail-layout">
        <div className="gallery">
          <div className="thumbs">
            {product.images.map((img, i) => (
              <button key={img.id} className={i === imageIndex ? "selected" : ""} onClick={() => setImageIndex(i)}>
                <img src={img.url} alt={img.alt} />
              </button>
            ))}
          </div>
          <div className="hero-image"><img src={image?.url} alt={image?.alt || product.title} /></div>
        </div>
        <div className="detail-info">
          <p className="brand-name">{product.brand}</p>
          <h1>{product.title}</h1>
          <div className="rating-row">
            <span className="rating">{product.rating} ★</span>
            <span>{product.reviews.toLocaleString("en-IN")} Ratings & Reviews</span>
          </div>
          <div className="detail-price">
            <strong>{money(product.price)}</strong><span>{money(product.mrp)}</span><em>{discount}% off</em>
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
          <section className="reviews">
            <h2>Reviews & Ratings</h2>
            <form onSubmit={(e) => { e.preventDefault(); addReview({ product_id: product.id, rating: Number(reviewForm.rating), comment: reviewForm.comment }); setReviewForm({ rating: 5, comment: "" }); }}>
              <select value={reviewForm.rating} onChange={(e) => setReviewForm((c) => ({ ...c, rating: e.target.value }))}>
                {[5,4,3,2,1].map((r) => <option key={r} value={r}>{r} star</option>)}
              </select>
              <input required value={reviewForm.comment} onChange={(e) => setReviewForm((c) => ({ ...c, comment: e.target.value }))} placeholder="Write a review" />
              <button type="submit">Submit</button>
            </form>
            {reviews.map((rev) => (
              <article className="review-card" key={rev.id}>
                <strong>{rev.rating} ★ by {rev.user.name}</strong>
                {rev.verified_purchase && <span>Verified Purchase</span>}
                <p>{rev.comment}</p>
              </article>
            ))}
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
              <h2>{item.product.title}</h2><p>{item.product.brand}</p>
              <strong>{money(item.product.price)}</strong>
              <div className="quantity">
                <button onClick={() => updateCart(item.id, Math.max(1, item.quantity - 1))}>-</button>
                <span>{item.quantity}</span>
                <button onClick={() => updateCart(item.id, Math.min(10, item.product.stock, item.quantity + 1))}>+</button>
                <button className="remove" onClick={() => removeCart(item.id)}>Remove</button>
              </div>
            </div>
          </article>
        )) : <div className="empty-state">Your cart is empty.</div>}
      </section>
      <PriceBox summary={cart.summary} action={cart.items.length ? () => go("checkout") : null} label="Continue to Checkout" />
    </main>
  );
}

function CheckoutPage({ cart, buyer, setCheckoutAddress, go }) {
  const [form, setForm] = useState({
    customer_name: buyer?.name || "", phone: buyer?.phone || "",
    address_line: buyer?.address_line || "", city: buyer?.city || "",
    state: buyer?.state || "", pincode: buyer?.pincode || "",
  });
  const update = (key, value) => setForm((c) => ({ ...c, [key]: value }));
  return (
    <main className="checkout-page">
      <section className="checkout-form">
        <h1>Delivery Address</h1>
        <form onSubmit={(e) => { e.preventDefault(); setCheckoutAddress(form); go("payment"); }}>
          <input required placeholder="Full name" value={form.customer_name} onChange={(e) => update("customer_name", e.target.value)} />
          <input required placeholder="Mobile number" value={form.phone} onChange={(e) => update("phone", e.target.value)} />
          <textarea required placeholder="Address" value={form.address_line} onChange={(e) => update("address_line", e.target.value)} />
          <input required placeholder="City" value={form.city} onChange={(e) => update("city", e.target.value)} />
          <input required placeholder="State" value={form.state} onChange={(e) => update("state", e.target.value)} />
          <input required placeholder="Pincode" value={form.pincode} onChange={(e) => update("pincode", e.target.value)} />
          <button type="submit">Continue to Payment</button>
          <button type="button" className="secondary" onClick={() => go("cart")}>Back to Cart</button>
        </form>
      </section>
      <OrderReview cart={cart} />
    </main>
  );
}

function AuthPage({ login, signup, googleLogin }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "aarav.buyer@example.com", phone: "9876543210", password: "password123" });
  const update = (key, value) => setForm((c) => ({ ...c, [key]: value }));
  return (
    <main className="dashboard-page">
      <section className="checkout-form auth-box">
        <h1>{mode === "login" ? "Login" : "Signup"}</h1>
        <p style={{ fontSize: 13, color: "#878787", marginBottom: 12 }}>
          Demo buyer: <strong>aarav.buyer@example.com</strong> / <strong>password123</strong><br />
          Admin: <strong>admin@flipkart.com</strong> / <strong>admin123</strong>
        </p>
        <form onSubmit={(e) => { e.preventDefault(); mode === "login" ? login(form) : signup(form); }}>
          {mode === "signup" && <input required placeholder="Full name" value={form.name} onChange={(e) => update("name", e.target.value)} />}
          {mode === "signup" && <input required placeholder="Phone" value={form.phone} onChange={(e) => update("phone", e.target.value)} />}
          <input required placeholder="Email" value={form.email} onChange={(e) => update("email", e.target.value)} />
          <input required type="password" placeholder="Password" value={form.password} onChange={(e) => update("password", e.target.value)} />
          <button type="submit">{mode === "login" ? "Login" : "Create Account"}</button>
          <button type="button" className="secondary" onClick={() => googleLogin({ email: "google.user@example.com", name: "Google Demo User", provider: "google" })}>Continue with Google</button>
          <button type="button" className="link-button" onClick={() => setMode(mode === "login" ? "signup" : "login")}>
            {mode === "login" ? "Create new account" : "Already have an account"}
          </button>
        </form>
      </section>
    </main>
  );
}

// ── Simulated Razorpay Payment Page ──────────────────────────────────────────
function PaymentPage({ cart, checkoutAddress, placeOrder, go, setNotice }) {
  const [method, setMethod]               = useState("RAZORPAY");
  const [payerName, setPayerName]         = useState(checkoutAddress?.customer_name || "");
  const [upiId, setUpiId]                 = useState("");
  const [cardNumber, setCardNumber]       = useState("");
  const [cardExpiry, setCardExpiry]       = useState("");
  const [cardCvv, setCardCvv]             = useState("");
  const [cardName, setCardName]           = useState("");
  const [loading, setLoading]             = useState(false);
  const [rzpOpen, setRzpOpen]             = useState(false);
  const [rzpTab, setRzpTab]               = useState("card");
  const [rzpUpi, setRzpUpi]               = useState("");
  const [rzpProcessing, setRzpProcessing] = useState(false);

  const total = cart.summary.total;

  const handleRzpPay = async (e) => {
    e.preventDefault();
    setRzpProcessing(true);
    await new Promise((res) => setTimeout(res, 1800));
    const fakePayId = `pay_${Math.random().toString(36).slice(2,18).toUpperCase()}`;
    const fakeOrdId = `order_${Math.random().toString(36).slice(2,18).toUpperCase()}`;
    setRzpProcessing(false);
    setRzpOpen(false);
    await placeOrder({
      method: "RAZORPAY",
      payer_name: payerName || checkoutAddress?.customer_name,
      payment_reference: fakePayId,
      razorpay_order_id: fakeOrdId,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (method === "RAZORPAY") { setRzpOpen(true); return; }
    setLoading(true);
    try {
      const payload = { method, payer_name: payerName };
      if (method === "UPI")  payload.upi_id    = upiId;
      if (method === "CARD") payload.card_last4 = cardNumber.slice(-4);
      await placeOrder(payload);
    } catch (err) {
      setNotice(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* ── Razorpay-look-alike modal ─────────────────────────────────────── */}
      {rzpOpen && (
        <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.6)", display:"flex", alignItems:"center", justifyContent:"center", zIndex:9999 }}>
          <div style={{ background:"#fff", borderRadius:12, width:"min(460px,96vw)", boxShadow:"0 24px 64px rgba(0,0,0,0.35)", overflow:"hidden", fontFamily:"system-ui,sans-serif" }}>

            {/* Header */}
            <div style={{ background:"#072654", padding:"16px 20px", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
              <div>
                <div style={{ color:"#fff", fontWeight:700, fontSize:15 }}>Flipkart Clone</div>
                <div style={{ color:"#8eb4e3", fontSize:12 }}>Secure Payment • {money(total)}</div>
              </div>
              <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                <span style={{ background:"#1a9e5c", color:"#fff", fontSize:10, padding:"2px 8px", borderRadius:3, fontWeight:700 }}>TEST MODE</span>
                <button onClick={() => { setRzpOpen(false); setNotice("Payment cancelled"); }}
                  style={{ color:"#8eb4e3", background:"none", border:"none", fontSize:22, cursor:"pointer", lineHeight:1 }}>×</button>
              </div>
            </div>

            {/* Tabs */}
            <div style={{ display:"flex", borderBottom:"2px solid #f0f0f0" }}>
              {[["card","💳 Card"],["upi","📱 UPI"],["netbanking","🏦 Netbanking"]].map(([k,label]) => (
                <button key={k} onClick={() => setRzpTab(k)} style={{
                  flex:1, padding:"11px 0", border:"none", cursor:"pointer",
                  background: rzpTab===k ? "#fff" : "#f8f8f8",
                  borderBottom: rzpTab===k ? "2px solid #072654" : "none",
                  fontWeight: rzpTab===k ? 700 : 400,
                  fontSize:12, color: rzpTab===k ? "#072654" : "#666",
                }}>{label}</button>
              ))}
            </div>

            <div style={{ padding:20 }}>
              {rzpProcessing ? (
                <div style={{ textAlign:"center", padding:"32px 0" }}>
                  <div style={{ fontSize:40, marginBottom:12 }}>⏳</div>
                  <div style={{ fontWeight:700, color:"#072654", fontSize:16 }}>Processing payment...</div>
                  <div style={{ color:"#888", fontSize:13, marginTop:6 }}>Please wait, do not close this window</div>
                  <div style={{ marginTop:20, height:5, background:"#f0f0f0", borderRadius:3, overflow:"hidden" }}>
                    <div style={{ height:"100%", background:"#072654", borderRadius:3, animation:"rzpBar 1.8s ease forwards" }} />
                  </div>
                  <style>{`@keyframes rzpBar{from{width:0}to{width:100%}}`}</style>
                </div>
              ) : (
                <form onSubmit={handleRzpPay}>
                  {rzpTab==="card" && (
                    <div style={{ display:"grid", gap:12 }}>
                      <div style={{ fontSize:12, color:"#555", background:"#fffbe6", border:"1px solid #ffe58f", padding:"7px 10px", borderRadius:5 }}>
                        🧪 Test — any card number, any future expiry, any CVV
                      </div>
                      <input required placeholder="Card number (any 16 digits)" maxLength={19} value={cardNumber}
                        onChange={(e) => setCardNumber(e.target.value.replace(/\D/g,"").replace(/(.{4})/g,"$1 ").trim())}
                        style={rzpInput} />
                      <input required placeholder="Name on card" value={cardName}
                        onChange={(e) => setCardName(e.target.value)} style={rzpInput} />
                      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 }}>
                        <input required placeholder="MM/YY" maxLength={5} value={cardExpiry}
                          onChange={(e) => { let v=e.target.value.replace(/\D/g,""); if(v.length>=2) v=v.slice(0,2)+"/"+v.slice(2,4); setCardExpiry(v); }}
                          style={rzpInput} />
                        <input required placeholder="CVV" maxLength={3} type="password" value={cardCvv}
                          onChange={(e) => setCardCvv(e.target.value.replace(/\D/g,""))} style={rzpInput} />
                      </div>
                      <button type="submit" style={rzpPayBtn}>Pay {money(total)}</button>
                    </div>
                  )}

                  {rzpTab==="upi" && (
                    <div style={{ display:"grid", gap:12 }}>
                      <div style={{ fontSize:12, color:"#555", background:"#fffbe6", border:"1px solid #ffe58f", padding:"7px 10px", borderRadius:5 }}>
                        🧪 Enter any UPI ID — payment always succeeds in test mode
                      </div>
                      <input required placeholder="Enter UPI ID (e.g. name@upi)" value={rzpUpi}
                        onChange={(e) => setRzpUpi(e.target.value)} style={rzpInput} />
                      <button type="submit" style={rzpPayBtn}>Verify & Pay {money(total)}</button>
                    </div>
                  )}

                  {rzpTab==="netbanking" && (
                    <div style={{ display:"grid", gap:12 }}>
                      <div style={{ fontSize:12, color:"#555", background:"#fffbe6", border:"1px solid #ffe58f", padding:"7px 10px", borderRadius:5 }}>
                        🧪 Select any bank — will succeed automatically
                      </div>
                      <select required defaultValue="" style={rzpInput}>
                        <option value="" disabled>Select your bank</option>
                        {["SBI","HDFC Bank","ICICI Bank","Axis Bank","Kotak Bank","PNB","Bank of Baroda","Canara Bank","IndusInd Bank","Yes Bank"].map((b) => (
                          <option key={b} value={b}>{b}</option>
                        ))}
                      </select>
                      <button type="submit" style={rzpPayBtn}>Proceed to Bank</button>
                    </div>
                  )}
                </form>
              )}
            </div>

            <div style={{ padding:"10px 20px", background:"#f8f8f8", textAlign:"center", fontSize:11, color:"#aaa", display:"flex", alignItems:"center", justifyContent:"center", gap:5 }}>
              🔒 Secured by <strong style={{ color:"#072654", marginLeft:3 }}>Razorpay</strong>&nbsp;• Simulated Test Mode
            </div>
          </div>
        </div>
      )}

      {/* ── Payment method selector ───────────────────────────────────────── */}
      <main className="checkout-page">
        <section className="checkout-form">
          <h1>Payment</h1>
          <form onSubmit={handleSubmit}>
            <select value={method} onChange={(e) => setMethod(e.target.value)}>
              <option value="RAZORPAY">💳 Razorpay (Card / UPI / Netbanking)</option>
              <option value="UPI">📱 UPI (Demo)</option>
              <option value="CARD">💳 Debit/Credit Card (Demo)</option>
              <option value="STRIPE">🌐 Stripe (Demo)</option>
              <option value="PAYPAL">🅿 PayPal (Demo)</option>
              <option value="COD">🚚 Cash on Delivery</option>
            </select>

            <input required placeholder="Payer name" value={payerName}
              onChange={(e) => setPayerName(e.target.value)} />

            {method === "UPI" && (
              <input required placeholder="UPI ID" value={upiId} onChange={(e) => setUpiId(e.target.value)} />
            )}
            {method === "CARD" && (
              <input required maxLength="4" placeholder="Last 4 card digits"
                value={cardNumber} onChange={(e) => setCardNumber(e.target.value.replace(/\D/g,""))} />
            )}
            {method === "RAZORPAY" && (
              <div style={{ padding:10, background:"#eaf2ff", borderRadius:6, fontSize:13, color:"#2874f0" }}>
                ✅ A secure Razorpay-style payment window will open. No real card needed — test mode works with any details.
              </div>
            )}

            <button type="submit" disabled={loading}>
              {loading ? "Processing..." : method === "COD" ? "Place Order" : `Pay ${money(total)} & Place Order`}
            </button>
            <button type="button" className="secondary" onClick={() => go("checkout")}>Back to Address</button>
          </form>
        </section>
        <OrderReview cart={cart} />
      </main>
    </>
  );
}

function OrderReview({ cart }) {
  return (
    <section className="order-review">
      <h2>Order Summary</h2>
      {cart.items.map((item) => (
        <div className="review-line" key={item.id}>
          <span>{item.product.title}</span>
          <strong>{item.quantity} × {money(item.product.price)}</strong>
        </div>
      ))}
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
              <p>{order.status} | {order.tracking_status} | {order.payment_method} | {order.payment_status}</p>
            </div>
            <strong>{money(order.total_amount)}</strong>
            <div className="order-items">{order.items.map((item) => <span key={item.id}>{item.quantity} × {item.title}</span>)}</div>
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
          {dashboard.products.map((p) => <div key={p.id}><span>{p.title}</span><strong>{p.stock} left</strong><em>{money(p.price)}</em></div>)}
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

const th = { padding:"8px 12px", textAlign:"left", fontWeight:700, color:"#555" };
const td = { padding:"8px 12px" };

function AdminPage({ setNotice }) {
  const [data, setData]       = useState(null);
  const [tab, setTab]         = useState("overview");
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.adminDashboard().then(setData).catch((e) => setNotice(e.message)).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const deleteUser = async (id) => {
    if (!confirm("Delete this user?")) return;
    try { await api.adminDeleteUser(id); setNotice("User deleted"); load(); } catch(e) { setNotice(e.message); }
  };
  const deleteProduct = async (id) => {
    if (!confirm("Delete this product?")) return;
    try { await api.adminDeleteProduct(id); setNotice("Product deleted"); load(); } catch(e) { setNotice(e.message); }
  };

  if (loading) return <main className="dashboard-page"><div className="empty-state">Loading admin data...</div></main>;
  if (!data) return null;
  const { stats, users, products, orders } = data;

  return (
    <main className="dashboard-page">
      <section style={{ background:"#172337", color:"#fff", padding:"20px 24px", borderRadius:8, marginBottom:20 }}>
        <h1 style={{ margin:0, fontSize:22 }}>🛡️ Admin Dashboard</h1>
        <p style={{ margin:"4px 0 0", color:"#a0aec0", fontSize:13 }}>Full platform overview</p>
      </section>

      <section className="seller-stats" style={{ gridTemplateColumns:"repeat(3,1fr)", marginBottom:20 }}>
        <div><span>Total Users</span><strong>{stats.total_users}</strong></div>
        <div><span>Total Products</span><strong>{stats.total_products}</strong></div>
        <div><span>Total Orders</span><strong>{stats.total_orders}</strong></div>
        <div><span>Revenue</span><strong>{money(stats.total_revenue)}</strong></div>
        <div><span>Paid Orders</span><strong style={{ color:"#388e3c" }}>{stats.paid_orders}</strong></div>
        <div><span>Pending</span><strong style={{ color:"#f44336" }}>{stats.pending_orders}</strong></div>
      </section>

      <div style={{ display:"flex", gap:10, marginBottom:16 }}>
        {["overview","users","products","orders"].map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding:"8px 20px", borderRadius:4, border:"none",
            background: tab===t ? "#2874f0" : "#f0f0f0",
            color: tab===t ? "#fff" : "#333", fontWeight:700, cursor:"pointer",
          }}>{t.charAt(0).toUpperCase()+t.slice(1)}</button>
        ))}
      </div>

      {tab==="overview" && (
        <section className="dashboard-card">
          <h1>Platform Summary</h1>
          <ul style={{ lineHeight:2.2, color:"#444" }}>
            <li>👥 <strong>{stats.total_users}</strong> registered users</li>
            <li>📦 <strong>{stats.total_products}</strong> products listed</li>
            <li>🛒 <strong>{stats.total_orders}</strong> orders placed</li>
            <li>💰 Total revenue: <strong>{money(stats.total_revenue)}</strong></li>
            <li>✅ <strong>{stats.paid_orders}</strong> paid | ⏳ <strong>{stats.pending_orders}</strong> pending</li>
          </ul>
        </section>
      )}

      {tab==="users" && (
        <section className="dashboard-card">
          <h1>All Users ({users.length})</h1>
          <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
            <thead><tr style={{ background:"#f5f5f5" }}>
              <th style={th}>ID</th><th style={th}>Name</th><th style={th}>Email</th>
              <th style={th}>Role</th><th style={th}>Phone</th><th style={th}>Action</th>
            </tr></thead>
            <tbody>{users.map((u) => (
              <tr key={u.id} style={{ borderBottom:"1px solid #f0f0f0" }}>
                <td style={td}>{u.id}</td><td style={td}>{u.name}</td><td style={td}>{u.email}</td>
                <td style={td}><span style={{ padding:"2px 8px", borderRadius:4, background:u.role==="seller"?"#fff3e0":"#e8f5e9", color:u.role==="seller"?"#e65100":"#2e7d32", fontWeight:700, fontSize:11 }}>{u.role}</span></td>
                <td style={td}>{u.phone}</td>
                <td style={td}><button onClick={() => deleteUser(u.id)} style={{ color:"#f44336", background:"none", border:"1px solid #f44336", borderRadius:4, padding:"3px 10px", cursor:"pointer", fontSize:12 }}>Delete</button></td>
              </tr>
            ))}</tbody>
          </table>
        </section>
      )}

      {tab==="products" && (
        <section className="dashboard-card">
          <h1>All Products ({products.length})</h1>
          <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
            <thead><tr style={{ background:"#f5f5f5" }}>
              <th style={th}>ID</th><th style={th}>Title</th><th style={th}>Brand</th>
              <th style={th}>Price</th><th style={th}>Stock</th><th style={th}>Category</th><th style={th}>Action</th>
            </tr></thead>
            <tbody>{products.map((p) => (
              <tr key={p.id} style={{ borderBottom:"1px solid #f0f0f0" }}>
                <td style={td}>{p.id}</td><td style={td}>{p.title}</td><td style={td}>{p.brand}</td>
                <td style={td}>{money(p.price)}</td>
                <td style={td}><span style={{ color:p.stock<5?"#f44336":"#388e3c", fontWeight:700 }}>{p.stock}</span></td>
                <td style={td}>{p.category?.name}</td>
                <td style={td}><button onClick={() => deleteProduct(p.id)} style={{ color:"#f44336", background:"none", border:"1px solid #f44336", borderRadius:4, padding:"3px 10px", cursor:"pointer", fontSize:12 }}>Delete</button></td>
              </tr>
            ))}</tbody>
          </table>
        </section>
      )}

      {tab==="orders" && (
        <section className="dashboard-card">
          <h1>All Orders ({orders.length})</h1>
          {orders.map((order) => (
            <article className="order-card" key={order.id}>
              <div>
                <h2>{order.order_number}</h2>
                <p>{order.customer_name} | {order.city} | {order.payment_method} |{" "}
                  <span style={{ color:order.payment_status==="PAID"?"#388e3c":"#e65100", fontWeight:700 }}>{order.payment_status}</span>
                </p>
              </div>
              <strong>{money(order.total_amount)}</strong>
              <div className="order-items">{order.items.map((item) => <span key={item.id}>{item.quantity} × {item.title}</span>)}</div>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}

function AIChatWidget({ open, setOpen, messages, sendMessage, loading }) {
  const [draft, setDraft] = useState("");
  const starters = [
    "Suggest a phone under 25000",
    "How do payments work here?",
    "Show me my recent orders",
  ];
  const showStarters = messages.length <= 1;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!draft.trim() || loading) return;
    const text = draft.trim();
    setDraft("");
    await sendMessage(text);
  };

  return (
    <section className={open ? "ai-chat open" : "ai-chat"}>
      {open ? (
        <div className="ai-chat-panel">
          <div className="ai-chat-header">
            <div>
              <strong>Flipkart AI Bot</strong>
              <span>OpenAI-powered shopping help</span>
            </div>
            <button onClick={() => setOpen(false)}>Close</button>
          </div>
          <div className="ai-chat-body">
            {messages.map((message, index) => (
              <article key={`${message.role}-${index}`} className={message.role === "assistant" ? "ai-msg assistant" : "ai-msg user"}>
                <span>{message.role === "assistant" ? "AI" : "You"}</span>
                <p>{message.content}</p>
              </article>
            ))}
            {showStarters && (
              <div className="ai-starters">
                {starters.map((starter) => (
                  <button key={starter} onClick={() => sendMessage(starter)}>{starter}</button>
                ))}
              </div>
            )}
            {loading && <div className="ai-msg assistant"><span>AI</span><p>Thinking...</p></div>}
          </div>
          <form className="ai-chat-form" onSubmit={handleSubmit}>
            <input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask about products, orders, payments..." />
            <button type="submit" disabled={loading}>Send</button>
          </form>
        </div>
      ) : (
        <button className="ai-chat-launcher" onClick={() => setOpen(true)}>Ask AI</button>
      )}
    </section>
  );
}

function ConfirmationPage({ order, go }) {
  return (
    <main className="confirmation">
      <div>
        <span className="success-mark">✓</span>
        <h1>Order placed successfully!</h1>
        <p>Your order ID is <strong>{order?.order_number}</strong>.</p>
        <p>Payment: <strong>{order?.payment_method}</strong> | <strong>{order?.payment_status}</strong></p>
        <p style={{ color:"#388e3c", fontSize:13 }}>📧 A confirmation email has been sent to your registered email address.</p>
        <button onClick={() => go("orders")}>View Order Summary</button>
      </div>
    </main>
  );
}

export default function App() {
  const [page, setPage]                       = useState("home");
  const [activeRole, setActiveRole]           = useState("buyer");
  const [query, setQuery]                     = useState("");
  const [filters, setFilters]                 = useState({ category:"all", max_price:"", min_rating:"" });
  const [categories, setCategories]           = useState([]);
  const [products, setProducts]               = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [productReviews, setProductReviews]   = useState([]);
  const [wishlist, setWishlist]               = useState([]);
  const [cart, setCart]                       = useState(emptyCart);
  const [users, setUsers]                     = useState([]);
  const [authUser, setAuthUser]               = useState(null);
  const [orders, setOrders]                   = useState([]);
  const [sellerDashboard, setSellerDashboard] = useState(null);
  const [checkoutAddress, setCheckoutAddress] = useState(null);
  const [order, setOrder]                     = useState(null);
  const [loading, setLoading]                 = useState(false);
  const [notice, setNotice]                   = useState("");
  const [chatOpen, setChatOpen]               = useState(false);
  const [chatLoading, setChatLoading]         = useState(false);
  const [chatMessages, setChatMessages]       = useState([
    { role: "assistant", content: "Hi, I am the Flipkart AI bot. Ask me about products, payments, orders, or general shopping questions." },
  ]);

  const buyer       = authUser || users.find((u) => u.id === BUYER_ID);
  const seller      = users.find((u) => u.id === SELLER_ID);
  const currentUser = authUser || (activeRole === "buyer" ? buyer : seller);
  const cartCount   = useMemo(() => cart.items.reduce((t,i) => t+i.quantity, 0), [cart.items]);

  const refreshOrders = () => api.orders().then(setOrders).catch((e) => setNotice(e.message));
  const refreshSeller = () => api.sellerDashboard(SELLER_ID).then(setSellerDashboard).catch((e) => setNotice(e.message));

  useEffect(() => {
    api.users().then(setUsers).catch((e) => setNotice(e.message));
    api.categories().then(setCategories).catch((e) => setNotice(e.message));
    api.cart().then(setCart).catch(() => setCart(emptyCart));
    api.wishlist().then((p) => setWishlist(p.items)).catch(() => setWishlist([]));
    refreshOrders(); refreshSeller();
  }, []);

  useEffect(() => {
    setLoading(true);
    const t = setTimeout(() => {
      api.products({ search:query, category:filters.category, max_price:filters.max_price, min_rating:filters.min_rating })
        .then(setProducts).catch((e) => setNotice(e.message)).finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(t);
  }, [query, filters]);

  useEffect(() => {
    if (activeRole === "seller") setPage("seller");
    if (activeRole === "buyer" && page === "seller") setPage("home");
  }, [activeRole]);

  const go = (nextPage) => {
    if (nextPage === "orders") refreshOrders();
    if (nextPage === "seller") refreshSeller();
    if (nextPage === "payment" && !checkoutAddress) { setNotice("Please add delivery address first"); setPage("checkout"); return; }
    setPage(nextPage);
  };

  const openProduct = async (id) => {
    try { setSelectedProduct(await api.product(id)); setProductReviews(await api.reviews(id)); setPage("detail"); }
    catch(e) { setNotice(e.message); }
  };

  const addToCart = async (productId) => {
    try { setCart(await api.addToCart(productId)); setNotice("Added to cart"); }
    catch(e) { setNotice(e.message); }
  };

  const buyNow = async (productId) => {
    try { setCart(await api.addToCart(productId)); setPage("checkout"); }
    catch(e) { setNotice(e.message); }
  };

  const placeOrder = async (payment) => {
    try {
      if (!checkoutAddress) { setNotice("Please add delivery address first"); setPage("checkout"); return; }
      const placed = await api.placeOrder({ address: checkoutAddress, payment });
      setOrder(placed); setCart(emptyCart); setCheckoutAddress(null);
      refreshOrders(); refreshSeller(); setPage("confirmation");
    } catch(e) { setNotice(e.message); }
  };

  const login = async (payload) => {
    try {
      const result = await api.login({ email:payload.email, password:payload.password });
      setAuthUser(result.user);
      if (result.user.role === "admin") { setNotice("Welcome, Admin!"); setPage("admin"); }
      else { setNotice("Logged in"); setPage("home"); }
    } catch(e) { setNotice(e.message); }
  };

  const signup = async (payload) => {
    try {
      const result = await api.signup(payload);
      setAuthUser(result.user);
      setUsers((c) => [result.user, ...c.filter((u) => u.id !== result.user.id)]);
      setNotice("Account created"); setPage("home");
    } catch(e) { setNotice(e.message); }
  };

  const googleLogin = async (payload) => {
    try {
      const result = await api.googleLogin(payload);
      setAuthUser(result.user); setNotice("Signed in with Google demo"); setPage("home");
    } catch(e) { setNotice(e.message); }
  };

  const toggleWishlist = async (productId) => {
    try { const p = await api.toggleWishlist(productId); setWishlist(p.items); }
    catch(e) { setNotice(e.message); }
  };

  const addReview = async (payload) => {
    try { await api.addReview(payload); setProductReviews(await api.reviews(payload.product_id)); setNotice("Review submitted"); }
    catch(e) { setNotice(e.message); }
  };

  const sendChatMessage = async (message) => {
    const nextMessages = [...chatMessages, { role: "user", content: message }];
    setChatMessages(nextMessages);
    setChatLoading(true);
    try {
      const result = await api.aiChat({
        message,
        history: nextMessages.slice(-10).map((item) => ({ role: item.role, content: item.content })),
      });
      setChatMessages((current) => [...current, { role: "assistant", content: result.reply }]);
      setChatOpen(true);
    } catch (error) {
      setNotice(error.message);
      setChatMessages((current) => [...current, { role: "assistant", content: `I hit a snag: ${error.message}` }]);
      setChatOpen(true);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <ErrorBoundary>
      <Header query={query} setQuery={setQuery} cartCount={cartCount} page={page} go={go}
        activeRole={activeRole} setActiveRole={setActiveRole} currentUser={currentUser} />
      {notice && <button className="toast" onClick={() => setNotice("")}>{notice} ✕</button>}
      {page==="auth"         && <AuthPage login={login} signup={signup} googleLogin={googleLogin} />}
      {page==="home"         && <HomePage products={products} categories={categories} filters={filters} setFilters={setFilters} openProduct={openProduct} loading={loading} buyer={buyer} wishlistIds={wishlist.map((i)=>i.id)} toggleWishlist={toggleWishlist} />}
      {(page==="buyer"||page==="orders") && <OrdersPage orders={orders} buyer={buyer} go={go} />}
      {page==="seller"       && <SellerPage dashboard={sellerDashboard} />}
      {page==="admin"        && <AdminPage setNotice={setNotice} />}
      {page==="detail"       && <ProductDetail product={selectedProduct} onBack={() => setPage("home")} addToCart={addToCart} buyNow={buyNow} reviews={productReviews} addReview={addReview} />}
      {page==="cart"         && <CartPage cart={cart} updateCart={(id,qty)=>api.updateCart(id,qty).then(setCart)} removeCart={(id)=>api.removeCart(id).then(setCart)} go={go} />}
      {page==="checkout"     && <CheckoutPage cart={cart} buyer={buyer} setCheckoutAddress={setCheckoutAddress} go={go} />}
      {page==="payment"      && <PaymentPage cart={cart} checkoutAddress={checkoutAddress} placeOrder={placeOrder} go={go} setNotice={setNotice} />}
      {page==="confirmation" && <ConfirmationPage order={order} go={go} />}
      <AIChatWidget open={chatOpen} setOpen={setChatOpen} messages={chatMessages} sendMessage={sendChatMessage} loading={chatLoading} />
    </ErrorBoundary>
  );
}
