import os
import re
import smtplib
import hmac
import hashlib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import razorpay
import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, select
from sqlalchemy.orm import Session, selectinload

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_FILE)

from .database import Base, engine, get_db
from .models import CartItem, Category, Order, OrderItem, Product, Review, User, WishlistItem
from .schemas import (
    AIChatIn,
    AIChatOut,
    CartAdd,
    CartOut,
    CartSummaryOut,
    CartUpdate,
    CategoryOut,
    CheckoutIn,
    AuthIn,
    AuthOut,
    OrderOut,
    OAuthIn,
    ProductOut,
    ReviewIn,
    ReviewOut,
    RazorpayOrderOut,
    RazorpayVerifyIn,
    AdminStatsOut,
    AdminDashboardOut,
    SellerDashboardOut,
    SellerStatsOut,
    SignupIn,
    UserOut,
    WishlistOut,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Flipkart Clone API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_USER_ID = 1
DEFAULT_SELLER_ID = 2

# ── Razorpay client ──────────────────────────────────────────────────────────
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
rzp_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)) if RAZORPAY_KEY_ID else None

# ── Gmail SMTP ────────────────────────────────────────────────────────────────
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

# ── Admin credentials ─────────────────────────────────────────────────────────
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@flipkart.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


# ── Runtime schema migrations ─────────────────────────────────────────────────
def ensure_runtime_schema():
    statements = [
        "CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(160) NOT NULL, email VARCHAR(180) NOT NULL UNIQUE, phone VARCHAR(20) NOT NULL, role VARCHAR(20) NOT NULL, address_line VARCHAR(255) DEFAULT '', city VARCHAR(100) DEFAULT '', state VARCHAR(100) DEFAULT '', pincode VARCHAR(12) DEFAULT '', store_name VARCHAR(160) DEFAULT '')",
        "ALTER TABLE users ADD COLUMN password_hash VARCHAR(128) DEFAULT ''",
        "ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(40) DEFAULT ''",
        "ALTER TABLE products ADD COLUMN seller_id INT DEFAULT 2",
        "ALTER TABLE orders ADD COLUMN payment_method VARCHAR(40) DEFAULT 'UPI'",
        "ALTER TABLE orders ADD COLUMN payment_status VARCHAR(40) DEFAULT 'PAID'",
        "ALTER TABLE orders ADD COLUMN payment_reference VARCHAR(80) DEFAULT ''",
        "ALTER TABLE orders ADD COLUMN tracking_status VARCHAR(80) DEFAULT 'Order placed'",
        "ALTER TABLE orders ADD COLUMN razorpay_order_id VARCHAR(80) DEFAULT ''",
        "ALTER TABLE order_items ADD COLUMN seller_id INT DEFAULT 2",
        "CREATE TABLE IF NOT EXISTS wishlist_items (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT DEFAULT 1, product_id INT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_wishlist_user (user_id), CONSTRAINT fk_wishlist_products FOREIGN KEY (product_id) REFERENCES products(id))",
        "CREATE TABLE IF NOT EXISTS reviews (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT DEFAULT 1, product_id INT NOT NULL, rating INT NOT NULL, comment TEXT NOT NULL, verified_purchase BOOLEAN DEFAULT FALSE, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_reviews_product (product_id), CONSTRAINT fk_reviews_products FOREIGN KEY (product_id) REFERENCES products(id))",
    ]
    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception:
                pass
        connection.execute(text("UPDATE products SET seller_id = 2 WHERE seller_id IS NULL"))
        connection.execute(text("UPDATE order_items SET seller_id = 2 WHERE seller_id IS NULL"))


ensure_runtime_schema()


# ── Helpers ───────────────────────────────────────────────────────────────────
def product_options():
    return selectinload(Product.category), selectinload(Product.images), selectinload(Product.specs)


