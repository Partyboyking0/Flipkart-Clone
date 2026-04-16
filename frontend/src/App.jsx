import React, { Component, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AUTH_EXPIRED_EVENT, api } from "./api";

const emptyCart = { items: [], summary: { mrp_total: 0, subtotal: 0, discount: 0, delivery_fee: 0, total: 0 } };
const defaultChatMessages = [
  { role: "assistant", content: "Hi, I am the Flipkart AI bot. Ask me about products, payments, orders, or general shopping questions." },
];
const orderSteps = ["PLACED", "PACKED", "SHIPPED", "DELIVERED"];
const heroBanners = [
  {
    title: "Big Saving Days",
    subtitle: "Fresh picks across mobiles, appliances, fashion, and daily essentials.",
    image: "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?auto=format&fit=crop&w=1400&q=80",
    accent: "Up to 70% off",
  },
  {
    title: "Upgrade Your Tech",
    subtitle: "Top-rated gadgets with exchange-friendly prices and fast delivery.",
    image: "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1400&q=80",
    accent: "Trending now",
  },
  {
    title: "Home Comfort Edit",
    subtitle: "Smart picks for kitchens, living spaces, and everyday convenience.",
    image: "https://images.unsplash.com/photo-1556911220-bff31c812dba?auto=format&fit=crop&w=1400&q=80",
    accent: "Limited-time deals",
  },
];
const footerColumns = [
  { title: "About", links: ["Contact Us", "About Us", "Careers", "Stories"] },
  { title: "Help", links: ["Payments", "Shipping", "Cancellation", "FAQ"] },
  { title: "Policy", links: ["Return Policy", "Terms Of Use", "Security", "Privacy"] },
  { title: "Social", links: ["Facebook", "X", "YouTube", "Instagram"] },
];

const money = (value) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value || 0);

const rzpInput = {
  width: "100%",
  padding: "10px 12px",
  border: "1px solid #ddd",
  borderRadius: 6,
  fontSize: 14,
  outline: "none",
  boxSizing: "border-box",
};

const rzpPayBtn = {
  width: "100%",
  padding: "12px",
  background: "#172337",
  color: "#fff",
  border: "none",
  borderRadius: 6,
  fontWeight: 700,
  fontSize: 15,
  cursor: "pointer",
};

function statusTone(status) {
  if (["PAID", "APPROVED", "DELIVERED", "ACTIVE", "RESOLVED", "VERIFIED"].includes(status)) return "good";
  if (["PENDING", "PLACED", "PACKED", "SHIPPED", "IN_REVIEW", "REQUESTED"].includes(status)) return "warn";
  return "bad";
}

function percentageOff(product) {
  if (!product?.mrp) return 0;
  return Math.round(((product.mrp - product.price) / product.mrp) * 100);
}

function readFilesAsDataUrls(files) {
  return Promise.all(
    files.map(
      (file) =>
        new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result));
          reader.onerror = reject;
          reader.readAsDataURL(file);
        }),
    ),
  );
}

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

function StatusBadge({ value }) {
  const tone = statusTone(value || "");
  return <span className={`status-badge ${tone}`}>{value || "UNKNOWN"}</span>;
}

function TrackingTimeline({ status }) {
  const currentIndex = Math.max(orderSteps.indexOf(status || "PLACED"), 0);
  return (
    <div className="tracking-line">
      {orderSteps.map((step, index) => (
        <div key={step} className={index <= currentIndex ? "tracking-step active" : "tracking-step"}>
          <span>{index + 1}</span>
          <strong>{step}</strong>
        </div>
      ))}
    </div>
  );
}

function GoogleSignInButton({ googleLogin, selectedRole }) {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
  const ref = useRef(null);
  const [error, setError] = useState("");
  const origin = typeof window !== "undefined" ? window.location.origin : "";

  useEffect(() => {
    if (!clientId || !ref.current) return undefined;
    let mounted = true;

    const renderButton = () => {
      if (!mounted || !window.google?.accounts?.id || !ref.current) return;
      ref.current.innerHTML = "";
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: ({ credential }) => {
          if (credential) googleLogin({ credential, provider: "google", role: selectedRole });
        },
      });
      window.google.accounts.id.renderButton(ref.current, {
        theme: "outline",
        size: "large",
        text: "continue_with",
        shape: "rectangular",
        width: 320,
      });
    };

    const existing = document.querySelector("script[data-google-gsi]");
    if (existing && window.google?.accounts?.id) {
      renderButton();
      return () => {
        mounted = false;
      };
    }

    const script = existing || document.createElement("script");
    if (!existing) {
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.dataset.googleGsi = "true";
      script.onload = renderButton;
      script.onerror = () => mounted && setError("Google sign-in could not load.");
      document.head.appendChild(script);
    } else {
      script.addEventListener("load", renderButton);
    }

    return () => {
      mounted = false;
      if (existing) existing.removeEventListener("load", renderButton);
    };
  }, [clientId, googleLogin]);

  if (!clientId) {
    return <p className="helper-text">Add VITE_GOOGLE_CLIENT_ID in frontend/.env and restart Vite to enable Google sign-in.</p>;
  }

  return (
    <div className="oauth-box">
      <div ref={ref} />
      <p className="helper-text">Continue with Google as a <strong>{selectedRole}</strong>.</p>
      {origin && <p className="helper-text">Authorized JavaScript origin: <strong>{origin}</strong></p>}
      {error && <p className="helper-text bad-text">{error}</p>}
    </div>
  );
}

function Header({ query, setQuery, cartCount, currentUser, go, logout }) {
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
  const isAdmin = currentUser?.role === "admin";
  const isSeller = currentUser?.role === "seller";
  const primaryLabel = currentUser ? currentUser.name.split(" ")[0] : "Login";
  const sellerActionLabel = isAdmin ? "Admin" : "Seller";
  const moreLabel = isAdmin ? "Analytics" : currentUser?.role === "buyer" ? "Orders" : "More";
  const locationLabel = currentUser?.city ? `${currentUser.city}, ${currentUser.state}` : "Location not set";
  const locationAction = currentUser?.address_line ? "View saved address" : "Select delivery location";
  const openPrimary = () => go(currentUser ? (isAdmin ? "admin" : isSeller ? "seller" : "account") : "auth");
  const openSeller = () => go(isAdmin ? "admin" : "seller");
  const openMore = () => {
    if (!currentUser) {
      go("auth");
      return;
    }
    if (isAdmin) {
      go("admin");
      return;
    }
    if (isSeller) {
      go("seller");
      return;
    }
    go("orders");
  };

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="topbar-utility">
          <div className="topbar-utility-left">
            <button className="brand brand-badge" onClick={() => go("home")} aria-label="Go home">
              <span>Flipkart</span>
              <small>Explore <strong>Plus</strong></small>
            </button>
            <button className="utility-pill desktop-only" type="button" onClick={() => go("home")}>Travel</button>
          </div>

          <button className="utility-location desktop-only" type="button" onClick={() => go(currentUser ? "account" : "auth")}>
            <strong>{locationLabel}</strong>
            <span>{locationAction}</span>
          </button>
        </div>

        <div className="topbar-main">
          <div className="topbar-center">
            <button className="mobile-icon-button mobile-only" onClick={() => setMobileSearchOpen((value) => !value)}>
              Search
            </button>

            <label className={mobileSearchOpen ? "search open" : "search"}>
              <span className="search-icon" aria-hidden="true">Search</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search for products, brands and more"
              />
            </label>
          </div>

          <div className="topbar-right">
            <nav className="nav-actions">
              <button className="nav-login" onClick={openPrimary}>{primaryLabel}</button>
              <button className="nav-link desktop-only" onClick={openSeller}>{sellerActionLabel}</button>
              <button className="nav-link" onClick={openMore}>{moreLabel} <span className="caret">v</span></button>
              {!isAdmin && <button className="nav-link nav-cart" onClick={() => go(currentUser ? "cart" : "auth")}>Cart <span>{cartCount}</span></button>}
              {currentUser && !isAdmin && <button className="nav-link desktop-only" onClick={() => go("account")}>Account</button>}
              {currentUser && <button className="nav-link desktop-only" onClick={logout}>Logout</button>}
            </nav>
          </div>
        </div>
      </div>
    </header>
  );
}

function UserPanel({ user }) {
  if (!user) return null;
  return (
    <section className="user-panel">
      <div>
        <h2>{user.role === "seller" ? user.store_name || user.name : user.name}</h2>
        <p>{user.email}</p>
      </div>
      <div>
        <span>{user.phone}</span>
        <strong>{user.city}, {user.state} - {user.pincode}</strong>
      </div>
    </section>
  );
}

function ProductCard({ product, openProduct, wished, toggleWishlist }) {
  return (
    <article className="product-card" onClick={() => openProduct(product.id)}>
      <button
        className={wished ? "wish-button wished" : "wish-button"}
        onClick={(event) => {
          event.stopPropagation();
          toggleWishlist(product.id);
        }}
      >
        {wished ? "Wishlisted" : "Wishlist"}
      </button>
      <div className="product-image">
        <img src={product.images[0]?.url} alt={product.images[0]?.alt || product.title} />
      </div>
      <h3>{product.title}</h3>
      <div className="rating-row">
        <span className="rating">{product.rating} star</span>
        <span>({product.reviews.toLocaleString("en-IN")})</span>
      </div>
      <div className="price-row">
        <strong>{money(product.price)}</strong>
        <span>{money(product.mrp)}</span>
        <em>{percentageOff(product)}% off</em>
      </div>
      <p>{product.stock > 0 ? "In stock" : "Out of stock"}</p>
    </article>
  );
}

function ProductRail({ title, items, openProduct, wishlistIds, toggleWishlist, emptyText = "Nothing here yet." }) {
  return (
    <section className="dashboard-card">
      <div className="section-head">
        <h2>{title}</h2>
        <span>{items.length} items</span>
      </div>
      {items.length ? (
        <div className="mini-grid">
          {items.map((product) => (
            <ProductCard
              key={`${title}-${product.id}`}
              product={product}
              openProduct={openProduct}
              wished={wishlistIds.includes(product.id)}
              toggleWishlist={toggleWishlist}
            />
          ))}
        </div>
      ) : (
        <div className="empty-state">{emptyText}</div>
      )}
    </section>
  );
}