def cart_summary(items: list[CartItem]) -> CartSummaryOut:
    mrp_total = sum(item.product.mrp * item.quantity for item in items)
    subtotal = sum(item.product.price * item.quantity for item in items)
    discount = max(mrp_total - subtotal, 0)
    delivery_fee = 0 if subtotal >= 499 or subtotal == 0 else 40
    return CartSummaryOut(
        mrp_total=round(mrp_total, 2),
        subtotal=round(subtotal, 2),
        discount=round(discount, 2),
        delivery_fee=delivery_fee,
        total=round(subtotal + delivery_fee, 2),
    )


def load_cart(db: Session, user_id: int = DEFAULT_USER_ID) -> list[CartItem]:
    return list(
        db.scalars(
            select(CartItem)
            .where(CartItem.user_id == user_id)
            .options(
                selectinload(CartItem.product).selectinload(Product.category),
                selectinload(CartItem.product).selectinload(Product.images),
                selectinload(CartItem.product).selectinload(Product.specs),
            )
        )
    )


def hash_password(password: str) -> str:
    return sha256(password.encode("utf-8")).hexdigest()


def token_for(user: User) -> str:
    return f"demo-token-{user.id}-{uuid4().hex[:8]}"


def build_ai_context(db: Session) -> str:
    products = db.scalars(
        select(Product).options(selectinload(Product.category)).order_by(Product.rating.desc(), Product.id.asc())
    ).all()
    cart_items = load_cart(db)
    orders = db.scalars(
        select(Order).where(Order.user_id == DEFAULT_USER_ID).options(selectinload(Order.items)).order_by(Order.id.desc())
    ).all()
    categories = db.scalars(select(Category).order_by(Category.name)).all()

    product_lines = [
        f"- {product.title} | {product.category.name} | price INR {product.price:.0f} | mrp INR {product.mrp:.0f} | rating {product.rating} | stock {product.stock}"
        for product in products[:10]
    ]
    cart_lines = [
        f"- {item.quantity} x {item.product.title} at INR {item.product.price:.0f}"
        for item in cart_items[:6]
    ] or ["- Cart is currently empty"]
    order_lines = [
        f"- {order.order_number} | {order.status} | {order.tracking_status} | INR {order.total_amount:.0f} | payment {order.payment_method}/{order.payment_status}"
        for order in orders[:6]
    ] or ["- No past orders yet"]
    category_line = ", ".join(category.name for category in categories)

    return "\n".join(
        [
            "Store categories:",
            category_line,
            "",
            "Featured catalog snapshot:",
            *product_lines,
            "",
            "Current buyer cart:",
            *cart_lines,
            "",
            "Recent buyer orders:",
            *order_lines,
        ]
    )


def extract_openai_text(payload: dict) -> str:
    if payload.get("output_text"):
        return payload["output_text"]
    chunks = []
    for item in payload.get("output", []):
        if item.get("type") != "message" or item.get("role") != "assistant":
            continue
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(content["text"])
    return "\n".join(chunks).strip()


def money_text(value: float) -> str:
    return f"INR {value:,.0f}"


def local_ai_reply(message: str, db: Session) -> str:
    text_value = message.strip()
    text_lower = text_value.lower()
    categories = db.scalars(select(Category).order_by(Category.name.asc())).all()

    def detect_category_slug() -> str | None:
        alias_map = {
            "phone": "mobiles",
            "phones": "mobiles",
            "mobile": "mobiles",
            "mobiles": "mobiles",
            "headphone": "electronics",
            "headphones": "electronics",
            "earbuds": "electronics",
            "tv": "electronics",
            "fashion": "fashion",
            "shirt": "fashion",
            "jacket": "fashion",
            "fridge": "home-appliances",
            "kitchen": "home-appliances",
            "appliance": "home-appliances",
            "groceries": "grocery",
            "grocery": "grocery",
            "dal": "grocery",
        }
        for term, slug in alias_map.items():
            if term in text_lower:
                return slug
        for category in categories:
            if category.name.lower() in text_lower or category.slug.lower() in text_lower:
                return category.slug
        return None

    budget_match = re.search(r"(\d[\d,]{2,})", text_value)
    budget = int(budget_match.group(1).replace(",", "")) if budget_match else None

    if any(keyword in text_lower for keyword in ["payment", "pay", "cod", "upi", "card", "paypal", "stripe", "razorpay"]):
        return (
            "You can check out with Razorpay, Stripe, PayPal, UPI, card, or Cash on Delivery. "
            "COD places the order with pending payment status, while digital methods store a payment reference after confirmation."
        )

    if any(keyword in text_lower for keyword in ["order", "orders", "tracking", "track", "history"]):
        orders = db.scalars(
            select(Order)
            .where(Order.user_id == DEFAULT_USER_ID)
            .options(selectinload(Order.items))
            .order_by(Order.id.desc())
        ).all()
        if not orders:
            return "You do not have any past orders yet. Add a product to cart, choose a payment method, and place your first order."
        lines = []
        for order in orders[:3]:
            item_text = ", ".join(f"{item.quantity} x {item.title}" for item in order.items[:2])
            if len(order.items) > 2:
                item_text += ", ..."
            lines.append(
                f"{order.order_number}: {order.tracking_status}, {order.payment_method}/{order.payment_status}, total {money_text(order.total_amount)}"
                + (f" ({item_text})" if item_text else "")
            )
        return "Here are your recent orders:\n" + "\n".join(lines)

    if any(keyword in text_lower for keyword in ["cart", "checkout", "buy now", "place order"]):
        cart_items = load_cart(db)
        summary = cart_summary(cart_items)
        if not cart_items:
            return "Your cart is empty right now. Add a product first, then continue to checkout, enter the delivery address, choose a payment method, and place the order."
        item_lines = ", ".join(f"{item.quantity} x {item.product.title}" for item in cart_items[:3])
        if len(cart_items) > 3:
            item_lines += ", ..."
        return (
            f"Your cart currently has {item_lines}. Total payable is {money_text(summary.total)} after {money_text(summary.discount)} discount. "
            "From there you can continue to checkout, confirm the address, choose payment, and place the order."
        )

    if "wishlist" in text_lower:
        wishlist_items = db.scalars(
            select(WishlistItem)
            .where(WishlistItem.user_id == DEFAULT_USER_ID)
            .options(selectinload(WishlistItem.product))
        ).all()
        if not wishlist_items:
            return "Your wishlist is empty right now. Use the Wishlist button on any product card to save it for later."
        picks = ", ".join(item.product.title for item in wishlist_items[:4])
        return f"Your wishlist currently includes {picks}."

    if any(keyword in text_lower for keyword in ["category", "categories", "filter", "filters", "search"]):
        category_text = ", ".join(category.name for category in categories)
        return (
            f"You can search from the top bar and filter by category, max price, and minimum rating. "
            f"Current categories are {category_text}."
        )

    requested_category_slug = detect_category_slug()
    wants_recommendations = any(
        keyword in text_lower
        for keyword in ["suggest", "recommend", "best", "show", "find", "phone", "mobile", "headphone", "product"]
    )
    if wants_recommendations:
        product_query = select(Product).options(selectinload(Product.category)).order_by(
            Product.rating.desc(), Product.reviews.desc(), Product.price.asc()
        )
        if requested_category_slug:
            product_query = product_query.join(Product.category).where(Category.slug == requested_category_slug)
        if budget is not None:
            product_query = product_query.where(Product.price <= budget)
        matches = db.scalars(product_query.limit(3)).all()
        if matches:
            lines = [f"- {product.title} for {money_text(product.price)} with rating {product.rating}" for product in matches]
            intro_bits = []
            if requested_category_slug:
                intro_bits.append(f"in {requested_category_slug.replace('-', ' ')}")
            if budget is not None:
                intro_bits.append(f"under {money_text(budget)}")
            intro = " ".join(intro_bits).strip()
            intro = f" {intro}" if intro else ""
            return "Here are a few strong picks" + intro + ":\n" + "\n".join(lines)

    featured = db.scalars(
        select(Product).order_by(Product.rating.desc(), Product.reviews.desc(), Product.price.asc()).limit(3)
    ).all()
    if featured:
        lines = [f"- {product.title} for {money_text(product.price)}" for product in featured]
        return (
            "I can help with products, cart, checkout, payments, reviews, and orders. "
            "Some popular options right now are:\n" + "\n".join(lines)
        )

    return "I can help with products, payments, checkout, reviews, and orders. Tell me what you want to find."