function DealCard({ product, openProduct, wished, toggleWishlist }) {
  return (
    <article className="deal-card" onClick={() => openProduct(product.id)}>
      <button
        className={wished ? "deal-wish active" : "deal-wish"}
        onClick={(event) => {
          event.stopPropagation();
          toggleWishlist(product.id);
        }}
      >
        {wished ? "Saved" : "Wishlist"}
      </button>
      <div className="deal-card-media">
        <img src={product.images[0]?.url} alt={product.images[0]?.alt || product.title} />
      </div>
      <h3 title={product.title}>{product.title}</h3>
      <strong>{percentageOff(product)}% Off</strong>
      <span>{product.brand}</span>
    </article>
  );
}

function CategoryStrip({ categories, products, activeCategory, selectCategory }) {
  const allPreview = products[0]?.images?.[0]?.url || heroBanners[0].image;
  const items = [{ id: "all", name: "For You", slug: "all", preview: allPreview }].concat(categories.slice(0, 7).map((category, index) => {
    const preview = products.find((product) => product.category.slug === category.slug)?.images?.[0]?.url || heroBanners[index % heroBanners.length].image;
    return { ...category, preview };
  }));

  return (
    <section className="category-strip">
      <div className="category-strip-inner">
        {items.map((category) => (
          <button
            key={category.id}
            className={activeCategory === category.slug ? "category-chip active" : "category-chip"}
            onClick={() => selectCategory(category.slug)}
          >
            <span className="category-image-wrap">
              <img src={category.preview} alt={category.name} />
            </span>
            <span>{category.name}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function HeroCarousel() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setIndex((current) => (current + 1) % heroBanners.length);
    }, 4500);
    return () => window.clearInterval(timer);
  }, []);

  const activeBanner = heroBanners[index];

  return (
    <section className="hero-carousel">
      <button className="hero-arrow left" onClick={() => setIndex((current) => (current - 1 + heroBanners.length) % heroBanners.length)}>
        {"<"}
      </button>
      <div className="hero-slide">
        <img src={activeBanner.image} alt={activeBanner.title} />
        <div className="hero-copy">
          <span>{activeBanner.accent}</span>
          <h1>{activeBanner.title}</h1>
          <p>{activeBanner.subtitle}</p>
        </div>
      </div>
      <button className="hero-arrow right" onClick={() => setIndex((current) => (current + 1) % heroBanners.length)}>
        {">"}
      </button>
      <div className="hero-dots">
        {heroBanners.map((banner, dotIndex) => (
          <button
            key={banner.title}
            className={dotIndex === index ? "hero-dot active" : "hero-dot"}
            onClick={() => setIndex(dotIndex)}
            aria-label={`Show ${banner.title}`}
          />
        ))}
      </div>
    </section>
  );
}

function DealsSection({ title, items, countdown, openProduct, wishlistIds, toggleWishlist, onViewAll, hint }) {
  if (!items.length) return null;

  return (
    <section className="deal-section">
      <div className="deal-section-head">
        <div>
          <h2>{title}</h2>
          {countdown ? <p>{countdown}</p> : hint ? <p>{hint}</p> : null}
        </div>
        <button onClick={onViewAll}>View All</button>
      </div>
      <div className="deal-track">
        {items.map((product) => (
          <DealCard
            key={`${title}-${product.id}`}
            product={product}
            openProduct={openProduct}
            wished={wishlistIds.includes(product.id)}
            toggleWishlist={toggleWishlist}
          />
        ))}
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="footer-links-grid">
          {footerColumns.map((column) => (
            <section key={column.title}>
              <h2>{column.title}</h2>
              {column.links.map((link) => (
                <a key={link} href="#">{link}</a>
              ))}
            </section>
          ))}
          <section className="footer-address-block">
            <h2>Mail Us</h2>
            <p>Flipkart Clone Internet Private Limited</p>
            <p>Buildings Alyssa, Begonia and Clover</p>
            <p>Bengaluru, Karnataka, India</p>
          </section>
          <section className="footer-address-block">
            <h2>Registered Office Address</h2>
            <p>Flipkart Clone Campus, Outer Ring Road</p>
            <p>Bengaluru, Karnataka, India</p>
            <p>Support: support@flipkartclone.local</p>
          </section>
        </div>
        <div className="footer-bottom">
          <small>Copyright 2026 Flipkart Clone. All rights reserved.</small>
          <div className="payment-pill-row">
            {["Visa", "Mastercard", "UPI", "Razorpay", "PayPal", "COD"].map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}

function HomePage({
  products,
  categories,
  filters,
  setFilters,
  query,
  openProduct,
  loading,
  buyer,
  wishlistIds,
  toggleWishlist,
  recommendations,
  recentlyViewed,
}) {
  const updateFilter = (key, value) => setFilters((current) => ({ ...current, [key]: value }));
  const activeSearch = query.trim().length > 0;
  const hasActiveFilters = activeSearch || filters.category !== "all" || filters.max_price || filters.min_rating;
  const [countdown, setCountdown] = useState("");

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const target = new Date(now);
      target.setHours(23, 59, 59, 0);
      const diff = Math.max(target.getTime() - now.getTime(), 0);
      const hours = String(Math.floor(diff / (1000 * 60 * 60))).padStart(2, "0");
      const minutes = String(Math.floor((diff / (1000 * 60)) % 60)).padStart(2, "0");
      const seconds = String(Math.floor((diff / 1000) % 60)).padStart(2, "0");
      setCountdown(`Ends in ${hours}:${minutes}:${seconds}`);
    };
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const sections = categories
    .map((category) => ({
      category,
      items: products.filter((product) => product.category.slug === category.slug).slice(0, 6),
    }))
    .filter((section) => section.items.length);

  return (
    <main className="storefront-page">
      <CategoryStrip categories={categories} products={products} activeCategory={filters.category} selectCategory={updateFilter.bind(null, "category")} />
      <div className="storefront-main">
        <HeroCarousel />
        <section className="filter-ribbon">
          <div className="filter-ribbon-head">
            <div>
              <h2>{hasActiveFilters ? "Filtered results" : "Discover top picks"}</h2>
              <p>{loading ? "Updating products..." : `${products.length} products ready to explore`}</p>
            </div>
            <button className="clear-filters" onClick={() => setFilters({ category: "all", max_price: "", min_rating: "" })}>
              Clear Filters
            </button>
          </div>
          <div className="filter-ribbon-controls">
            <label>
              Category
              <select value={filters.category} onChange={(event) => updateFilter("category", event.target.value)}>
                <option value="all">All Categories</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.slug}>{category.name}</option>
                ))}
              </select>
            </label>
            <label>
              Max Price
              <input type="number" value={filters.max_price} onChange={(event) => updateFilter("max_price", event.target.value)} placeholder="50000" />
            </label>
            <label>
              Min Rating
              <select value={filters.min_rating} onChange={(event) => updateFilter("min_rating", event.target.value)}>
                <option value="">Any</option>
                <option value="4">4+</option>
                <option value="4.5">4.5+</option>
              </select>
            </label>
          </div>
        </section>

        {buyer?.role === "buyer" ? <UserPanel user={buyer} /> : null}

        {buyer?.role === "buyer" && recommendations.length ? (
          <DealsSection
            title="Recommended For You"
            items={recommendations.slice(0, 6)}
            hint="AI-backed picks based on your browsing."
            openProduct={openProduct}
            wishlistIds={wishlistIds}
            toggleWishlist={toggleWishlist}
            onViewAll={() => setFilters((current) => ({ ...current, category: "all" }))}
          />
        ) : null}

        {buyer?.role === "buyer" && recentlyViewed.length ? (
          <DealsSection
            title="Recently Viewed"
            items={recentlyViewed.slice(0, 6)}
            hint="Pick up where you left off."
            openProduct={openProduct}
            wishlistIds={wishlistIds}
            toggleWishlist={toggleWishlist}
            onViewAll={() => setFilters((current) => ({ ...current, category: "all" }))}
          />
        ) : null}

        {loading ? (
          <section className="deal-section">
            <div className="empty-state">Loading products...</div>
          </section>
        ) : products.length ? (
          <>
            <DealsSection
              title={hasActiveFilters ? "Search Results" : "Deals of the Day"}
              items={products.slice(0, 10)}
              countdown={hasActiveFilters ? "" : countdown}
              hint={hasActiveFilters ? "Search, price, rating, and category filters are applied." : ""}
              openProduct={openProduct}
              wishlistIds={wishlistIds}
              toggleWishlist={toggleWishlist}
              onViewAll={() => setFilters((current) => ({ ...current, category: "all" }))}
            />

            {!hasActiveFilters && sections.slice(0, 4).map((section) => (
              <DealsSection
                key={section.category.id}
                title={section.category.name}
                items={section.items}
                hint={`Fresh ${section.category.name.toLowerCase()} picks`}
                openProduct={openProduct}
                wishlistIds={wishlistIds}
                toggleWishlist={toggleWishlist}
                onViewAll={() => updateFilter("category", section.category.slug)}
              />
            ))}
          </>
        ) : (
          <section className="deal-section">
            <div className="empty-state">No products matched your search.</div>
          </section>
        )}
      </div>
    </main>
  );
}