# ── Email helper ──────────────────────────────────────────────────────────────
def send_order_email(to_email: str, order_number: str, customer_name: str, total: float, items: list, payment_method: str):
    """Send order confirmation email via Gmail SMTP."""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("[Email] Skipped — EMAIL_USER or EMAIL_PASSWORD not set in .env")
        return

    items_html = "".join(
        f"<tr><td style='padding:6px 12px'>{item.title}</td><td style='padding:6px 12px;text-align:center'>{item.quantity}</td><td style='padding:6px 12px;text-align:right'>₹{item.price * item.quantity:,.0f}</td></tr>"
        for item in items
    )

    html = f"""
    <html><body style='font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto'>
      <div style='background:#2874f0;padding:20px;text-align:center'>
        <h1 style='color:#fff;margin:0'>Flipkart</h1>
      </div>
      <div style='padding:24px'>
        <h2>Hi {customer_name}, your order is confirmed! 🎉</h2>
        <p>Order ID: <strong>{order_number}</strong></p>
        <p>Payment: <strong>{payment_method}</strong></p>
        <table style='width:100%;border-collapse:collapse;margin:16px 0'>
          <thead>
            <tr style='background:#f5f5f5'>
              <th style='padding:8px 12px;text-align:left'>Product</th>
              <th style='padding:8px 12px'>Qty</th>
              <th style='padding:8px 12px;text-align:right'>Amount</th>
            </tr>
          </thead>
          <tbody>{items_html}</tbody>
        </table>
        <div style='text-align:right;font-size:18px;font-weight:bold;border-top:2px solid #f0f0f0;padding-top:12px'>
          Total: ₹{total:,.0f}
        </div>
        <p style='color:#388e3c;margin-top:20px'>📦 Your order has been placed and will be delivered soon.</p>
      </div>
      <div style='background:#f5f5f5;padding:12px;text-align:center;font-size:12px;color:#878787'>
        Flipkart Clone &mdash; Built with FastAPI & React
      </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Order Confirmed: {order_number} | Flipkart"
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, to_email, msg.as_string())
        print(f"[Email] Order confirmation sent to {to_email}")
    except Exception as exc:
        print(f"[Email] Failed to send email: {exc}")


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "razorpay": "configured" if rzp_client else "not configured (add keys to .env)",
        "email": "configured" if EMAIL_USER else "not configured (add Gmail to .env)",
        "openai": "configured" if OPENAI_API_KEY else "not configured (add OPENAI_API_KEY to .env)",
    }


@app.post("/api/ai/chat", response_model=AIChatOut)
def ai_chat(payload: AIChatIn, db: Session = Depends(get_db)):
    if not OPENAI_API_KEY:
        return AIChatOut(reply=local_ai_reply(payload.message, db), model="local-fallback")

    context_block = build_ai_context(db)
    instructions = (
        "You are Flipkart Clone AI Support, a concise shopping assistant for this demo store. "
        "Answer questions about products, cart contents, wishlist ideas, checkout, payment methods, seller and buyer features, "
        "recent orders, and general shopping help using the supplied store context when relevant. "
        "If the user asks for something that depends on data you do not have, say that clearly and then help with what you can. "
        "Keep answers brief, practical, and friendly."
    )
    history = [
        {
            "role": item.role,
            "content": [{"type": "input_text", "text": item.content}],
        }
        for item in payload.history[-10:]
    ]
    history.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": f"{context_block}\n\nUser question:\n{payload.message}",
                }
            ],
        }
    )

    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "instructions": instructions,
                "input": history,
                "max_output_tokens": 500,
            },
            timeout=45,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return AIChatOut(reply=local_ai_reply(payload.message, db), model="local-fallback")

    response_payload = response.json()
    reply = extract_openai_text(response_payload)
    if not reply:
        return AIChatOut(reply=local_ai_reply(payload.message, db), model="local-fallback")
    return AIChatOut(reply=reply, model=response_payload.get("model", OPENAI_MODEL))


# ── Auth ──────────────────────────────────────────────────────────────────────
@app.post("/api/auth/signup", response_model=AuthOut)
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        role="buyer",
        password_hash=hash_password(payload.password),
        oauth_provider="",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthOut(user=user, token=token_for(user))


@app.post("/api/auth/login", response_model=AuthOut)
def login(payload: AuthIn, db: Session = Depends(get_db)):
    # Admin login
    if payload.email == ADMIN_EMAIL and payload.password == ADMIN_PASSWORD:
        admin_user = User(id=0, name="Admin", email=ADMIN_EMAIL, phone="0000000000", role="admin", password_hash="", oauth_provider="", address_line="", city="", state="", pincode="", store_name="Flipkart Admin")
        return AuthOut(user=admin_user, token=f"admin-token-{uuid4().hex[:8]}")
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or user.password_hash != hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return AuthOut(user=user, token=token_for(user))


@app.post("/api/auth/oauth/google", response_model=AuthOut)
def google_oauth(payload: OAuthIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user:
        user = User(
            name=payload.name,
            email=payload.email,
            phone="9999999999",
            role="buyer",
            password_hash="",
            oauth_provider=payload.provider,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return AuthOut(user=user, token=token_for(user))


# ── Categories ────────────────────────────────────────────────────────────────
@app.get("/api/categories", response_model=list[CategoryOut])
def categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.name)).all()


# ── Users ─────────────────────────────────────────────────────────────────────
@app.get("/api/users", response_model=list[UserOut])
def users(db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.id)).all()


@app.get("/api/users/{user_id}", response_model=UserOut)
def user_detail(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── Products ──────────────────────────────────────────────────────────────────
@app.get("/api/products", response_model=list[ProductOut])
def products(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    min_price: float | None = Query(default=None),
    max_price: float | None = Query(default=None),
    min_rating: float | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(Product).options(*product_options()).join(Product.category)
    if search:
        stmt = stmt.where(Product.title.ilike(f"%{search}%"))
    if category and category != "all":
        stmt = stmt.where(Category.slug == category)
    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)
    if min_rating is not None:
        stmt = stmt.where(Product.rating >= min_rating)
    return db.scalars(stmt.order_by(Product.id)).all()


@app.get("/api/products/{product_id}", response_model=ProductOut)
def product_detail(product_id: int, db: Session = Depends(get_db)):
    product = db.scalar(select(Product).where(Product.id == product_id).options(*product_options()))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ── Cart ──────────────────────────────────────────────────────────────────────
@app.get("/api/cart", response_model=CartOut)
def get_cart(db: Session = Depends(get_db)):
    items = load_cart(db)
    return CartOut(items=items, summary=cart_summary(items))


@app.post("/api/cart", response_model=CartOut)
def add_to_cart(payload: CartAdd, db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock <= 0:
        raise HTTPException(status_code=400, detail="Product is out of stock")
    item = db.scalar(
        select(CartItem).where(CartItem.user_id == DEFAULT_USER_ID, CartItem.product_id == payload.product_id)
    )
    if item:
        item.quantity = min(item.quantity + payload.quantity, 10, product.stock)
    else:
        db.add(CartItem(user_id=DEFAULT_USER_ID, product_id=payload.product_id, quantity=min(payload.quantity, product.stock)))
    db.commit()
    items = load_cart(db)
    return CartOut(items=items, summary=cart_summary(items))


@app.patch("/api/cart/{item_id}", response_model=CartOut)
def update_cart(item_id: int, payload: CartUpdate, db: Session = Depends(get_db)):
    item = db.scalar(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == DEFAULT_USER_ID).options(selectinload(CartItem.product))
    )
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    item.quantity = min(payload.quantity, item.product.stock)
    db.commit()
    items = load_cart(db)
    return CartOut(items=items, summary=cart_summary(items))


@app.delete("/api/cart/{item_id}", response_model=CartOut)
def remove_cart_item(item_id: int, db: Session = Depends(get_db)):
    item = db.scalar(select(CartItem).where(CartItem.id == item_id, CartItem.user_id == DEFAULT_USER_ID))
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()
    items = load_cart(db)
    return CartOut(items=items, summary=cart_summary(items))


# ── Wishlist ──────────────────────────────────────────────────────────────────
@app.get("/api/wishlist", response_model=WishlistOut)
def get_wishlist(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(WishlistItem)
        .where(WishlistItem.user_id == DEFAULT_USER_ID)
        .options(
            selectinload(WishlistItem.product).selectinload(Product.category),
            selectinload(WishlistItem.product).selectinload(Product.images),
            selectinload(WishlistItem.product).selectinload(Product.specs),
        )
    ).all()
    return WishlistOut(items=[row.product for row in rows])


@app.post("/api/wishlist/{product_id}", response_model=WishlistOut)
def toggle_wishlist(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    row = db.scalar(
        select(WishlistItem).where(WishlistItem.user_id == DEFAULT_USER_ID, WishlistItem.product_id == product_id)
    )
    if row:
        db.delete(row)
    else:
        db.add(WishlistItem(user_id=DEFAULT_USER_ID, product_id=product_id))
    db.commit()
    return get_wishlist(db)


# ── Reviews ───────────────────────────────────────────────────────────────────
@app.get("/api/products/{product_id}/reviews", response_model=list[ReviewOut])
def product_reviews(product_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(Review).where(Review.product_id == product_id).options(selectinload(Review.user)).order_by(Review.id.desc())
    ).all()


@app.post("/api/reviews", response_model=ReviewOut)
def add_review(payload: ReviewIn, db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    verified = db.scalar(
        select(OrderItem).join(Order).where(Order.user_id == DEFAULT_USER_ID, OrderItem.product_id == payload.product_id)
    ) is not None
    review = Review(
        user_id=DEFAULT_USER_ID,
        product_id=payload.product_id,
        rating=payload.rating,
        comment=payload.comment,
        verified_purchase=verified,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return db.scalar(select(Review).where(Review.id == review.id).options(selectinload(Review.user)))


# ── Razorpay: Create Order ────────────────────────────────────────────────────
@app.post("/api/razorpay/create-order", response_model=RazorpayOrderOut)
def razorpay_create_order(db: Session = Depends(get_db)):
    """Create a Razorpay order for the current cart total."""
    if not rzp_client:
        raise HTTPException(status_code=503, detail="Razorpay not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to .env")

    items = load_cart(db)
    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    summary = cart_summary(items)
    amount_paise = int(summary.total * 100)  # Razorpay expects paise

    try:
        rzp_order = rzp_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"receipt_{uuid4().hex[:10]}",
            "payment_capture": 1,
        })
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Razorpay error: {str(exc)}")

    return RazorpayOrderOut(
        razorpay_order_id=rzp_order["id"],
        amount=amount_paise,
        currency="INR",
        key_id=RAZORPAY_KEY_ID,
    )


# ── Razorpay: Verify Payment ──────────────────────────────────────────────────
@app.post("/api/razorpay/verify")
def razorpay_verify(payload: RazorpayVerifyIn):
    """Verify Razorpay payment signature."""
    if not rzp_client:
        raise HTTPException(status_code=503, detail="Razorpay not configured")

    body = f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}"
    expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()

    if expected != payload.razorpay_signature:
        raise HTTPException(status_code=400, detail="Payment verification failed. Invalid signature.")

    return {"verified": True, "payment_id": payload.razorpay_payment_id}


# ── Place Order ───────────────────────────────────────────────────────────────
@app.post("/api/orders", response_model=OrderOut)
def place_order(payload: CheckoutIn, db: Session = Depends(get_db)):
    items = load_cart(db)
    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    for item in items:
        if item.quantity > item.product.stock:
            raise HTTPException(status_code=400, detail=f"Only {item.product.stock} units left for {item.product.title}")

    summary = cart_summary(items)
    order = Order(
        order_number=f"OD{uuid4().hex[:12].upper()}",
        user_id=DEFAULT_USER_ID,
        customer_name=payload.address.customer_name,
        phone=payload.address.phone,
        address_line=payload.address.address_line,
        city=payload.address.city,
        state=payload.address.state,
        pincode=payload.address.pincode,
        total_amount=summary.total,
        payment_method=payload.payment.method,
        payment_status="PENDING" if payload.payment.method == "COD" else "PAID",
        payment_reference=payload.payment.payment_reference or f"PAY{uuid4().hex[:10].upper()}",
        razorpay_order_id=payload.payment.razorpay_order_id or "",
    )

    for item in items:
        order.items.append(
            OrderItem(
                product_id=item.product_id,
                title=item.product.title,
                price=item.product.price,
                quantity=item.quantity,
                seller_id=item.product.seller_id,
            )
        )
        item.product.stock -= item.quantity
        db.delete(item)

    db.add(order)
    db.commit()
    db.refresh(order)

    # Reload order with items for email
    full_order = db.scalar(select(Order).where(Order.id == order.id).options(selectinload(Order.items)))

    # Send confirmation email
    buyer = db.get(User, DEFAULT_USER_ID)
    if buyer and buyer.email:
        send_order_email(
            to_email=buyer.email,
            order_number=full_order.order_number,
            customer_name=full_order.customer_name,
            total=full_order.total_amount,
            items=full_order.items,
            payment_method=full_order.payment_method,
        )

    return full_order


@app.get("/api/orders", response_model=list[OrderOut])
def order_history(db: Session = Depends(get_db)):
    return db.scalars(
        select(Order).where(Order.user_id == DEFAULT_USER_ID).options(selectinload(Order.items)).order_by(Order.id.desc())
    ).all()


@app.get("/api/orders/{order_number}", response_model=OrderOut)
def order_by_number(order_number: str, db: Session = Depends(get_db)):
    order = db.scalar(select(Order).where(Order.order_number == order_number).options(selectinload(Order.items)))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ── Seller Dashboard ──────────────────────────────────────────────────────────
@app.get("/api/seller/{seller_id}/dashboard", response_model=SellerDashboardOut)
def seller_dashboard(seller_id: int, db: Session = Depends(get_db)):
    seller = db.get(User, seller_id)
    if not seller or seller.role != "seller":
        raise HTTPException(status_code=404, detail="Seller not found")

    prods = db.scalars(select(Product).where(Product.seller_id == seller_id).options(*product_options()).order_by(Product.id)).all()
    ords = db.scalars(
        select(Order).join(Order.items).where(OrderItem.seller_id == seller_id).options(selectinload(Order.items)).order_by(Order.id.desc())
    ).unique().all()
    seller_items = [item for order in ords for item in order.items if item.seller_id == seller_id]
    stats = SellerStatsOut(
        product_count=len(prods),
        units_sold=sum(item.quantity for item in seller_items),
        revenue=round(sum(item.price * item.quantity for item in seller_items), 2),
        order_count=len(ords),
    )
    return SellerDashboardOut(seller=seller, products=prods, orders=ords, stats=stats)


# ── Admin Dashboard ───────────────────────────────────────────────────────────
@app.get("/api/admin/dashboard", response_model=AdminDashboardOut)
def admin_dashboard(db: Session = Depends(get_db)):
    all_users = db.scalars(select(User).order_by(User.id)).all()
    all_products = db.scalars(select(Product).options(*product_options()).order_by(Product.id)).all()
    all_orders = db.scalars(select(Order).options(selectinload(Order.items)).order_by(Order.id.desc())).all()

    total_revenue = round(sum(o.total_amount for o in all_orders), 2)
    paid_orders = [o for o in all_orders if o.payment_status == "PAID"]

    stats = AdminStatsOut(
        total_users=len(all_users),
        total_products=len(all_products),
        total_orders=len(all_orders),
        total_revenue=total_revenue,
        paid_orders=len(paid_orders),
        pending_orders=len(all_orders) - len(paid_orders),
    )

    return AdminDashboardOut(stats=stats, users=all_users, products=all_products, orders=all_orders)


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"deleted": True}


@app.delete("/api/admin/products/{product_id}")
def admin_delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"deleted": True}