function ProductDetail({ product, onBack, addToCart, buyNow, reviews, addReview }) {
  const [imageIndex, setImageIndex] = useState(0);
  const [reviewForm, setReviewForm] = useState({ rating: 5, comment: "" });
  if (!product) return null;

  const image = product.images[imageIndex] || product.images[0];

  return (
    <main className="detail-page">
      <button className="back-link" onClick={onBack}>Back to products</button>
      <section className="detail-layout">
        <div className="gallery">
          <div className="thumbs">
            {product.images.map((item, index) => (
              <button key={item.id} className={imageIndex === index ? "selected" : ""} onClick={() => setImageIndex(index)}>
                <img src={item.url} alt={item.alt} />
              </button>
            ))}
          </div>
          <div className="hero-image">
            <img src={image?.url} alt={image?.alt || product.title} />
          </div>
        </div>
        <div className="detail-info">
          <p className="brand-name">{product.brand}</p>
          <h1>{product.title}</h1>
          <div className="rating-row">
            <span className="rating">{product.rating} star</span>
            <span>{product.reviews.toLocaleString("en-IN")} ratings and reviews</span>
          </div>
          <div className="detail-price">
            <strong>{money(product.price)}</strong>
            <span>{money(product.mrp)}</span>
            <em>{percentageOff(product)}% off</em>
          </div>
          <p className={product.stock > 0 ? "stock in" : "stock out"}>
            {product.stock > 0 ? `${product.stock} in stock` : "Out of stock"}
          </p>
          <p className="description">{product.description}</p>
          <div className="detail-actions">
            <button onClick={() => addToCart(product.id)} disabled={product.stock === 0}>Add to Cart</button>
            <button className="buy" onClick={() => buyNow(product.id)} disabled={product.stock === 0}>Buy Now</button>
          </div>
          <section className="specs">
            <h2>Specifications</h2>
            {product.specs.map((spec) => (
              <div key={spec.id}>
                <span>{spec.name}</span>
                <strong>{spec.value}</strong>
              </div>
            ))}
          </section>
          <section className="reviews">
            <h2>Reviews and Ratings</h2>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                addReview({ product_id: product.id, rating: Number(reviewForm.rating), comment: reviewForm.comment });
                setReviewForm({ rating: 5, comment: "" });
              }}
            >
              <select value={reviewForm.rating} onChange={(event) => setReviewForm((current) => ({ ...current, rating: event.target.value }))}>
                {[5, 4, 3, 2, 1].map((rating) => (
                  <option key={rating} value={rating}>{rating} star</option>
                ))}
              </select>
              <input required value={reviewForm.comment} onChange={(event) => setReviewForm((current) => ({ ...current, comment: event.target.value }))} placeholder="Write a review" />
              <button type="submit">Submit</button>
            </form>
            {reviews.map((review) => (
              <article className="review-card" key={review.id}>
                <strong>{review.rating} star by {review.user.name}</strong>
                <div className="inline-metadata">
                  {review.verified_purchase && <StatusBadge value="VERIFIED" />}
                </div>
                <p>{review.comment}</p>
                {review.seller_response && (
                  <div className="seller-response">
                    <strong>Seller response</strong>
                    <p>{review.seller_response}</p>
                  </div>
                )}
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
        {cart.items.length ? (
          cart.items.map((item) => (
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
          ))
        ) : (
          <div className="empty-state">Your cart is empty.</div>
        )}
      </section>
      <PriceBox summary={cart.summary} action={cart.items.length ? () => go("checkout") : null} label="Continue to Checkout" />
    </main>
  );
}

function CheckoutPage({ cart, buyer, addresses, setCheckoutAddress, go, saveAddress }) {
  const defaultAddress = addresses.find((address) => address.is_default) || addresses[0];
  const [form, setForm] = useState({
    label: defaultAddress?.label || "Home",
    customer_name: defaultAddress?.customer_name || buyer?.name || "",
    phone: defaultAddress?.phone || buyer?.phone || "",
    address_line: defaultAddress?.address_line || buyer?.address_line || "",
    city: defaultAddress?.city || buyer?.city || "",
    state: defaultAddress?.state || buyer?.state || "",
    pincode: defaultAddress?.pincode || buyer?.pincode || "",
  });
  const [saveToBook, setSaveToBook] = useState(false);
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  return (
    <main className="checkout-page">
      <section className="checkout-form">
        <h1>Delivery Address</h1>
        {addresses.length ? (
          <div className="picker-grid">
            {addresses.map((address) => (
              <button
                key={address.id}
                type="button"
                className={address.is_default ? "picker-card selected" : "picker-card"}
                onClick={() =>
                  setForm({
                    label: address.label,
                    customer_name: address.customer_name,
                    phone: address.phone,
                    address_line: address.address_line,
                    city: address.city,
                    state: address.state,
                    pincode: address.pincode,
                  })
                }
              >
                <strong>{address.label}</strong>
                <span>{address.address_line}</span>
                <small>{address.city}, {address.state} - {address.pincode}</small>
              </button>
            ))}
          </div>
        ) : null}
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            if (saveToBook) await saveAddress(form);
            setCheckoutAddress(form);
            go("payment");
          }}
        >
          <input required placeholder="Label" value={form.label} onChange={(event) => update("label", event.target.value)} />
          <input required placeholder="Full name" value={form.customer_name} onChange={(event) => update("customer_name", event.target.value)} />
          <input required placeholder="Mobile number" value={form.phone} onChange={(event) => update("phone", event.target.value)} />
          <textarea required placeholder="Address" value={form.address_line} onChange={(event) => update("address_line", event.target.value)} />
          <input required placeholder="City" value={form.city} onChange={(event) => update("city", event.target.value)} />
          <input required placeholder="State" value={form.state} onChange={(event) => update("state", event.target.value)} />
          <input required placeholder="Pincode" value={form.pincode} onChange={(event) => update("pincode", event.target.value)} />
          <label className="checkbox-row">
            <input type="checkbox" checked={saveToBook} onChange={(event) => setSaveToBook(event.target.checked)} />
            <span>Save this as an address</span>
          </label>
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
  const [oauthRole, setOauthRole] = useState("buyer");
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  return (
    <main className="auth-page">
      <section className="auth-promo">
        <span className="auth-badge">Flipkart-style storefront</span>
        <h1>Shop smarter with a clean buyer and seller experience.</h1>
        <p>Search fast, compare products, track orders, manage inventory, and move through checkout without friction.</p>
        <ul className="auth-points">
          <li>Responsive storefront with deals, carousel, and category shortcuts</li>
          <li>Buyer, seller, and admin flows in one connected app</li>
          <li>Google OAuth asks which side of the marketplace you belong to</li>
        </ul>
      </section>

      <section className="checkout-form auth-box auth-card">
        <h1>{mode === "login" ? "Login" : "Signup"}</h1>
        <p className="helper-text">
          Demo buyer: <strong>aarav.buyer@example.com</strong> / <strong>password123</strong>
          <br />
          Admin: <strong>admin@flipkart.com</strong> / <strong>admin123</strong>
        </p>
        <form onSubmit={(event) => { event.preventDefault(); mode === "login" ? login(form) : signup(form); }}>
          {mode === "signup" && <input required placeholder="Full name" value={form.name} onChange={(event) => update("name", event.target.value)} />}
          {mode === "signup" && <input required placeholder="Phone" value={form.phone} onChange={(event) => update("phone", event.target.value)} />}
          <input required placeholder="Email" value={form.email} onChange={(event) => update("email", event.target.value)} />
          <input required type="password" placeholder="Password" value={form.password} onChange={(event) => update("password", event.target.value)} />
          <button type="submit">{mode === "login" ? "Login" : "Create Account"}</button>
          <div className="oauth-role-panel">
            <div>
              <strong>Continue with Google</strong>
              <p className="helper-text">Choose whether this Google sign-in should open buyer or seller access.</p>
            </div>
            <div className="role-toggle">
              <button type="button" className={oauthRole === "buyer" ? "active" : ""} onClick={() => setOauthRole("buyer")}>Buyer</button>
              <button type="button" className={oauthRole === "seller" ? "active" : ""} onClick={() => setOauthRole("seller")}>Seller</button>
            </div>
          </div>
          <GoogleSignInButton googleLogin={googleLogin} selectedRole={oauthRole} />
          <button type="button" className="link-button" onClick={() => setMode(mode === "login" ? "signup" : "login")}>
            {mode === "login" ? "Create new account" : "Already have an account"}
          </button>
        </form>
      </section>
    </main>
  );
}

function PaymentPage({ cart, checkoutAddress, paymentMethods, savePaymentMethod, placeOrder, go, setNotice }) {
  const defaultPayment = paymentMethods.find((method) => method.is_default) || null;
  const [method, setMethod] = useState(defaultPayment?.provider || "RAZORPAY");
  const [payerName, setPayerName] = useState(checkoutAddress?.customer_name || "");
  const [upiId, setUpiId] = useState(defaultPayment?.upi_id || "");
  const [cardNumber, setCardNumber] = useState(defaultPayment?.card_last4 || "");
  const [saveMethod, setSaveMethod] = useState(false);
  const [loading, setLoading] = useState(false);
  const [rzpOpen, setRzpOpen] = useState(false);
  const [rzpTab, setRzpTab] = useState("card");
  const [rzpUpi, setRzpUpi] = useState("");
  const [rzpProcessing, setRzpProcessing] = useState(false);
  const total = cart.summary.total;

  const applySavedMethod = (saved) => {
    setMethod(saved.provider);
    setUpiId(saved.upi_id || "");
    setCardNumber(saved.card_last4 || "");
    setSaveMethod(false);
  };

  const handleRazorpayPay = async (event) => {
    event.preventDefault();
    setRzpProcessing(true);
    await new Promise((resolve) => setTimeout(resolve, 1400));
    const fakePayId = `pay_${Math.random().toString(36).slice(2, 14).toUpperCase()}`;
    const fakeOrderId = `order_${Math.random().toString(36).slice(2, 14).toUpperCase()}`;
    setRzpProcessing(false);
    setRzpOpen(false);
    await placeOrder({
      method: "RAZORPAY",
      payer_name: payerName || checkoutAddress?.customer_name,
      payment_reference: fakePayId,
      razorpay_order_id: fakeOrderId,
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (method === "RAZORPAY") {
      setRzpOpen(true);
      return;
    }
    setLoading(true);
    try {
      if (saveMethod && ["UPI", "CARD"].includes(method)) {
        await savePaymentMethod({
          provider: method,
          label: method === "UPI" ? `UPI ${upiId}` : `Card ending ${cardNumber.slice(-4)}`,
          upi_id: method === "UPI" ? upiId : "",
          card_last4: method === "CARD" ? cardNumber.slice(-4) : "",
          is_default: paymentMethods.length === 0,
        });
      }
      const payload = { method, payer_name: payerName };
      if (method === "UPI") payload.upi_id = upiId;
      if (method === "CARD") payload.card_last4 = cardNumber.slice(-4);
      await placeOrder(payload);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {rzpOpen && (
        <div className="modal-backdrop">
          <div className="modal-panel">
            <div className="modal-head">
              <div>
                <strong>Flipkart Clone</strong>
                <span>Secure payment for {money(total)}</span>
              </div>
              <button onClick={() => setRzpOpen(false)}>Close</button>
            </div>
            <div className="modal-tabs">
              {["card", "upi", "netbanking"].map((tab) => (
                <button key={tab} className={rzpTab === tab ? "active" : ""} onClick={() => setRzpTab(tab)}>
                  {tab}
                </button>
              ))}
            </div>
            <div className="modal-body">
              {rzpProcessing ? (
                <div className="empty-state">Processing payment...</div>
              ) : (
                <form onSubmit={handleRazorpayPay}>
                  {rzpTab === "card" && (
                    <div className="stack-gap">
                      <input required placeholder="Card number" style={rzpInput} />
                      <input required placeholder="Name on card" style={rzpInput} />
                      <div className="two-col">
                        <input required placeholder="MM/YY" style={rzpInput} />
                        <input required placeholder="CVV" style={rzpInput} />
                      </div>
                    </div>
                  )}
                  {rzpTab === "upi" && (
                    <input required placeholder="Enter UPI ID" value={rzpUpi} onChange={(event) => setRzpUpi(event.target.value)} style={rzpInput} />
                  )}
                  {rzpTab === "netbanking" && (
                    <select required defaultValue="" style={rzpInput}>
                      <option value="" disabled>Select bank</option>
                      {["SBI", "HDFC", "ICICI", "Axis", "Kotak"].map((bank) => (
                        <option key={bank} value={bank}>{bank}</option>
                      ))}
                    </select>
                  )}
                  <button type="submit" style={rzpPayBtn}>Pay {money(total)}</button>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
      <main className="checkout-page">
        <section className="checkout-form">
          <h1>Payment</h1>
          {paymentMethods.length ? (
            <div className="picker-grid">
              {paymentMethods.map((saved) => (
                <button key={saved.id} type="button" className="picker-card" onClick={() => applySavedMethod(saved)}>
                  <strong>{saved.label}</strong>
                  <span>{saved.provider}</span>
                  <small>{saved.upi_id || (saved.card_last4 ? `xxxx-${saved.card_last4}` : "Saved option")}</small>
                </button>
              ))}
            </div>
          ) : null}
          <form onSubmit={handleSubmit}>
            <select value={method} onChange={(event) => setMethod(event.target.value)}>
              <option value="RAZORPAY">Razorpay</option>
              <option value="UPI">UPI</option>
              <option value="CARD">Debit or Credit Card</option>
              <option value="STRIPE">Stripe</option>
              <option value="PAYPAL">PayPal</option>
              <option value="COD">Cash on Delivery</option>
            </select>
            <input required placeholder="Payer name" value={payerName} onChange={(event) => setPayerName(event.target.value)} />
            {method === "UPI" && <input required placeholder="UPI ID" value={upiId} onChange={(event) => setUpiId(event.target.value)} />}
            {method === "CARD" && <input required maxLength="4" placeholder="Last 4 card digits" value={cardNumber} onChange={(event) => setCardNumber(event.target.value.replace(/\D/g, ""))} />}
            {["UPI", "CARD"].includes(method) && (
              <label className="checkbox-row">
                <input type="checkbox" checked={saveMethod} onChange={(event) => setSaveMethod(event.target.checked)} />
                <span>Save this payment method</span>
              </label>
            )}
            <button type="submit" disabled={loading}>
              {loading ? "Processing..." : method === "COD" ? "Place Order" : `Pay ${money(total)} and Place Order`}
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
          <strong>{item.quantity} x {money(item.product.price)}</strong>
        </div>
      ))}
      <PriceBox summary={cart.summary} />
    </section>
  );
}

function OrdersPage({ orders, buyer, go, reorderOrder, submitComplaint }) {
  const [complaintDrafts, setComplaintDrafts] = useState({});
  const updateDraft = (orderId, key, value) =>
    setComplaintDrafts((current) => ({
      ...current,
      [orderId]: { ...(current[orderId] || { subject: "", message: "", open: false }), [key]: value },
    }));

  return (
    <main className="dashboard-page">
      <UserPanel user={buyer} />
      <section className="dashboard-card">
        <h1>Past Orders</h1>
        {orders.length ? (
          orders.map((order) => {
            const draft = complaintDrafts[order.id] || { subject: "", message: "", open: false };
            return (
              <article className="order-card" key={order.id}>
                <div className="order-card-head">
                  <div>
                    <h2>{order.order_number}</h2>
                    <p>{order.payment_method} | {order.payment_status} | {order.created_at?.slice?.(0, 10)}</p>
                  </div>
                  <strong>{money(order.total_amount)}</strong>
                </div>
                <TrackingTimeline status={order.status} />
                <div className="inline-metadata">
                  <StatusBadge value={order.status} />
                  <StatusBadge value={order.tracking_status} />
                  {order.refund_status !== "NONE" && <StatusBadge value={order.refund_status} />}
                </div>
                <div className="order-items detail-list">
                  {order.items.map((item) => (
                    <div key={item.id}>
                      <span>{item.quantity} x {item.title}</span>
                      <strong>{item.status}</strong>
                    </div>
                  ))}
                </div>
                <div className="button-row">
                  <button onClick={() => reorderOrder(order.order_number)}>Reorder</button>
                  <button className="secondary" onClick={() => updateDraft(order.id, "open", !draft.open)}>
                    {draft.open ? "Hide Issue Form" : "Report Issue"}
                  </button>
                </div>
                {draft.open && (
                  <form
                    className="inline-form"
                    onSubmit={(event) => {
                      event.preventDefault();
                      submitComplaint({ order_id: order.id, subject: draft.subject, message: draft.message });
                      setComplaintDrafts((current) => ({ ...current, [order.id]: { subject: "", message: "", open: false } }));
                    }}
                  >
                    <input required placeholder="Issue title" value={draft.subject} onChange={(event) => updateDraft(order.id, "subject", event.target.value)} />
                    <textarea required placeholder="Tell us what happened" value={draft.message} onChange={(event) => updateDraft(order.id, "message", event.target.value)} />
                    <button type="submit">Submit Issue</button>
                  </form>
                )}
              </article>
            );
          })
        ) : (
          <div className="empty-state">No orders yet.</div>
        )}
        <button className="wide-action" onClick={() => go("home")}>Continue Shopping</button>
      </section>
    </main>
  );
}

function AccountPage({
  user,
  updateProfile,
  addresses,
  saveAddress,
  updateAddress,
  deleteAddress,
  paymentMethods,
  savePaymentMethod,
  deletePaymentMethod,
  recentlyViewed,
  recommendations,
  complaints,
  submitComplaint,
  openProduct,
  wishlistIds,
  toggleWishlist,
}) {
  const [profile, setProfile] = useState({
    name: user?.name || "",
    phone: user?.phone || "",
    address_line: user?.address_line || "",
    city: user?.city || "",
    state: user?.state || "",
    pincode: user?.pincode || "",
    store_name: user?.store_name || "",
  });
  const [addressForm, setAddressForm] = useState({
    label: "Home",
    customer_name: user?.name || "",
    phone: user?.phone || "",
    address_line: "",
    city: "",
    state: "",
    pincode: "",
  });
  const [paymentForm, setPaymentForm] = useState({ provider: "UPI", label: "", upi_id: "", card_last4: "" });
  const [complaintForm, setComplaintForm] = useState({ subject: "", message: "" });

  useEffect(() => {
    setProfile({
      name: user?.name || "",
      phone: user?.phone || "",
      address_line: user?.address_line || "",
      city: user?.city || "",
      state: user?.state || "",
      pincode: user?.pincode || "",
      store_name: user?.store_name || "",
    });
  }, [user]);

  return (
    <main className="dashboard-page">
      <UserPanel user={user} />
      <section className="account-grid">
        <section className="dashboard-card">
          <h1>Profile</h1>
          <form className="inline-form" onSubmit={(event) => { event.preventDefault(); updateProfile(profile); }}>
            <input value={profile.name} onChange={(event) => setProfile((current) => ({ ...current, name: event.target.value }))} placeholder="Full name" />
            <input value={profile.phone} onChange={(event) => setProfile((current) => ({ ...current, phone: event.target.value }))} placeholder="Phone" />
            <textarea value={profile.address_line} onChange={(event) => setProfile((current) => ({ ...current, address_line: event.target.value }))} placeholder="Primary address" />
            <div className="two-col">
              <input value={profile.city} onChange={(event) => setProfile((current) => ({ ...current, city: event.target.value }))} placeholder="City" />
              <input value={profile.state} onChange={(event) => setProfile((current) => ({ ...current, state: event.target.value }))} placeholder="State" />
            </div>
            <input value={profile.pincode} onChange={(event) => setProfile((current) => ({ ...current, pincode: event.target.value }))} placeholder="Pincode" />
            {user?.role === "seller" && <input value={profile.store_name} onChange={(event) => setProfile((current) => ({ ...current, store_name: event.target.value }))} placeholder="Store name" />}
            <button type="submit">Save Profile</button>
          </form>
        </section>
        <section className="dashboard-card">
          <div className="section-head">
            <h1>Multiple Addresses</h1>
            <span>{addresses.length} saved</span>
          </div>
          <div className="stack-gap">
            {addresses.map((address) => (
              <div className="detail-list-card" key={address.id}>
                <div>
                  <strong>{address.label}</strong>
                  <p>{address.customer_name}, {address.phone}</p>
                  <p>{address.address_line}, {address.city}, {address.state} - {address.pincode}</p>
                </div>
                <div className="button-row">
                  <button className="secondary" onClick={() => updateAddress(address.id, { is_default: true })}>Set Default</button>
                  <button className="secondary" onClick={() => deleteAddress(address.id)}>Delete</button>
                </div>
              </div>
            ))}
          </div>
          <form
            className="inline-form"
            onSubmit={(event) => {
              event.preventDefault();
              saveAddress(addressForm);
              setAddressForm({ label: "Home", customer_name: user?.name || "", phone: user?.phone || "", address_line: "", city: "", state: "", pincode: "" });
            }}
          >
            <input value={addressForm.label} onChange={(event) => setAddressForm((current) => ({ ...current, label: event.target.value }))} placeholder="Label" />
            <input value={addressForm.customer_name} onChange={(event) => setAddressForm((current) => ({ ...current, customer_name: event.target.value }))} placeholder="Customer name" />
            <input value={addressForm.phone} onChange={(event) => setAddressForm((current) => ({ ...current, phone: event.target.value }))} placeholder="Phone" />
            <textarea value={addressForm.address_line} onChange={(event) => setAddressForm((current) => ({ ...current, address_line: event.target.value }))} placeholder="Address" />
            <div className="two-col">
              <input value={addressForm.city} onChange={(event) => setAddressForm((current) => ({ ...current, city: event.target.value }))} placeholder="City" />
              <input value={addressForm.state} onChange={(event) => setAddressForm((current) => ({ ...current, state: event.target.value }))} placeholder="State" />
            </div>
            <input value={addressForm.pincode} onChange={(event) => setAddressForm((current) => ({ ...current, pincode: event.target.value }))} placeholder="Pincode" />
            <button type="submit">Add Address</button>
          </form>
        </section>
        <section className="dashboard-card">
          <div className="section-head">
            <h1>Saved Payment Methods</h1>
            <span>{paymentMethods.length} saved</span>
          </div>
          <div className="stack-gap">
            {paymentMethods.map((method) => (
              <div className="detail-list-card" key={method.id}>
                <div>
                  <strong>{method.label}</strong>
                  <p>{method.provider}</p>
                  <p>{method.upi_id || (method.card_last4 ? `xxxx-${method.card_last4}` : "Saved option")}</p>
                </div>
                <div className="button-row">
                  <button className="secondary" onClick={() => deletePaymentMethod(method.id)}>Delete</button>
                </div>
              </div>
            ))}
          </div>
          <form
            className="inline-form"
            onSubmit={(event) => {
              event.preventDefault();
              savePaymentMethod(paymentForm);
              setPaymentForm({ provider: "UPI", label: "", upi_id: "", card_last4: "" });
            }}
          >
            <select value={paymentForm.provider} onChange={(event) => setPaymentForm((current) => ({ ...current, provider: event.target.value }))}>
              <option value="UPI">UPI</option>
              <option value="CARD">Card</option>
            </select>
            <input value={paymentForm.label} onChange={(event) => setPaymentForm((current) => ({ ...current, label: event.target.value }))} placeholder="Label" />
            {paymentForm.provider === "UPI" ? (
              <input value={paymentForm.upi_id} onChange={(event) => setPaymentForm((current) => ({ ...current, upi_id: event.target.value }))} placeholder="UPI ID" />
            ) : (
              <input value={paymentForm.card_last4} onChange={(event) => setPaymentForm((current) => ({ ...current, card_last4: event.target.value.replace(/\D/g, "") }))} placeholder="Last 4 digits" maxLength="4" />
            )}
            <button type="submit">Save Payment Method</button>
          </form>
        </section>
      </section>
      <div className="stack-gap">
        <ProductRail title="Recently Viewed" items={recentlyViewed} openProduct={openProduct} wishlistIds={wishlistIds} toggleWishlist={toggleWishlist} />
        <ProductRail title="Recommended For You" items={recommendations} openProduct={openProduct} wishlistIds={wishlistIds} toggleWishlist={toggleWishlist} />
        <section className="dashboard-card">
          <div className="section-head">
            <h1>Complaints and Support</h1>
            <span>{complaints.length} total</span>
          </div>
          <form
            className="inline-form"
            onSubmit={(event) => {
              event.preventDefault();
              submitComplaint(complaintForm);
              setComplaintForm({ subject: "", message: "" });
            }}
          >
            <input value={complaintForm.subject} onChange={(event) => setComplaintForm((current) => ({ ...current, subject: event.target.value }))} placeholder="Issue title" />
            <textarea value={complaintForm.message} onChange={(event) => setComplaintForm((current) => ({ ...current, message: event.target.value }))} placeholder="Tell us what happened" />
            <button type="submit">Submit Complaint</button>
          </form>
          <div className="stack-gap">
            {complaints.map((complaint) => (
              <div className="detail-list-card" key={complaint.id}>
                <div>
                  <strong>{complaint.subject}</strong>
                  <p>{complaint.message}</p>
                </div>
                <div className="stack-mini">
                  <StatusBadge value={complaint.status} />
                  {complaint.resolution_note ? <small>{complaint.resolution_note}</small> : null}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

const th = { padding: "8px 12px", textAlign: "left", fontWeight: 700, color: "#555" };
const td = { padding: "8px 12px" };

function SellerPage({ dashboard, categories, saveSellerProduct, deleteSellerProduct, updateSellerOrderItemStatus, respondToReview }) {
  const [tab, setTab] = useState("inventory");
  const [editingProduct, setEditingProduct] = useState(null);
  const [saving, setSaving] = useState(false);
  const [productForm, setProductForm] = useState({
    category_slug: categories[0]?.slug || "mobiles",
    title: "",
    brand: "",
    description: "",
    price: "",
    mrp: "",
    stock: "",
    low_stock_threshold: 5,
    assured: true,
    images: [],
    specsText: "",
  });
  const [reviewResponses, setReviewResponses] = useState({});

  useEffect(() => {
    if (!editingProduct) {
      setProductForm({
        category_slug: categories[0]?.slug || "mobiles",
        title: "",
        brand: "",
        description: "",
        price: "",
        mrp: "",
        stock: "",
        low_stock_threshold: 5,
        assured: true,
        images: [],
        specsText: "",
      });
      return;
    }
    setProductForm({
      category_slug: editingProduct.category.slug,
      title: editingProduct.title,
      brand: editingProduct.brand,
      description: editingProduct.description,
      price: editingProduct.price,
      mrp: editingProduct.mrp,
      stock: editingProduct.stock,
      low_stock_threshold: editingProduct.low_stock_threshold || 5,
      assured: editingProduct.assured,
      images: editingProduct.images.map((image) => image.url),
      specsText: editingProduct.specs.map((spec) => `${spec.name}: ${spec.value}`).join("\n"),
    });
  }, [categories, editingProduct]);

  if (!dashboard) return <main className="dashboard-page"><div className="empty-state">Loading seller dashboard...</div></main>;

  const submitProduct = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      const specs = productForm.specsText
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => {
          const [name, ...rest] = line.split(":");
          return { name: name.trim(), value: rest.join(":").trim() };
        })
        .filter((spec) => spec.name && spec.value);
      const payload = {
        category_slug: productForm.category_slug,
        title: productForm.title,
        brand: productForm.brand,
        description: productForm.description,
        price: Number(productForm.price),
        mrp: Number(productForm.mrp),
        stock: Number(productForm.stock),
        low_stock_threshold: Number(productForm.low_stock_threshold),
        assured: productForm.assured,
        images: productForm.images,
        specs,
      };
      await saveSellerProduct(editingProduct?.id, payload);
      setEditingProduct(null);
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="dashboard-page">
      <UserPanel user={dashboard.seller} />
      <section className="seller-stats">
        <div><span>Products</span><strong>{dashboard.stats.product_count}</strong></div>
        <div><span>Units Sold</span><strong>{dashboard.stats.units_sold}</strong></div>
        <div><span>Revenue</span><strong>{money(dashboard.stats.revenue)}</strong></div>
        <div><span>Orders</span><strong>{dashboard.stats.order_count}</strong></div>
        <div><span>Low Stock</span><strong>{dashboard.stats.low_stock_count}</strong></div>
        <div><span>Pending Review</span><strong>{dashboard.stats.pending_products}</strong></div>
      </section>
      <div className="tab-row">
        {["inventory", "products", "orders", "reviews"].map((tabName) => (
          <button key={tabName} className={tab === tabName ? "active" : ""} onClick={() => setTab(tabName)}>{tabName}</button>
        ))}
      </div>
      {tab === "inventory" && (
        <section className="dashboard-card">
          <div className="section-head">
            <h1>Inventory Management</h1>
            <span>Low stock and listing visibility</span>
          </div>
          <div className="seller-table">
            {dashboard.products.map((product) => (
              <div key={product.id}>
                <span>{product.title}</span>
                <strong>{product.stock > 0 ? `${product.stock} left` : "Out of stock"}</strong>
                <em>{money(product.price)}</em>
                <small>{product.stock <= product.low_stock_threshold ? "Low stock alert" : product.listing_status}</small>
              </div>
            ))}
          </div>
          <div className="stack-gap">
            <h2>Top-selling products</h2>
            {dashboard.top_products.length ? (
              dashboard.top_products.map((item) => (
                <div className="detail-list-card" key={item.product_id}>
                  <strong>{item.title}</strong>
                  <span>{item.units_sold} units sold</span>
                  <strong>{money(item.revenue)}</strong>
                </div>
              ))
            ) : (
              <div className="empty-state">Top sellers will show up after your first few orders.</div>
            )}
          </div>
        </section>
      )}
      {tab === "products" && (
        <div className="account-grid">
          <section className="dashboard-card">
            <div className="section-head">
              <h1>{editingProduct ? "Edit Product" : "Add Product"}</h1>
              <span>{editingProduct ? "Update and resubmit" : "New listings start pending"}</span>
            </div>
            <form className="inline-form" onSubmit={submitProduct}>
              <select value={productForm.category_slug} onChange={(event) => setProductForm((current) => ({ ...current, category_slug: event.target.value }))}>
                {categories.map((category) => (
                  <option key={category.id} value={category.slug}>{category.name}</option>
                ))}
              </select>
              <input value={productForm.title} onChange={(event) => setProductForm((current) => ({ ...current, title: event.target.value }))} placeholder="Product title" />
              <input value={productForm.brand} onChange={(event) => setProductForm((current) => ({ ...current, brand: event.target.value }))} placeholder="Brand" />
              <textarea value={productForm.description} onChange={(event) => setProductForm((current) => ({ ...current, description: event.target.value }))} placeholder="Description" />
              <div className="two-col">
                <input value={productForm.price} onChange={(event) => setProductForm((current) => ({ ...current, price: event.target.value }))} placeholder="Price" />
                <input value={productForm.mrp} onChange={(event) => setProductForm((current) => ({ ...current, mrp: event.target.value }))} placeholder="MRP" />
              </div>
              <div className="two-col">
                <input value={productForm.stock} onChange={(event) => setProductForm((current) => ({ ...current, stock: event.target.value }))} placeholder="Stock" />
                <input value={productForm.low_stock_threshold} onChange={(event) => setProductForm((current) => ({ ...current, low_stock_threshold: event.target.value }))} placeholder="Low stock threshold" />
              </div>
              <textarea value={productForm.specsText} onChange={(event) => setProductForm((current) => ({ ...current, specsText: event.target.value }))} placeholder="Specs, one per line. Example: RAM: 8 GB" />
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={async (event) => {
                  const files = Array.from(event.target.files || []);
                  if (!files.length) return;
                  const images = await readFilesAsDataUrls(files);
                  setProductForm((current) => ({ ...current, images }));
                }}
              />
              <label className="checkbox-row">
                <input type="checkbox" checked={productForm.assured} onChange={(event) => setProductForm((current) => ({ ...current, assured: event.target.checked }))} />
                <span>Flipkart assured</span>
              </label>
              <button type="submit" disabled={saving}>{saving ? "Saving..." : editingProduct ? "Update Product" : "Add Product"}</button>
              {editingProduct && <button type="button" className="secondary" onClick={() => setEditingProduct(null)}>Cancel Edit</button>}
            </form>
          </section>
          <section className="dashboard-card">
            <div className="section-head">
              <h1>Product Management</h1>
              <span>{dashboard.products.length} products</span>
            </div>
            <div className="stack-gap">
              {dashboard.products.map((product) => (
                <div className="detail-list-card" key={product.id}>
                  <div>
                    <strong>{product.title}</strong>
                    <p>{money(product.price)} | Stock {product.stock} | {percentageOff(product)}% off</p>
                    <div className="inline-metadata">
                      <StatusBadge value={product.listing_status} />
                      {product.stock <= product.low_stock_threshold && <StatusBadge value="LOW_STOCK" />}
                    </div>
                  </div>
                  <div className="button-row">
                    <button className="secondary" onClick={() => setEditingProduct(product)}>Edit</button>
                    <button className="secondary" onClick={() => deleteSellerProduct(product.id)}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
      {tab === "orders" && (
        <section className="dashboard-card">
          <h1>Order Management</h1>
          {dashboard.orders.length ? (
            dashboard.orders.map((order) => (
              <article className="order-card" key={order.id}>
                <div className="order-card-head">
                  <div>
                    <h2>{order.order_number}</h2>
                    <p>{order.customer_name}, {order.city}</p>
                  </div>
                  <strong>{money(order.total_amount)}</strong>
                </div>
                <div className="inline-metadata">
                  <StatusBadge value={order.payment_status} />
                  <StatusBadge value={order.status} />
                </div>
                {order.items.map((item) => (
                  <div className="detail-list-card" key={item.id}>
                    <div>
                      <strong>{item.title}</strong>
                      <p>{item.quantity} x {money(item.price)}</p>
                    </div>
                    <select value={item.status} onChange={(event) => updateSellerOrderItemStatus(order.id, item.id, event.target.value)}>
                      {orderSteps.map((step) => (
                        <option key={step} value={step}>{step}</option>
                      ))}
                    </select>
                  </div>
                ))}
              </article>
            ))
          ) : (
            <div className="empty-state">No seller orders yet.</div>
          )}
        </section>
      )}
      {tab === "reviews" && (
        <section className="dashboard-card">
          <h1>Customer Reviews</h1>
          {dashboard.reviews.length ? (
            dashboard.reviews.map((review) => (
              <article className="review-card" key={review.id}>
                <strong>{review.user.name} rated {review.rating} star</strong>
                <p>{review.comment}</p>
                <textarea value={reviewResponses[review.id] ?? review.seller_response ?? ""} onChange={(event) => setReviewResponses((current) => ({ ...current, [review.id]: event.target.value }))} placeholder="Reply to this review" />
                <button onClick={() => respondToReview(review.id, reviewResponses[review.id] ?? review.seller_response ?? "")}>Save Response</button>
              </article>
            ))
          ) : (
            <div className="empty-state">No reviews yet.</div>
          )}
        </section>
      )}
    </main>
  );
}

function AdminPage({ setNotice }) {
  const [data, setData] = useState(null);
  const [tab, setTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const load = useCallback(() => {
    setLoading(true);
    api.adminDashboard().then(setData).catch((error) => setNotice(error.message)).finally(() => setLoading(false));
  }, [setNotice]);
  useEffect(() => {
    load();
  }, [load]);
  if (loading) return <main className="dashboard-page"><div className="empty-state">Loading admin data...</div></main>;
  if (!data) return null;
  const { stats, growth, users, products, orders, transactions, complaints, fraud_flags: fraudFlags } = data;
  const updateUser = async (userId, payload, successMessage) => {
    await api.adminUpdateUser(userId, payload);
    setNotice(successMessage);
    load();
  };
  const moderateProduct = async (productId, listing_status, approval_note) => {
    await api.adminModerateProduct(productId, { listing_status, approval_note });
    setNotice("Product status updated");
    load();
  };
  const updateTransaction = async (transactionId, refund_status) => {
    await api.adminUpdateTransaction(transactionId, { refund_status });
    setNotice("Transaction updated");
    load();
  };
  const updateComplaint = async (complaintId, status) => {
    await api.adminUpdateComplaint(complaintId, { status, resolution_note: status === "RESOLVED" ? "Closed by admin" : "" });
    setNotice("Complaint updated");
    load();
  };
  const deleteUser = async (userId) => {
    if (!window.confirm("Delete this user?")) return;
    await api.adminDeleteUser(userId);
    setNotice("User deleted");
    load();
  };
  const deleteProduct = async (productId) => {
    if (!window.confirm("Delete this product?")) return;
    await api.adminDeleteProduct(productId);
    setNotice("Product deleted");
    load();
  };
  return (
    <main className="dashboard-page">
      <section className="admin-hero">
        <h1>Admin Dashboard</h1>
        <p>Platform monitoring, moderation, payments, and marketplace controls.</p>
      </section>
      <section className="seller-stats admin-stats-grid">
        <div><span>Total Users</span><strong>{stats.total_users}</strong></div>
        <div><span>Active Users</span><strong>{stats.active_users}</strong></div>
        <div><span>Total Products</span><strong>{stats.total_products}</strong></div>
        <div><span>Total Orders</span><strong>{stats.total_orders}</strong></div>
        <div><span>Revenue</span><strong>{money(stats.total_revenue)}</strong></div>
        <div><span>Pending Sellers</span><strong>{stats.pending_sellers}</strong></div>
        <div><span>Pending Products</span><strong>{stats.pending_products}</strong></div>
        <div><span>Refunded</span><strong>{stats.refunded_transactions}</strong></div>
      </section>
      <section className="dashboard-card">
        <div className="section-head">
          <h2>Growth Stats</h2>
          <span>Last 7 days</span>
        </div>
        <div className="seller-stats admin-stats-grid">
          <div><span>Users</span><strong>{growth.users_last_7_days}</strong><small>{growth.users_growth_percent}%</small></div>
          <div><span>Orders</span><strong>{growth.orders_last_7_days}</strong><small>{growth.orders_growth_percent}%</small></div>
          <div><span>Revenue</span><strong>{money(growth.revenue_last_7_days)}</strong><small>{growth.revenue_growth_percent}%</small></div>
        </div>
      </section>
      <div className="tab-row">
        {["overview", "users", "sellers", "products", "orders", "payments", "reports"].map((tabName) => (
          <button key={tabName} className={tab === tabName ? "active" : ""} onClick={() => setTab(tabName)}>{tabName}</button>
        ))}
      </div>
      {tab === "overview" && (
        <section className="dashboard-card">
          <ul className="summary-list">
            <li>{stats.total_users} registered users across buyer and seller roles.</li>
            <li>{stats.pending_sellers} sellers waiting for approval and {stats.pending_products} products waiting to go live.</li>
            <li>{transactions.length} transactions tracked, with {stats.refunded_transactions} refunds already processed.</li>
            <li>{complaints.length} complaints and {fraudFlags.length} fraud flags currently on the radar.</li>
          </ul>
        </section>
      )}
      {tab === "users" && (
        <section className="dashboard-card">
          <h1>User Management</h1>
          <table className="admin-table">
            <thead><tr><th style={th}>Name</th><th style={th}>Email</th><th style={th}>Role</th><th style={th}>Status</th><th style={th}>Action</th></tr></thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td style={td}>{user.name}</td>
                  <td style={td}>{user.email}</td>
                  <td style={td}>{user.role}</td>
                  <td style={td}><StatusBadge value={user.is_active ? "ACTIVE" : "BANNED"} /></td>
                  <td style={td}>
                    <div className="button-row">
                      <button className="secondary" onClick={() => updateUser(user.id, { is_active: !user.is_active }, user.is_active ? "User banned" : "User activated")}>{user.is_active ? "Ban" : "Activate"}</button>
                      {user.role !== "admin" && <button className="secondary" onClick={() => updateUser(user.id, { role: user.role === "buyer" ? "seller" : "buyer" }, "Role updated")}>Make {user.role === "buyer" ? "Seller" : "Buyer"}</button>}
                      <button className="secondary" onClick={() => deleteUser(user.id)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      {tab === "sellers" && (
        <section className="dashboard-card">
          <h1>Seller Control</h1>
          {users.filter((user) => user.role === "seller").map((seller) => (
            <div className="detail-list-card" key={seller.id}>
              <div>
                <strong>{seller.store_name || seller.name}</strong>
                <p>{seller.email}</p>
                <div className="inline-metadata">
                  <StatusBadge value={seller.seller_status} />
                  <StatusBadge value={seller.is_active ? "ACTIVE" : "BANNED"} />
                </div>
              </div>
              <div className="button-row">
                <button className="secondary" onClick={() => updateUser(seller.id, { seller_status: "APPROVED" }, "Seller approved")}>Approve</button>
                <button className="secondary" onClick={() => updateUser(seller.id, { seller_status: "REJECTED" }, "Seller rejected")}>Reject</button>
                <button className="secondary" onClick={() => updateUser(seller.id, { seller_status: "SUSPENDED" }, "Seller suspended")}>Suspend</button>
              </div>
            </div>
          ))}
        </section>
      )}
      {tab === "products" && (
        <section className="dashboard-card">
          <h1>Product Control</h1>
          {products.map((product) => (
            <div className="detail-list-card" key={product.id}>
              <div>
                <strong>{product.title}</strong>
                <p>{product.brand} | {money(product.price)} | Stock {product.stock}</p>
                <div className="inline-metadata">
                  <StatusBadge value={product.listing_status} />
                  {product.approval_note ? <small>{product.approval_note}</small> : null}
                </div>
              </div>
              <div className="button-row">
                <button className="secondary" onClick={() => moderateProduct(product.id, "APPROVED", "Approved for listing")}>Approve</button>
                <button className="secondary" onClick={() => moderateProduct(product.id, "REJECTED", "Rejected by admin")}>Reject</button>
                <button className="secondary" onClick={() => deleteProduct(product.id)}>Remove</button>
              </div>
            </div>
          ))}
        </section>
      )}
      {tab === "orders" && (
        <section className="dashboard-card">
          <h1>Platform Orders</h1>
          {orders.map((order) => (
            <article className="order-card" key={order.id}>
              <div className="order-card-head">
                <div>
                  <h2>{order.order_number}</h2>
                  <p>{order.customer_name} | {order.city}</p>
                </div>
                <strong>{money(order.total_amount)}</strong>
              </div>
              <div className="inline-metadata">
                <StatusBadge value={order.status} />
                <StatusBadge value={order.payment_status} />
                {order.refund_status !== "NONE" && <StatusBadge value={order.refund_status} />}
              </div>
            </article>
          ))}
        </section>
      )}
      {tab === "payments" && (
        <section className="dashboard-card">
          <h1>Payment Monitoring</h1>
          {transactions.map((transaction) => (
            <div className="detail-list-card" key={transaction.id}>
              <div>
                <strong>{transaction.provider}</strong>
                <p>Order {transaction.order_id} | {money(transaction.amount)}</p>
                <div className="inline-metadata">
                  <StatusBadge value={transaction.status} />
                  <StatusBadge value={transaction.refund_status} />
                </div>
              </div>
              <div className="button-row">
                <button className="secondary" onClick={() => updateTransaction(transaction.id, "REQUESTED")}>Mark Refund Requested</button>
                <button className="secondary" onClick={() => updateTransaction(transaction.id, "REFUNDED")}>Refund</button>
              </div>
            </div>
          ))}
        </section>
      )}
      {tab === "reports" && (
        <div className="account-grid">
          <section className="dashboard-card">
            <h1>Complaints</h1>
            {complaints.map((complaint) => (
              <div className="detail-list-card" key={complaint.id}>
                <div>
                  <strong>{complaint.subject}</strong>
                  <p>{complaint.message}</p>
                  <small>{complaint.user.name}</small>
                </div>
                <div className="button-row">
                  <StatusBadge value={complaint.status} />
                  <button className="secondary" onClick={() => updateComplaint(complaint.id, "IN_REVIEW")}>Review</button>
                  <button className="secondary" onClick={() => updateComplaint(complaint.id, "RESOLVED")}>Resolve</button>
                </div>
              </div>
            ))}
          </section>
          <section className="dashboard-card">
            <h1>Fraud Detection</h1>
            {fraudFlags.map((flag) => (
              <div className="detail-list-card" key={flag.id}>
                <div>
                  <strong>Order {flag.order_id}</strong>
                  <p>{flag.reason}</p>
                </div>
                <div className="inline-metadata">
                  <StatusBadge value={flag.severity} />
                  <StatusBadge value={flag.status} />
                </div>
              </div>
            ))}
          </section>
        </div>
      )}
    </main>
  );
}

function AIChatWidget({ open, setOpen, messages, sendMessage, clearHistory, loading }) {
  const [draft, setDraft] = useState("");
  const starters = ["Suggest a phone under 25000", "Compare Motorola and Sony", "How do payments work here?", "Show me my recent orders"];
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
              <span>Shopping help with saved chat history</span>
            </div>
            <div className="ai-chat-header-actions">
              <button onClick={clearHistory}>Clear</button>
              <button onClick={() => setOpen(false)}>Close</button>
            </div>
          </div>
          <div className="ai-chat-body">
            {messages.map((message, index) => (
              <article key={`${message.role}-${index}`} className={message.role === "assistant" ? "ai-msg assistant" : "ai-msg user"}>
                <span>{message.role === "assistant" ? "AI" : "You"}</span>
                <p>{message.content}</p>
              </article>
            ))}
            {showStarters && <div className="ai-starters">{starters.map((starter) => <button key={starter} onClick={() => sendMessage(starter)}>{starter}</button>)}</div>}
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
        <span className="success-mark">OK</span>
        <h1>Order placed successfully!</h1>
        <p>Your order ID is <strong>{order?.order_number}</strong>.</p>
        <p>Payment: <strong>{order?.payment_method}</strong> | <strong>{order?.payment_status}</strong></p>
        <p className="helper-text">A confirmation email has been sent to your registered email address.</p>
        <button onClick={() => go("orders")}>View Order Summary</button>
      </div>
    </main>
  );
}

export default function App() {
  const [page, setPage] = useState("home");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({ category: "all", max_price: "", min_rating: "" });
  const [categories, setCategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [productReviews, setProductReviews] = useState([]);
  const [wishlist, setWishlist] = useState([]);
  const [cart, setCart] = useState(emptyCart);
  const [authUser, setAuthUser] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const [orders, setOrders] = useState([]);
  const [sellerDashboard, setSellerDashboard] = useState(null);
  const [addresses, setAddresses] = useState([]);
  const [paymentMethods, setPaymentMethods] = useState([]);
  const [recentlyViewed, setRecentlyViewed] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [complaints, setComplaints] = useState([]);
  const [checkoutAddress, setCheckoutAddress] = useState(null);
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState(defaultChatMessages);

  const currentUser = authUser;
  const cartCount = useMemo(() => cart.items.reduce((total, item) => total + item.quantity, 0), [cart.items]);

  const resetProtectedState = useCallback(() => {
    setCart(emptyCart);
    setWishlist([]);
    setOrders([]);
    setSellerDashboard(null);
    setAddresses([]);
    setPaymentMethods([]);
    setRecentlyViewed([]);
    setRecommendations([]);
    setComplaints([]);
    setCheckoutAddress(null);
    setOrder(null);
    setChatMessages(defaultChatMessages);
  }, []);

  const ensureCustomerAccess = useCallback((message = "Please login to continue") => {
    if (!currentUser) {
      setNotice(message);
      setPage("auth");
      return false;
    }
    if (currentUser.role === "admin") {
      setNotice("Admins cannot use buyer actions");
      return false;
    }
    return true;
  }, [currentUser]);

  const refreshProfile = useCallback(async () => {
    if (!api.hasToken()) return;
    const user = await api.me();
    setAuthUser(user);
  }, []);

  const refreshOrders = useCallback(() => {
    if (!currentUser || currentUser.role !== "buyer") {
      setOrders([]);
      return Promise.resolve();
    }
    return api.orders().then(setOrders).catch((error) => setNotice(error.message));
  }, [currentUser]);

  const refreshSeller = useCallback(() => {
    if (!currentUser || currentUser.role !== "seller") {
      setSellerDashboard(null);
      return Promise.resolve();
    }
    return api.sellerDashboard(currentUser.id).then(setSellerDashboard).catch((error) => setNotice(error.message));
  }, [currentUser]);

  const refreshAccountData = useCallback(async () => {
    if (!currentUser || currentUser.role === "admin") {
      resetProtectedState();
      return;
    }
    const results = await Promise.allSettled([
      api.cart(),
      api.wishlist(),
      api.addresses(),
      api.paymentMethods(),
      api.recentlyViewed(),
      api.recommendations(),
      api.complaints(),
      api.aiHistory(),
    ]);
    if (results[0].status === "fulfilled") setCart(results[0].value); else setCart(emptyCart);
    if (results[1].status === "fulfilled") setWishlist(results[1].value.items); else setWishlist([]);
    if (results[2].status === "fulfilled") setAddresses(results[2].value.items); else setAddresses([]);
    if (results[3].status === "fulfilled") setPaymentMethods(results[3].value.items); else setPaymentMethods([]);
    if (results[4].status === "fulfilled") setRecentlyViewed(results[4].value.items); else setRecentlyViewed([]);
    if (results[5].status === "fulfilled") setRecommendations(results[5].value.items); else setRecommendations([]);
    if (results[6].status === "fulfilled") setComplaints(results[6].value.items); else setComplaints([]);
    if (results[7].status === "fulfilled" && results[7].value.items?.length) {
      setChatMessages(results[7].value.items.map((item) => ({ role: item.role, content: item.content })));
    } else {
      setChatMessages(defaultChatMessages);
    }
  }, [currentUser, resetProtectedState]);

  useEffect(() => {
    api.categories().then(setCategories).catch((error) => setNotice(error.message));
    api.hydrateToken();
    if (!api.hasToken()) {
      setAuthReady(true);
      return;
    }
    api.me()
      .then((user) => {
        setAuthUser(user);
        setPage(user.role === "admin" ? "admin" : user.role === "seller" ? "seller" : "home");
      })
      .catch(() => {
        api.clearToken();
        setAuthUser(null);
      })
      .finally(() => setAuthReady(true));
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const handleAuthExpired = (event) => {
      setAuthUser(null);
      resetProtectedState();
      setChatOpen(false);
      setPage((current) => (["cart", "checkout", "payment", "orders", "account", "seller", "admin", "confirmation"].includes(current) ? "auth" : current));
      setNotice(event.detail?.message || "Session expired. Please login again.");
      setAuthReady(true);
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
  }, [resetProtectedState]);

  useEffect(() => {
    if (!authReady) return;
    if (!currentUser) {
      resetProtectedState();
      return;
    }
    refreshAccountData();
    if (currentUser.role === "seller") refreshSeller();
    if (currentUser.role === "buyer") refreshOrders();
  }, [authReady, currentUser, refreshAccountData, refreshOrders, refreshSeller, resetProtectedState]);

  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => {
      api.products({ search: query, category: filters.category, max_price: filters.max_price, min_rating: filters.min_rating })
        .then(setProducts)
        .catch((error) => setNotice(error.message))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(timer);
  }, [query, filters]);

  const go = useCallback((nextPage) => {
    if (nextPage === "payment" && !checkoutAddress) {
      setNotice("Please add a delivery address first");
      setPage("checkout");
      return;
    }
    if (["account", "cart", "checkout", "payment", "orders"].includes(nextPage) && !ensureCustomerAccess()) return;
    if (nextPage === "seller") {
      if (!currentUser) {
        setNotice("Please login as a seller");
        setPage("auth");
        return;
      }
      if (currentUser.role !== "seller") {
        setNotice("Seller access required");
        return;
      }
      refreshSeller();
    }
    if (nextPage === "admin") {
      if (!currentUser) {
        setNotice("Please login as admin");
        setPage("auth");
        return;
      }
      if (currentUser.role !== "admin") {
        setNotice("Admin access required");
        return;
      }
    }
    if (nextPage === "orders") refreshOrders();
    if (nextPage === "account") refreshAccountData();
    setPage(nextPage);
  }, [checkoutAddress, currentUser, ensureCustomerAccess, refreshAccountData, refreshOrders, refreshSeller]);

  const openProduct = async (id) => {
    try {
      const product = await api.product(id);
      setSelectedProduct(product);
      setProductReviews(await api.reviews(id));
      if (currentUser && currentUser.role !== "admin") {
        const viewed = await api.recentlyViewed().catch(() => null);
        if (viewed) setRecentlyViewed(viewed.items);
        const recs = await api.recommendations().catch(() => null);
        if (recs) setRecommendations(recs.items);
      }
      setPage("detail");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const addToCart = async (productId) => {
    if (!ensureCustomerAccess()) return;
    try {
      setCart(await api.addToCart(productId));
      setNotice("Added to cart");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const buyNow = async (productId) => {
    if (!ensureCustomerAccess()) return;
    try {
      setCart(await api.addToCart(productId));
      setPage("checkout");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const updateCartLine = async (itemId, quantity) => {
    try {
      setCart(await api.updateCart(itemId, quantity));
    } catch (error) {
      setNotice(error.message);
    }
  };

  const removeCartLine = async (itemId) => {
    try {
      setCart(await api.removeCart(itemId));
    } catch (error) {
      setNotice(error.message);
    }
  };

  const placeOrder = async (payment) => {
    if (!ensureCustomerAccess()) return;
    try {
      if (!checkoutAddress) {
        setNotice("Please add a delivery address first");
        setPage("checkout");
        return;
      }
      const placed = await api.placeOrder({ address: checkoutAddress, payment });
      setOrder(placed);
      setCart(emptyCart);
      setCheckoutAddress(null);
      await refreshOrders();
      await refreshAccountData();
      setPage("confirmation");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const completeAuth = useCallback((result, successMessage) => {
    resetProtectedState();
    setChatOpen(false);
    setAuthUser(result.user);
    setNotice(successMessage);
    setPage(result.user.role === "admin" ? "admin" : result.user.role === "seller" ? "seller" : "home");
  }, [resetProtectedState]);

  const login = useCallback(async (payload) => {
    try {
      const result = await api.login({ email: payload.email, password: payload.password });
      api.setToken(result.token);
      completeAuth(result, result.user.role === "admin" ? "Welcome, Admin!" : "Logged in");
    } catch (error) {
      setNotice(error.message);
    }
  }, [completeAuth]);

  const signup = useCallback(async (payload) => {
    try {
      const result = await api.signup(payload);
      api.setToken(result.token);
      completeAuth(result, "Account created");
    } catch (error) {
      setNotice(error.message);
    }
  }, [completeAuth]);

  const googleLogin = useCallback(async (payload) => {
    try {
      const result = await api.googleLogin(payload);
      api.setToken(result.token);
      completeAuth(result, "Signed in with Google");
    } catch (error) {
      setNotice(error.message);
    }
  }, [completeAuth]);

  const logoutUser = async () => {
    try {
      if (api.hasToken()) await api.logout();
    } catch (_) {
      // noop
    }
    api.clearToken();
    setAuthUser(null);
    resetProtectedState();
    setPage("home");
    setNotice("Logged out");
  };

  const toggleWishlist = async (productId) => {
    if (!ensureCustomerAccess()) return;
    try {
      const payload = await api.toggleWishlist(productId);
      setWishlist(payload.items);
    } catch (error) {
      setNotice(error.message);
    }
  };

  const addReview = async (payload) => {
    if (!ensureCustomerAccess("Please login to submit a review")) return;
    try {
      await api.addReview(payload);
      setProductReviews(await api.reviews(payload.product_id));
      setNotice("Review submitted");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const updateProfile = async (payload) => {
    try {
      await api.updateProfile(payload);
      await refreshProfile();
      setNotice("Profile updated");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const saveAddress = async (payload) => {
    try {
      const response = await api.addAddress(payload);
      setAddresses(response.items);
      await refreshProfile();
      setNotice("Address saved");
      return response.items;
    } catch (error) {
      setNotice(error.message);
      throw error;
    }
  };

  const updateAddress = async (addressId, payload) => {
    try {
      const response = await api.updateAddress(addressId, payload);
      setAddresses(response.items);
      await refreshProfile();
      setNotice("Address updated");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const deleteAddress = async (addressId) => {
    try {
      const response = await api.deleteAddress(addressId);
      setAddresses(response.items);
      await refreshProfile();
      setNotice("Address deleted");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const savePaymentMethod = async (payload) => {
    try {
      const response = await api.addPaymentMethod(payload);
      setPaymentMethods(response.items);
      setNotice("Payment method saved");
      return response.items;
    } catch (error) {
      setNotice(error.message);
      throw error;
    }
  };

  const deletePaymentMethod = async (paymentId) => {
    try {
      const response = await api.deletePaymentMethod(paymentId);
      setPaymentMethods(response.items);
      setNotice("Payment method deleted");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const submitComplaint = async (payload) => {
    try {
      await api.addComplaint(payload);
      const response = await api.complaints();
      setComplaints(response.items);
      setNotice("Complaint submitted");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const reorderOrder = async (orderNumber) => {
    try {
      setCart(await api.reorder(orderNumber));
      setPage("cart");
      setNotice("Order moved to cart");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const saveSellerProduct = async (productId, payload) => {
    try {
      if (productId) await api.updateSellerProduct(productId, payload);
      else await api.createSellerProduct(payload);
      await refreshSeller();
      setNotice(productId ? "Product updated" : "Product created and sent for approval");
    } catch (error) {
      setNotice(error.message);
      throw error;
    }
  };

  const deleteSellerProduct = async (productId) => {
    try {
      await api.deleteSellerProduct(productId);
      await refreshSeller();
      setNotice("Product deleted");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const updateSellerOrderItemStatus = async (orderId, itemId, status) => {
    try {
      await api.updateSellerOrderItemStatus(orderId, itemId, status);
      await refreshSeller();
      setNotice("Order item updated");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const respondToReview = async (reviewId, response) => {
    try {
      await api.respondToReview(reviewId, response);
      await refreshSeller();
      setNotice("Review response saved");
    } catch (error) {
      setNotice(error.message);
    }
  };

  const sendChatMessage = async (message) => {
    const nextMessages = [...chatMessages, { role: "user", content: message }];
    setChatMessages(nextMessages);
    setChatLoading(true);
    try {
      const result = await api.aiChat({ message, history: nextMessages.slice(-10).map((item) => ({ role: item.role, content: item.content })) });
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

  const clearChatHistory = async () => {
    if (!currentUser || currentUser.role === "admin") {
      setChatMessages(defaultChatMessages);
      setNotice("Local chat cleared");
      return;
    }
    try {
      await api.clearAiHistory();
      setChatMessages(defaultChatMessages);
      setNotice("Chat history cleared");
    } catch (error) {
      setNotice(error.message);
    }
  };

  return (
    <ErrorBoundary>
      <Header query={query} setQuery={setQuery} cartCount={cartCount} currentUser={currentUser} go={go} logout={logoutUser} />
      {notice && <button className="toast" onClick={() => setNotice("")}>{notice} x</button>}
      {page === "auth" && <AuthPage login={login} signup={signup} googleLogin={googleLogin} />}
      {page === "home" && <HomePage query={query} products={products} categories={categories} filters={filters} setFilters={setFilters} openProduct={openProduct} loading={loading} buyer={currentUser && currentUser.role !== "admin" ? currentUser : null} wishlistIds={wishlist.map((item) => item.id)} toggleWishlist={toggleWishlist} recommendations={recommendations} recentlyViewed={recentlyViewed} />}
      {page === "detail" && <ProductDetail product={selectedProduct} onBack={() => setPage("home")} addToCart={addToCart} buyNow={buyNow} reviews={productReviews} addReview={addReview} />}
      {page === "cart" && <CartPage cart={cart} updateCart={updateCartLine} removeCart={removeCartLine} go={go} />}
      {page === "checkout" && <CheckoutPage cart={cart} buyer={currentUser} addresses={addresses} setCheckoutAddress={setCheckoutAddress} go={go} saveAddress={saveAddress} />}
      {page === "payment" && <PaymentPage cart={cart} checkoutAddress={checkoutAddress} paymentMethods={paymentMethods} savePaymentMethod={savePaymentMethod} placeOrder={placeOrder} go={go} setNotice={setNotice} />}
      {page === "orders" && <OrdersPage orders={orders} buyer={currentUser} go={go} reorderOrder={reorderOrder} submitComplaint={submitComplaint} />}
      {page === "account" && <AccountPage user={currentUser} updateProfile={updateProfile} addresses={addresses} saveAddress={saveAddress} updateAddress={updateAddress} deleteAddress={deleteAddress} paymentMethods={paymentMethods} savePaymentMethod={savePaymentMethod} deletePaymentMethod={deletePaymentMethod} recentlyViewed={recentlyViewed} recommendations={recommendations} complaints={complaints} submitComplaint={submitComplaint} openProduct={openProduct} wishlistIds={wishlist.map((item) => item.id)} toggleWishlist={toggleWishlist} />}
      {page === "seller" && <SellerPage dashboard={sellerDashboard} categories={categories} saveSellerProduct={saveSellerProduct} deleteSellerProduct={deleteSellerProduct} updateSellerOrderItemStatus={updateSellerOrderItemStatus} respondToReview={respondToReview} />}
      {page === "admin" && <AdminPage setNotice={setNotice} />}
      {page === "confirmation" && <ConfirmationPage order={order} go={go} />}
      {page !== "auth" && page !== "admin" && <Footer />}
      {page !== "auth" && <AIChatWidget open={chatOpen} setOpen={setChatOpen} messages={chatMessages} sendMessage={sendChatMessage} clearHistory={clearChatHistory} loading={chatLoading} />}
    </ErrorBoundary>
  );
}
