import os
import re
import smtplib
import hmac
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import razorpay
import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, func, text, select
from sqlalchemy.orm import Session, selectinload

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_FILE)

from .database import Base, engine, get_db
from .models import (
    AIChatMessage,
    AuthSession,
    CartItem,
    Category,
    Complaint,
    FraudFlag,
    Order,
    OrderItem,
    PaymentTransaction,
    Product,
    ProductImage,
    ProductSpec,
    RecentlyViewedProduct,
    Review,
    SavedPaymentMethod,
    User,
    UserAddress,
    WishlistItem,
)
from .schemas import (
    AccountUpdateIn,
    AIChatIn,
    AIChatHistoryOut,
    AIChatMessageOut,
    AIChatOut,
    AddressIn,
    AddressListOut,
    AddressOut,
    AddressUpdateIn,
    AdminUserUpdateIn,
    CartAdd,
    CartOut,
    CartSummaryOut,
    CartUpdate,
    CategoryOut,
    CheckoutIn,
    ComplaintIn,
    ComplaintListOut,
    ComplaintOut,
    ComplaintUpdateIn,
    AuthIn,
    AuthOut,
    GrowthStatsOut,
    OrderOut,
    OrderStatusUpdateIn,
    OAuthIn,
    PaymentTransactionOut,
    ProductOut,
    ProductListOut,
    ProductModerationIn,
    RefundUpdateIn,
    ReviewIn,
    ReviewOut,
    ReviewResponseIn,
    RazorpayOrderOut,
    RazorpayVerifyIn,
    AdminStatsOut,
    AdminDashboardOut,
    FraudFlagOut,
    SavedPaymentMethodIn,
    SavedPaymentMethodListOut,
    SavedPaymentMethodOut,
    SellerDashboardOut,
    SellerProductIn,
    SellerProductUpdateIn,
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
SESSION_DAYS = 7

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
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


# ── Runtime schema migrations ─────────────────────────────────────────────────
def ensure_runtime_schema():
    statements = [
        "CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(160) NOT NULL, email VARCHAR(180) NOT NULL UNIQUE, phone VARCHAR(20) NOT NULL, role VARCHAR(20) NOT NULL, address_line VARCHAR(255) DEFAULT '', city VARCHAR(100) DEFAULT '', state VARCHAR(100) DEFAULT '', pincode VARCHAR(12) DEFAULT '', store_name VARCHAR(160) DEFAULT '')",
        "ALTER TABLE users ADD COLUMN password_hash VARCHAR(128) DEFAULT ''",
        "ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(40) DEFAULT ''",
        "ALTER TABLE users ADD COLUMN google_sub VARCHAR(160) DEFAULT ''",
        "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN seller_status VARCHAR(20) DEFAULT 'APPROVED'",
        "ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE products ADD COLUMN seller_id INT DEFAULT 2",
        "ALTER TABLE products ADD COLUMN listing_status VARCHAR(20) DEFAULT 'APPROVED'",
        "ALTER TABLE products ADD COLUMN approval_note VARCHAR(255) DEFAULT ''",
        "ALTER TABLE products ADD COLUMN low_stock_threshold INT DEFAULT 5",
        "ALTER TABLE orders ADD COLUMN payment_method VARCHAR(40) DEFAULT 'UPI'",
        "ALTER TABLE orders ADD COLUMN payment_status VARCHAR(40) DEFAULT 'PAID'",
        "ALTER TABLE orders ADD COLUMN payment_reference VARCHAR(80) DEFAULT ''",
        "ALTER TABLE orders ADD COLUMN tracking_status VARCHAR(80) DEFAULT 'Order placed'",
        "ALTER TABLE orders ADD COLUMN razorpay_order_id VARCHAR(80) DEFAULT ''",
        "ALTER TABLE orders ADD COLUMN refund_status VARCHAR(40) DEFAULT 'NONE'",
        "ALTER TABLE order_items ADD COLUMN seller_id INT DEFAULT 2",
        "ALTER TABLE order_items ADD COLUMN status VARCHAR(40) DEFAULT 'PLACED'",
        "ALTER TABLE order_items ADD COLUMN tracking_status VARCHAR(80) DEFAULT 'Placed'",
        "CREATE TABLE IF NOT EXISTS wishlist_items (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT DEFAULT 1, product_id INT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_wishlist_user (user_id), CONSTRAINT fk_wishlist_products FOREIGN KEY (product_id) REFERENCES products(id))",
        "CREATE TABLE IF NOT EXISTS reviews (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT DEFAULT 1, product_id INT NOT NULL, rating INT NOT NULL, comment TEXT NOT NULL, verified_purchase BOOLEAN DEFAULT FALSE, seller_response TEXT, seller_responded_at DATETIME NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_reviews_product (product_id), CONSTRAINT fk_reviews_products FOREIGN KEY (product_id) REFERENCES products(id))",
        "ALTER TABLE reviews ADD COLUMN seller_response TEXT",
        "ALTER TABLE reviews ADD COLUMN seller_responded_at DATETIME NULL",
        "CREATE TABLE IF NOT EXISTS ai_chat_messages (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT DEFAULT 1, role VARCHAR(20) NOT NULL, content TEXT NOT NULL, model_name VARCHAR(80) DEFAULT '', created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_ai_chat_user (user_id))",
        "CREATE TABLE IF NOT EXISTS auth_sessions (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NULL, role VARCHAR(20) NOT NULL, email VARCHAR(180) DEFAULT '', token_hash VARCHAR(128) NOT NULL UNIQUE, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, expires_at DATETIME NOT NULL, revoked_at DATETIME NULL, INDEX ix_auth_sessions_user_id (user_id), INDEX ix_auth_sessions_token_hash (token_hash))",
        "CREATE TABLE IF NOT EXISTS user_addresses (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, label VARCHAR(60) DEFAULT 'Home', customer_name VARCHAR(160) NOT NULL, phone VARCHAR(20) NOT NULL, address_line VARCHAR(255) NOT NULL, city VARCHAR(100) NOT NULL, state VARCHAR(100) NOT NULL, pincode VARCHAR(12) NOT NULL, is_default BOOLEAN DEFAULT FALSE, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_user_addresses_user (user_id), CONSTRAINT fk_user_addresses_user FOREIGN KEY (user_id) REFERENCES users(id))",
        "CREATE TABLE IF NOT EXISTS saved_payment_methods (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, provider VARCHAR(40) NOT NULL, label VARCHAR(80) NOT NULL, upi_id VARCHAR(120) DEFAULT '', card_last4 VARCHAR(4) DEFAULT '', is_default BOOLEAN DEFAULT FALSE, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_saved_payment_user (user_id), CONSTRAINT fk_saved_payment_user FOREIGN KEY (user_id) REFERENCES users(id))",
        "CREATE TABLE IF NOT EXISTS recently_viewed_products (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, product_id INT NOT NULL, viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_recently_viewed_user (user_id), INDEX ix_recently_viewed_product (product_id), CONSTRAINT fk_recently_viewed_user FOREIGN KEY (user_id) REFERENCES users(id), CONSTRAINT fk_recently_viewed_product FOREIGN KEY (product_id) REFERENCES products(id))",
        "CREATE TABLE IF NOT EXISTS payment_transactions (id INT AUTO_INCREMENT PRIMARY KEY, order_id INT NOT NULL, user_id INT NOT NULL, provider VARCHAR(40) NOT NULL, amount FLOAT NOT NULL, status VARCHAR(40) DEFAULT 'PAID', reference VARCHAR(120) DEFAULT '', refund_status VARCHAR(40) DEFAULT 'NONE', created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_payment_transactions_order (order_id), INDEX ix_payment_transactions_user (user_id), CONSTRAINT fk_payment_transactions_order FOREIGN KEY (order_id) REFERENCES orders(id), CONSTRAINT fk_payment_transactions_user FOREIGN KEY (user_id) REFERENCES users(id))",
        "CREATE TABLE IF NOT EXISTS complaints (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, order_id INT NULL, product_id INT NULL, subject VARCHAR(160) NOT NULL, message TEXT NOT NULL, status VARCHAR(40) DEFAULT 'OPEN', resolution_note TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_complaints_user (user_id), CONSTRAINT fk_complaints_user FOREIGN KEY (user_id) REFERENCES users(id), CONSTRAINT fk_complaints_order FOREIGN KEY (order_id) REFERENCES orders(id), CONSTRAINT fk_complaints_product FOREIGN KEY (product_id) REFERENCES products(id))",
        "CREATE TABLE IF NOT EXISTS fraud_flags (id INT AUTO_INCREMENT PRIMARY KEY, order_id INT NOT NULL, reason VARCHAR(255) NOT NULL, severity VARCHAR(20) DEFAULT 'MEDIUM', status VARCHAR(40) DEFAULT 'OPEN', created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_fraud_flags_order (order_id), CONSTRAINT fk_fraud_flags_order FOREIGN KEY (order_id) REFERENCES orders(id))",
    ]
    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception:
                pass
        connection.execute(text("UPDATE products SET seller_id = 2 WHERE seller_id IS NULL"))
        connection.execute(text("UPDATE products SET listing_status = 'APPROVED' WHERE listing_status IS NULL OR listing_status = ''"))
        connection.execute(text("UPDATE products SET low_stock_threshold = 5 WHERE low_stock_threshold IS NULL"))
        connection.execute(text("UPDATE order_items SET seller_id = 2 WHERE seller_id IS NULL"))
        connection.execute(text("UPDATE order_items SET status = 'PLACED' WHERE status IS NULL OR status = ''"))
        connection.execute(text("UPDATE order_items SET tracking_status = 'Placed' WHERE tracking_status IS NULL OR tracking_status = ''"))
        connection.execute(text("UPDATE users SET is_active = TRUE WHERE is_active IS NULL"))
        connection.execute(text("UPDATE users SET seller_status = CASE WHEN role = 'seller' THEN 'APPROVED' ELSE 'APPROVED' END WHERE seller_status IS NULL OR seller_status = ''"))


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


def load_ai_history(db: Session, user_id: int = DEFAULT_USER_ID, limit: int = 30) -> list[AIChatMessage]:
    items = list(
        db.scalars(
            select(AIChatMessage)
            .where(AIChatMessage.user_id == user_id)
            .order_by(AIChatMessage.id.desc())
            .limit(limit)
        )
    )
    items.reverse()
    return items


def save_ai_turn(db: Session, user_message: str, assistant_message: str, model_name: str, user_id: int = DEFAULT_USER_ID):
    db.add(AIChatMessage(user_id=user_id, role="user", content=user_message, model_name=""))
    db.add(AIChatMessage(user_id=user_id, role="assistant", content=assistant_message, model_name=model_name))
    db.commit()


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 390000).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def legacy_hash_password(password: str) -> str:
    return sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    if stored_hash.startswith("pbkdf2_sha256$"):
        _, salt, expected = stored_hash.split("$", 2)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 390000).hex()
        return hmac.compare_digest(digest, expected)
    return legacy_hash_password(password) == stored_hash


def build_admin_user() -> User:
    return User(
        id=0,
        name="Admin",
        email=ADMIN_EMAIL,
        phone="0000000000",
        role="admin",
        password_hash="",
        oauth_provider="",
        google_sub="",
        is_active=True,
        seller_status="APPROVED",
        address_line="",
        city="",
        state="",
        pincode="",
        store_name="Flipkart Admin",
    )


def token_hash_for(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, user: User | None, role: str, email: str) -> str:
    raw_token = uuid4().hex + uuid4().hex
    db.add(
        AuthSession(
            user_id=user.id if user else None,
            role=role,
            email=email,
            token_hash=token_hash_for(raw_token),
            expires_at=datetime.utcnow() + timedelta(days=SESSION_DAYS),
        )
    )
    db.commit()
    return raw_token


def get_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def get_current_session(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AuthSession | None:
    token = get_bearer_token(authorization)
    if not token:
        return None
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash_for(token)))
    if not session:
        return None
    if session.revoked_at is not None or session.expires_at <= datetime.utcnow():
        return None
    return session


def require_current_session(session: AuthSession | None = Depends(get_current_session)) -> AuthSession:
    if not session:
        raise HTTPException(status_code=401, detail="Please login to continue")
    return session


def get_optional_user(
    session: AuthSession | None = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> User | None:
    if not session:
        return None
    if session.role == "admin":
        return build_admin_user()
    if session.user_id is None:
        return None
    user = db.get(User, session.user_id)
    if not user:
        session.revoked_at = datetime.utcnow()
        db.commit()
        return None
    if not user.is_active:
        session.revoked_at = datetime.utcnow()
        db.commit()
        return None
    return user


def require_user(user: User | None = Depends(get_optional_user)) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Please login to continue")
    return user


def require_customer_user(user: User = Depends(require_user)) -> User:
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Admins cannot use this action")
    return user


def require_seller_user(user: User = Depends(require_user)) -> User:
    if user.role != "seller":
        raise HTTPException(status_code=403, detail="Seller access required")
    if user.seller_status != "APPROVED":
        raise HTTPException(status_code=403, detail=f"Seller account is {user.seller_status.lower()}")
    return user


def require_admin_user(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def revoke_session(db: Session, session: AuthSession):
    session.revoked_at = datetime.utcnow()
    db.commit()


ORDER_STATUS_FLOW = ["PLACED", "PACKED", "SHIPPED", "DELIVERED"]
TRACKING_COPY = {
    "PLACED": "Order placed",
    "PACKED": "Packed",
    "SHIPPED": "Shipped",
    "DELIVERED": "Delivered",
}


def sync_review_stats(db: Session, product_id: int):
    reviews = db.scalars(select(Review).where(Review.product_id == product_id)).all()
    product = db.get(Product, product_id)
    if not product:
        return
    if not reviews:
        product.rating = 0
        product.reviews = 0
        return
    product.rating = round(sum(review.rating for review in reviews) / len(reviews), 1)
    product.reviews = len(reviews)


def sync_order_status(order: Order):
    statuses = [item.status for item in order.items]
    if not statuses:
        order.status = "PLACED"
        order.tracking_status = TRACKING_COPY["PLACED"]
        return
    if all(status == "DELIVERED" for status in statuses):
        order.status = "DELIVERED"
    elif all(status in {"SHIPPED", "DELIVERED"} for status in statuses):
        order.status = "SHIPPED"
    elif all(status in {"PACKED", "SHIPPED", "DELIVERED"} for status in statuses):
        order.status = "PACKED"
    else:
        order.status = "PLACED"
    order.tracking_status = TRACKING_COPY[order.status]


def set_default_address(db: Session, user_id: int, address_id: int):
    addresses = db.scalars(select(UserAddress).where(UserAddress.user_id == user_id)).all()
    for address in addresses:
        address.is_default = address.id == address_id


def set_default_payment(db: Session, user_id: int, payment_id: int):
    methods = db.scalars(select(SavedPaymentMethod).where(SavedPaymentMethod.user_id == user_id)).all()
    for method in methods:
        method.is_default = method.id == payment_id


def record_recently_viewed(db: Session, user_id: int, product_id: int):
    existing = db.scalar(
        select(RecentlyViewedProduct).where(
            RecentlyViewedProduct.user_id == user_id,
            RecentlyViewedProduct.product_id == product_id,
        )
    )
    if existing:
        existing.viewed_at = datetime.utcnow()
    else:
        db.add(RecentlyViewedProduct(user_id=user_id, product_id=product_id))
    db.commit()

    old_rows = db.scalars(
        select(RecentlyViewedProduct)
        .where(RecentlyViewedProduct.user_id == user_id)
        .order_by(RecentlyViewedProduct.viewed_at.desc(), RecentlyViewedProduct.id.desc())
        .offset(12)
    ).all()
    for row in old_rows:
        db.delete(row)
    if old_rows:
        db.commit()


def recommended_products_for_user(db: Session, user_id: int) -> list[Product]:
    wishlist_ids = {
        row.product_id
        for row in db.scalars(select(WishlistItem).where(WishlistItem.user_id == user_id)).all()
    }
    recent_rows = db.scalars(
        select(RecentlyViewedProduct).where(RecentlyViewedProduct.user_id == user_id).order_by(RecentlyViewedProduct.viewed_at.desc())
    ).all()
    recent_ids = [row.product_id for row in recent_rows]
    orders = db.scalars(
        select(Order).where(Order.user_id == user_id).options(selectinload(Order.items)).order_by(Order.id.desc())
    ).all()
    purchased_ids = {item.product_id for order in orders for item in order.items}
    liked_product_ids = list(wishlist_ids) + recent_ids + list(purchased_ids)

    liked_products = []
    if liked_product_ids:
        liked_products = db.scalars(
            select(Product).where(Product.id.in_(liked_product_ids)).options(selectinload(Product.category))
        ).all()

    category_counter = Counter(product.category_id for product in liked_products if product.category_id)
    preferred_category_ids = [category_id for category_id, _ in category_counter.most_common(3)]
    excluded_ids = wishlist_ids | purchased_ids | set(recent_ids)

    stmt = select(Product).where(Product.listing_status == "APPROVED").options(*product_options())
    if preferred_category_ids:
        stmt = stmt.where(Product.category_id.in_(preferred_category_ids))
    if excluded_ids:
        stmt = stmt.where(~Product.id.in_(excluded_ids))
    picks = db.scalars(stmt.order_by(Product.rating.desc(), Product.reviews.desc(), Product.id.desc()).limit(8)).all()
    if picks:
        return picks
    fallback = select(Product).where(Product.listing_status == "APPROVED").options(*product_options()).order_by(
        Product.rating.desc(), Product.reviews.desc(), Product.id.desc()
    )
    return db.scalars(fallback.limit(8)).all()


def create_payment_transaction(db: Session, order: Order):
    transaction = PaymentTransaction(
        order_id=order.id,
        user_id=order.user_id,
        provider=order.payment_method,
        amount=order.total_amount,
        status=order.payment_status,
        reference=order.payment_reference,
        refund_status=order.refund_status,
    )
    db.add(transaction)
    db.commit()
    return transaction


def maybe_create_fraud_flag(db: Session, order: Order):
    total_units = sum(item.quantity for item in order.items)
    reasons = []
    if order.payment_method == "COD" and order.total_amount >= 25000:
        reasons.append("High-value COD order")
    if order.total_amount >= 50000:
        reasons.append("High-value transaction")
    if total_units >= 6:
        reasons.append("Large unit count in a single order")
    for reason in reasons:
        db.add(FraudFlag(order_id=order.id, reason=reason, severity="HIGH" if "High-value" in reason else "MEDIUM"))
    if reasons:
        db.commit()


def seller_order_payload(order: Order, seller_id: int) -> Order:
    seller_items = [item for item in order.items if item.seller_id == seller_id]
    return SimpleNamespace(
        id=order.id,
        order_number=order.order_number,
        user_id=order.user_id,
        customer_name=order.customer_name,
        phone=order.phone,
        address_line=order.address_line,
        city=order.city,
        state=order.state,
        pincode=order.pincode,
        total_amount=sum(item.price * item.quantity for item in seller_items),
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        payment_reference=order.payment_reference,
        razorpay_order_id=order.razorpay_order_id,
        status=order.status,
        tracking_status=order.tracking_status,
        refund_status=order.refund_status,
        created_at=order.created_at,
        items=seller_items,
    )


def growth_percent(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def verify_google_credential(credential: str) -> dict:
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    try:
        response = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": credential},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="Unable to verify Google login right now") from exc

    payload = response.json()
    if payload.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Google client ID mismatch")
    if payload.get("email_verified") not in {"true", True, "True"}:
        raise HTTPException(status_code=400, detail="Google email is not verified")
    if payload.get("iss") not in {"https://accounts.google.com", "accounts.google.com"}:
        raise HTTPException(status_code=400, detail="Invalid Google issuer")
    return payload


def build_ai_context(db: Session, user_id: int | None = None) -> str:
    products = db.scalars(
        select(Product).where(Product.listing_status == "APPROVED").options(selectinload(Product.category)).order_by(Product.rating.desc(), Product.id.asc())
    ).all()
    cart_items = load_cart(db, user_id) if user_id else []
    orders = (
        db.scalars(
            select(Order).where(Order.user_id == user_id).options(selectinload(Order.items)).order_by(Order.id.desc())
        ).all()
        if user_id
        else []
    )
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


def product_discount_percent(product: Product) -> int:
    if not product.mrp:
        return 0
    return round(((product.mrp - product.price) / product.mrp) * 100)


def spec_summary(product: Product, count: int = 2) -> str:
    top_specs = [f"{spec.name}: {spec.value}" for spec in product.specs[:count]]
    return ", ".join(top_specs) if top_specs else "No highlighted specs"


def find_products_for_comparison(text_lower: str, products: list[Product]) -> list[Product]:
    exact_matches = [product for product in products if product.title.lower() in text_lower]
    if len(exact_matches) >= 2:
        return exact_matches[:2]

    brand_matches = []
    seen_ids = {product.id for product in exact_matches}
    for product in products:
        if product.id in seen_ids:
            continue
        if product.brand.lower() in text_lower:
            brand_matches.append(product)
            seen_ids.add(product.id)
    if len(exact_matches) + len(brand_matches) >= 2:
        return (exact_matches + brand_matches)[:2]

    ranked_matches = []
    stop_words = {"with", "from", "price", "under", "compare", "versus", "between", "which", "better", "than", "best"}
    for product in products:
        tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", product.title.lower())
            if len(token) > 3 and token not in stop_words
        }
        score = sum(token in text_lower for token in tokens)
        if score >= 2:
            ranked_matches.append((score, product))
    ranked_matches.sort(key=lambda item: (-item[0], -item[1].rating, item[1].price))
    unique_matches = []
    seen_ids = set()
    for _, product in ranked_matches:
        if product.id in seen_ids:
            continue
        unique_matches.append(product)
        seen_ids.add(product.id)
        if len(unique_matches) == 2:
            break
    return unique_matches


def comparison_reply(selected: list[Product]) -> str:
    if len(selected) < 2:
        return ""
    left, right = selected[:2]
    cheaper = left if left.price < right.price else right if right.price < left.price else None
    better_rated = left if left.rating > right.rating else right if right.rating > left.rating else None
    bigger_discount = (
        left if product_discount_percent(left) > product_discount_percent(right)
        else right if product_discount_percent(right) > product_discount_percent(left)
        else None
    )
    lines = [
        f"Comparing {left.title} and {right.title}:",
        f"- {left.title}: {left.category.name}, {money_text(left.price)} vs MRP {money_text(left.mrp)}, rating {left.rating}, stock {left.stock}, {product_discount_percent(left)}% off. Key specs: {spec_summary(left)}.",
        f"- {right.title}: {right.category.name}, {money_text(right.price)} vs MRP {money_text(right.mrp)}, rating {right.rating}, stock {right.stock}, {product_discount_percent(right)}% off. Key specs: {spec_summary(right)}.",
    ]
    summary = []
    if cheaper:
        summary.append(f"{cheaper.brand} is the cheaper option")
    if better_rated:
        summary.append(f"{better_rated.brand} is rated higher")
    if bigger_discount:
        summary.append(f"{bigger_discount.brand} has the bigger discount")
    if summary:
        lines.append("Quick take: " + "; ".join(summary) + ".")
    return "\n".join(lines)


def local_ai_reply(message: str, db: Session, user: User | None = None) -> str:
    text_value = message.strip()
    text_lower = text_value.lower()
    current_user_id = user.id if user and user.role != "admin" else None
    categories = db.scalars(select(Category).order_by(Category.name.asc())).all()
    products = db.scalars(
        select(Product)
        .where(Product.listing_status == "APPROVED")
        .options(selectinload(Product.category), selectinload(Product.specs))
        .order_by(Product.rating.desc(), Product.reviews.desc(), Product.price.asc())
    ).all()

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
    comparison_trigger = any(keyword in text_lower for keyword in ["compare", "comparison", "vs", "versus", "difference", "better"])

    if comparison_trigger:
        comparison_products = find_products_for_comparison(text_lower, products)
        comparison_text = comparison_reply(comparison_products)
        if comparison_text:
            return comparison_text

    if any(keyword in text_lower for keyword in ["payment", "pay", "cod", "upi", "card", "paypal", "stripe", "razorpay"]):
        return (
            "You can check out with Razorpay, Stripe, PayPal, UPI, card, or Cash on Delivery. "
            "COD places the order with pending payment status, while digital methods store a payment reference after confirmation."
        )

    if any(keyword in text_lower for keyword in ["order", "orders", "tracking", "track", "history"]):
        if not current_user_id:
            return "Login to see your recent orders and tracking updates."
        orders = db.scalars(
            select(Order)
            .where(Order.user_id == current_user_id)
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
        if not current_user_id:
            return "Login to manage your cart, checkout, and place orders."
        cart_items = load_cart(db, current_user_id)
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
        if not current_user_id:
            return "Login to save products in your wishlist and revisit them later."
        wishlist_items = db.scalars(
            select(WishlistItem)
            .where(WishlistItem.user_id == current_user_id)
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
        ).where(Product.listing_status == "APPROVED")
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

    featured = products[:3]
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
        "google_oauth": "configured" if GOOGLE_CLIENT_ID else "not configured (add GOOGLE_CLIENT_ID to .env)",
    }


@app.get("/api/ai/history", response_model=AIChatHistoryOut)
def ai_history(current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    return AIChatHistoryOut(items=load_ai_history(db, current_user.id))


@app.delete("/api/ai/history", response_model=AIChatHistoryOut)
def clear_ai_history(current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    db.execute(delete(AIChatMessage).where(AIChatMessage.user_id == current_user.id))
    db.commit()
    return AIChatHistoryOut(items=[])


@app.post("/api/ai/chat", response_model=AIChatOut)
def ai_chat(payload: AIChatIn, current_user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    chat_user_id = current_user.id if current_user and current_user.role != "admin" else None
    history_seed = payload.history[-10:]
    if not history_seed and chat_user_id:
        history_seed = [
            AIChatMessageOut.model_validate(item, from_attributes=True)
            for item in load_ai_history(db, user_id=chat_user_id, limit=10)
        ]

    if not OPENAI_API_KEY:
        reply = local_ai_reply(payload.message, db, current_user)
        if chat_user_id:
            save_ai_turn(db, payload.message, reply, "local-fallback", user_id=chat_user_id)
        return AIChatOut(reply=reply, model="local-fallback")

    context_block = build_ai_context(db, user_id=chat_user_id)
    instructions = (
        "You are Flipkart Clone AI Support, a concise shopping assistant for this demo store. "
        "Answer questions about products, cart contents, wishlist ideas, checkout, payment methods, seller and buyer features, "
        "Offer direct product comparisons when asked, calling out price, discount, ratings, stock, and a couple of key specs. "
        "recent orders, and general shopping help using the supplied store context when relevant. "
        "If the user asks for something that depends on data you do not have, say that clearly and then help with what you can. "
        "Keep answers brief, practical, and friendly."
    )
    history = [
        {
            "role": item.role,
            "content": [{"type": "input_text", "text": item.content}],
        }
        for item in history_seed
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
        reply = local_ai_reply(payload.message, db, current_user)
        if chat_user_id:
            save_ai_turn(db, payload.message, reply, "local-fallback", user_id=chat_user_id)
        return AIChatOut(reply=reply, model="local-fallback")

    response_payload = response.json()
    reply = extract_openai_text(response_payload)
    if not reply:
        reply = local_ai_reply(payload.message, db, current_user)
        if chat_user_id:
            save_ai_turn(db, payload.message, reply, "local-fallback", user_id=chat_user_id)
        return AIChatOut(reply=reply, model="local-fallback")
    if chat_user_id:
        save_ai_turn(db, payload.message, reply, response_payload.get("model", OPENAI_MODEL), user_id=chat_user_id)
    return AIChatOut(reply=reply, model=response_payload.get("model", OPENAI_MODEL))


# ── Auth ──────────────────────────────────────────────────────────────────────
@app.get("/api/auth/me", response_model=UserOut)
def auth_me(current_user: User = Depends(require_user)):
    return current_user


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
    return AuthOut(user=user, token=create_session(db, user, user.role, user.email))


@app.post("/api/auth/login", response_model=AuthOut)
def login(payload: AuthIn, db: Session = Depends(get_db)):
    if payload.email == ADMIN_EMAIL and payload.password == ADMIN_PASSWORD:
        admin_user = build_admin_user()
        return AuthOut(user=admin_user, token=create_session(db, None, "admin", ADMIN_EMAIL))
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    if user.role == "seller" and user.seller_status == "SUSPENDED":
        raise HTTPException(status_code=403, detail="Seller account is suspended")
    if user.password_hash and not user.password_hash.startswith("pbkdf2_sha256$"):
        user.password_hash = hash_password(payload.password)
        db.commit()
    return AuthOut(user=user, token=create_session(db, user, user.role, user.email))


@app.post("/api/auth/oauth/google", response_model=AuthOut)
def google_oauth(payload: OAuthIn, db: Session = Depends(get_db)):
    google_user = verify_google_credential(payload.credential)
    google_sub = google_user.get("sub", "")
    email = google_user.get("email", "")
    if not email:
        raise HTTPException(status_code=400, detail="Google account did not return an email")

    user = None
    if google_sub:
        user = db.scalar(select(User).where(User.google_sub == google_sub))
    if not user:
        user = db.scalar(select(User).where(User.email == email))

    if not user:
        user = User(
            name=google_user.get("name") or email.split("@")[0],
            email=email,
            phone="9999999999",
            role="buyer",
            password_hash="",
            oauth_provider=payload.provider,
            google_sub=google_sub,
            is_active=True,
            seller_status="APPROVED",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is inactive")
        user.oauth_provider = payload.provider
        if google_sub and user.google_sub != google_sub:
            user.google_sub = google_sub
        if not user.name and google_user.get("name"):
            user.name = google_user["name"]
        db.commit()
    return AuthOut(user=user, token=create_session(db, user, user.role, user.email))


@app.post("/api/auth/logout")
def logout(session: AuthSession = Depends(require_current_session), db: Session = Depends(get_db)):
    revoke_session(db, session)
    return {"logged_out": True}


# ── Categories ────────────────────────────────────────────────────────────────
@app.get("/api/categories", response_model=list[CategoryOut])
def categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.name)).all()


# ── Users ─────────────────────────────────────────────────────────────────────
@app.get("/api/users", response_model=list[UserOut])
def users(_: User = Depends(require_admin_user), db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.id)).all()


@app.get("/api/users/{user_id}", response_model=UserOut)
def user_detail(user_id: int, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only view your own profile")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.patch("/api/account/profile", response_model=UserOut)
def update_profile(payload: AccountUpdateIn, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    if current_user.role == "admin":
        raise HTTPException(status_code=403, detail="Admin profile is managed from configuration")
    updates = payload.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@app.get("/api/account/addresses", response_model=AddressListOut)
def get_addresses(current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    items = db.scalars(
        select(UserAddress).where(UserAddress.user_id == current_user.id).order_by(UserAddress.is_default.desc(), UserAddress.id.asc())
    ).all()
    return AddressListOut(items=items)


@app.post("/api/account/addresses", response_model=AddressListOut)
def add_address(payload: AddressIn, current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    is_first = db.scalar(select(func.count(UserAddress.id)).where(UserAddress.user_id == current_user.id)) == 0
    address = UserAddress(user_id=current_user.id, is_default=is_first, **payload.model_dump())
    db.add(address)
    db.commit()
    db.refresh(address)
    if is_first:
        current_user.address_line = address.address_line
        current_user.city = address.city
        current_user.state = address.state
        current_user.pincode = address.pincode
        current_user.phone = address.phone
        db.commit()
    return get_addresses(current_user=current_user, db=db)


@app.patch("/api/account/addresses/{address_id}", response_model=AddressListOut)
def update_address(address_id: int, payload: AddressUpdateIn, current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    address = db.scalar(select(UserAddress).where(UserAddress.id == address_id, UserAddress.user_id == current_user.id))
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    updates = payload.model_dump(exclude_none=True)
    make_default = updates.pop("is_default", None)
    for field, value in updates.items():
        setattr(address, field, value)
    db.commit()
    if make_default:
        set_default_address(db, current_user.id, address.id)
        db.commit()
    default_address = db.scalar(select(UserAddress).where(UserAddress.user_id == current_user.id, UserAddress.is_default.is_(True)))
    if default_address:
        current_user.address_line = default_address.address_line
        current_user.city = default_address.city
        current_user.state = default_address.state
        current_user.pincode = default_address.pincode
        current_user.phone = default_address.phone
        db.commit()
    return get_addresses(current_user=current_user, db=db)


@app.delete("/api/account/addresses/{address_id}", response_model=AddressListOut)
def delete_address(address_id: int, current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    address = db.scalar(select(UserAddress).where(UserAddress.id == address_id, UserAddress.user_id == current_user.id))
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    deleted_default = address.is_default
    db.delete(address)
    db.commit()
    if deleted_default:
        next_address = db.scalar(select(UserAddress).where(UserAddress.user_id == current_user.id).order_by(UserAddress.id.asc()))
        if next_address:
            next_address.is_default = True
            db.commit()
    return get_addresses(current_user=current_user, db=db)


@app.get("/api/account/payment-methods", response_model=SavedPaymentMethodListOut)
def get_saved_payment_methods(current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    items = db.scalars(
        select(SavedPaymentMethod)
        .where(SavedPaymentMethod.user_id == current_user.id)
        .order_by(SavedPaymentMethod.is_default.desc(), SavedPaymentMethod.id.asc())
    ).all()
    return SavedPaymentMethodListOut(items=items)


@app.post("/api/account/payment-methods", response_model=SavedPaymentMethodListOut)
def add_saved_payment_method(payload: SavedPaymentMethodIn, current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    is_first = db.scalar(select(func.count(SavedPaymentMethod.id)).where(SavedPaymentMethod.user_id == current_user.id)) == 0
    method = SavedPaymentMethod(
        user_id=current_user.id,
        provider=payload.provider,
        label=payload.label,
        upi_id=payload.upi_id or "",
        card_last4=payload.card_last4 or "",
        is_default=payload.is_default or is_first,
    )
    db.add(method)
    db.commit()
    db.refresh(method)
    if method.is_default:
        set_default_payment(db, current_user.id, method.id)
        db.commit()
    return get_saved_payment_methods(current_user=current_user, db=db)


@app.delete("/api/account/payment-methods/{payment_id}", response_model=SavedPaymentMethodListOut)
def delete_saved_payment_method(payment_id: int, current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    method = db.scalar(
        select(SavedPaymentMethod).where(SavedPaymentMethod.id == payment_id, SavedPaymentMethod.user_id == current_user.id)
    )
    if not method:
        raise HTTPException(status_code=404, detail="Saved payment method not found")
    deleted_default = method.is_default
    db.delete(method)
    db.commit()
    if deleted_default:
        next_method = db.scalar(
            select(SavedPaymentMethod).where(SavedPaymentMethod.user_id == current_user.id).order_by(SavedPaymentMethod.id.asc())
        )
        if next_method:
            next_method.is_default = True
            db.commit()
    return get_saved_payment_methods(current_user=current_user, db=db)


@app.get("/api/account/recently-viewed", response_model=ProductListOut)
def get_recently_viewed(current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(RecentlyViewedProduct)
        .where(RecentlyViewedProduct.user_id == current_user.id)
        .options(
            selectinload(RecentlyViewedProduct.product).selectinload(Product.category),
            selectinload(RecentlyViewedProduct.product).selectinload(Product.images),
            selectinload(RecentlyViewedProduct.product).selectinload(Product.specs),
        )
        .order_by(RecentlyViewedProduct.viewed_at.desc(), RecentlyViewedProduct.id.desc())
    ).all()
    items = [row.product for row in rows if row.product and row.product.listing_status == "APPROVED"]
    return ProductListOut(items=items)


@app.get("/api/account/recommendations", response_model=ProductListOut)
def get_account_recommendations(current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    return ProductListOut(items=recommended_products_for_user(db, current_user.id))


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
    stmt = select(Product).options(*product_options()).join(Product.category).where(Product.listing_status == "APPROVED")
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
def product_detail(product_id: int, current_user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    product = db.scalar(select(Product).where(Product.id == product_id).options(*product_options()))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.listing_status != "APPROVED" and not current_user:
        raise HTTPException(status_code=404, detail="Product not found")
    if current_user and current_user.role != "admin" and product.listing_status != "APPROVED":
        if current_user.role != "seller" or product.seller_id != current_user.id:
            raise HTTPException(status_code=404, detail="Product not found")
    if current_user and current_user.role != "admin":
        record_recently_viewed(db, current_user.id, product.id)
    return product


# ── Cart ──────────────────────────────────────────────────────────────────────
@app.get("/api/cart", response_model=CartOut)
def get_cart(current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    items = load_cart(db, current_user.id)
    return CartOut(items=items, summary=cart_summary(items))


@app.post("/api/cart", response_model=CartOut)
def add_to_cart(payload: CartAdd, current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock <= 0:
        raise HTTPException(status_code=400, detail="Product is out of stock")
    item = db.scalar(
        select(CartItem).where(CartItem.user_id == current_user.id, CartItem.product_id == payload.product_id)
    )
    if item:
        item.quantity = min(item.quantity + payload.quantity, 10, product.stock)
    else:
        db.add(CartItem(user_id=current_user.id, product_id=payload.product_id, quantity=min(payload.quantity, product.stock)))
    db.commit()
    items = load_cart(db, current_user.id)
    return CartOut(items=items, summary=cart_summary(items))


@app.patch("/api/cart/{item_id}", response_model=CartOut)
def update_cart(item_id: int, payload: CartUpdate, current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    item = db.scalar(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == current_user.id).options(selectinload(CartItem.product))
    )
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    item.quantity = min(payload.quantity, item.product.stock)
    db.commit()
    items = load_cart(db, current_user.id)
    return CartOut(items=items, summary=cart_summary(items))


@app.delete("/api/cart/{item_id}", response_model=CartOut)
def remove_cart_item(item_id: int, current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    item = db.scalar(select(CartItem).where(CartItem.id == item_id, CartItem.user_id == current_user.id))
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()
    items = load_cart(db, current_user.id)
    return CartOut(items=items, summary=cart_summary(items))


# ── Wishlist ──────────────────────────────────────────────────────────────────
@app.get("/api/wishlist", response_model=WishlistOut)
def get_wishlist(current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(WishlistItem)
        .where(WishlistItem.user_id == current_user.id)
        .options(
            selectinload(WishlistItem.product).selectinload(Product.category),
            selectinload(WishlistItem.product).selectinload(Product.images),
            selectinload(WishlistItem.product).selectinload(Product.specs),
        )
    ).all()
    return WishlistOut(items=[row.product for row in rows])


@app.post("/api/wishlist/{product_id}", response_model=WishlistOut)
def toggle_wishlist(product_id: int, current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    row = db.scalar(
        select(WishlistItem).where(WishlistItem.user_id == current_user.id, WishlistItem.product_id == product_id)
    )
    if row:
        db.delete(row)
    else:
        db.add(WishlistItem(user_id=current_user.id, product_id=product_id))
    db.commit()
    return get_wishlist(current_user=current_user, db=db)


# ── Reviews ───────────────────────────────────────────────────────────────────
@app.get("/api/products/{product_id}/reviews", response_model=list[ReviewOut])
def product_reviews(product_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(Review).where(Review.product_id == product_id).options(selectinload(Review.user)).order_by(Review.id.desc())
    ).all()


@app.post("/api/reviews", response_model=ReviewOut)
def add_review(payload: ReviewIn, current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    verified = db.scalar(
        select(OrderItem).join(Order).where(Order.user_id == current_user.id, OrderItem.product_id == payload.product_id)
    ) is not None
    review = Review(
        user_id=current_user.id,
        product_id=payload.product_id,
        rating=payload.rating,
        comment=payload.comment,
        verified_purchase=verified,
    )
    db.add(review)
    db.commit()
    sync_review_stats(db, payload.product_id)
    db.commit()
    db.refresh(review)
    return db.scalar(select(Review).where(Review.id == review.id).options(selectinload(Review.user)))


# ── Razorpay: Create Order ────────────────────────────────────────────────────
@app.post("/api/razorpay/create-order", response_model=RazorpayOrderOut)
def razorpay_create_order(current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    """Create a Razorpay order for the current cart total."""
    if not rzp_client:
        raise HTTPException(status_code=503, detail="Razorpay not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to .env")

    items = load_cart(db, current_user.id)
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
def place_order(payload: CheckoutIn, current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    items = load_cart(db, current_user.id)
    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    for item in items:
        if item.quantity > item.product.stock:
            raise HTTPException(status_code=400, detail=f"Only {item.product.stock} units left for {item.product.title}")

    summary = cart_summary(items)
    order = Order(
        order_number=f"OD{uuid4().hex[:12].upper()}",
        user_id=current_user.id,
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
        refund_status="NONE",
    )

    for item in items:
        order.items.append(
            OrderItem(
                product_id=item.product_id,
                title=item.product.title,
                price=item.product.price,
                quantity=item.quantity,
                seller_id=item.product.seller_id,
                status="PLACED",
                tracking_status="Placed",
            )
        )
        item.product.stock -= item.quantity
        db.delete(item)

    db.add(order)
    db.commit()
    db.refresh(order)

    # Reload order with items for email
    full_order = db.scalar(select(Order).where(Order.id == order.id).options(selectinload(Order.items)))
    sync_order_status(full_order)
    db.commit()
    db.refresh(full_order)
    create_payment_transaction(db, full_order)
    maybe_create_fraud_flag(db, full_order)

    # Send confirmation email
    if current_user and current_user.email:
        send_order_email(
            to_email=current_user.email,
            order_number=full_order.order_number,
            customer_name=full_order.customer_name,
            total=full_order.total_amount,
            items=full_order.items,
            payment_method=full_order.payment_method,
        )

    return full_order


@app.get("/api/orders", response_model=list[OrderOut])
def order_history(current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Order).where(Order.user_id == current_user.id).options(selectinload(Order.items)).order_by(Order.id.desc())
    ).all()


@app.get("/api/orders/{order_number}", response_model=OrderOut)
def order_by_number(order_number: str, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    order = db.scalar(select(Order).where(Order.order_number == order_number).options(selectinload(Order.items)))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user.role != "admin" and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only view your own orders")
    return order


@app.post("/api/orders/{order_number}/reorder", response_model=CartOut)
def reorder_items(order_number: str, current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    order = db.scalar(
        select(Order).where(Order.order_number == order_number, Order.user_id == current_user.id).options(selectinload(Order.items))
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    for item in order.items:
        product = db.get(Product, item.product_id)
        if not product or product.stock <= 0 or product.listing_status != "APPROVED":
            continue
        existing = db.scalar(
            select(CartItem).where(CartItem.user_id == current_user.id, CartItem.product_id == item.product_id)
        )
        reorder_qty = min(item.quantity, product.stock, 10)
        if existing:
            existing.quantity = min(existing.quantity + reorder_qty, product.stock, 10)
        else:
            db.add(CartItem(user_id=current_user.id, product_id=item.product_id, quantity=reorder_qty))
    db.commit()
    items = load_cart(db, current_user.id)
    return CartOut(items=items, summary=cart_summary(items))


@app.get("/api/complaints", response_model=ComplaintListOut)
def get_complaints(current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    stmt = select(Complaint).options(selectinload(Complaint.user)).order_by(Complaint.id.desc())
    if current_user.role != "admin":
        stmt = stmt.where(Complaint.user_id == current_user.id)
    return ComplaintListOut(items=db.scalars(stmt).all())


@app.post("/api/complaints", response_model=ComplaintOut)
def create_complaint(payload: ComplaintIn, current_user: User = Depends(require_customer_user), db: Session = Depends(get_db)):
    if payload.order_id:
        order = db.get(Order, payload.order_id)
        if not order or order.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Order not found")
    if payload.product_id:
        product = db.get(Product, payload.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
    complaint = Complaint(user_id=current_user.id, **payload.model_dump())
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return db.scalar(select(Complaint).where(Complaint.id == complaint.id).options(selectinload(Complaint.user)))


# ── Seller Dashboard ──────────────────────────────────────────────────────────
@app.post("/api/seller/products", response_model=ProductOut)
def create_seller_product(payload: SellerProductIn, current_user: User = Depends(require_seller_user), db: Session = Depends(get_db)):
    category = db.scalar(select(Category).where(Category.slug == payload.category_slug))
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    product = Product(
        category_id=category.id,
        title=payload.title,
        brand=payload.brand,
        description=payload.description,
        price=payload.price,
        mrp=payload.mrp,
        stock=payload.stock,
        assured=payload.assured,
        seller_id=current_user.id,
        listing_status="PENDING",
        approval_note="Awaiting admin approval",
        low_stock_threshold=payload.low_stock_threshold,
    )
    product.images = [
        ProductImage(url=url, alt=f"{payload.title} image {index + 1}")
        for index, url in enumerate(payload.images or [])
    ]
    product.specs = [ProductSpec(name=spec.name, value=spec.value) for spec in payload.specs]
    db.add(product)
    db.commit()
    db.refresh(product)
    return db.scalar(select(Product).where(Product.id == product.id).options(*product_options()))


@app.patch("/api/seller/products/{product_id}", response_model=ProductOut)
def update_seller_product(
    product_id: int,
    payload: SellerProductUpdateIn,
    current_user: User = Depends(require_seller_user),
    db: Session = Depends(get_db),
):
    product = db.scalar(select(Product).where(Product.id == product_id, Product.seller_id == current_user.id).options(*product_options()))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    updates = payload.model_dump(exclude_none=True)
    category_slug = updates.pop("category_slug", None)
    images = updates.pop("images", None)
    specs = updates.pop("specs", None)
    if category_slug:
        category = db.scalar(select(Category).where(Category.slug == category_slug))
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        product.category_id = category.id
    for field, value in updates.items():
        setattr(product, field, value)
    if images is not None:
        product.images = [ProductImage(url=url, alt=f"{product.title} image {index + 1}") for index, url in enumerate(images)]
    if specs is not None:
        product.specs = [ProductSpec(name=spec["name"], value=spec["value"]) if isinstance(spec, dict) else ProductSpec(name=spec.name, value=spec.value) for spec in specs]
    if product.listing_status == "REJECTED":
        product.listing_status = "PENDING"
        product.approval_note = "Updated by seller and awaiting review"
    db.commit()
    return db.scalar(select(Product).where(Product.id == product.id).options(*product_options()))


@app.delete("/api/seller/products/{product_id}")
def delete_seller_product(product_id: int, current_user: User = Depends(require_seller_user), db: Session = Depends(get_db)):
    product = db.scalar(select(Product).where(Product.id == product_id, Product.seller_id == current_user.id))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"deleted": True}


@app.get("/api/seller/reviews", response_model=list[ReviewOut])
def seller_reviews(current_user: User = Depends(require_seller_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Review)
        .join(Review.product)
        .where(Product.seller_id == current_user.id)
        .options(selectinload(Review.user), selectinload(Review.product))
        .order_by(Review.id.desc())
    ).all()


@app.patch("/api/seller/reviews/{review_id}/response", response_model=ReviewOut)
def respond_to_review(
    review_id: int,
    payload: ReviewResponseIn,
    current_user: User = Depends(require_seller_user),
    db: Session = Depends(get_db),
):
    review = db.scalar(
        select(Review)
        .join(Review.product)
        .where(Review.id == review_id, Product.seller_id == current_user.id)
        .options(selectinload(Review.user))
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    review.seller_response = payload.response
    review.seller_responded_at = datetime.utcnow()
    db.commit()
    return db.scalar(select(Review).where(Review.id == review.id).options(selectinload(Review.user)))


@app.patch("/api/seller/orders/{order_id}/items/{item_id}/status", response_model=OrderOut)
def update_seller_order_item_status(
    order_id: int,
    item_id: int,
    payload: OrderStatusUpdateIn,
    current_user: User = Depends(require_seller_user),
    db: Session = Depends(get_db),
):
    order = db.scalar(select(Order).where(Order.id == order_id).options(selectinload(Order.items)))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    item = next((line for line in order.items if line.id == item_id and line.seller_id == current_user.id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")
    item.status = payload.status
    item.tracking_status = TRACKING_COPY[payload.status]
    sync_order_status(order)
    db.commit()
    db.refresh(order)
    return seller_order_payload(order, current_user.id)


@app.get("/api/seller/{seller_id}/dashboard", response_model=SellerDashboardOut)
def seller_dashboard(seller_id: int, current_user: User = Depends(require_user), db: Session = Depends(get_db)):
    if current_user.role not in {"seller", "admin"}:
        raise HTTPException(status_code=403, detail="Seller access required")
    if current_user.role == "seller":
        require_seller_user(current_user)
    if current_user.role == "seller" and current_user.id != seller_id:
        raise HTTPException(status_code=403, detail="You can only view your own seller dashboard")
    seller = db.get(User, seller_id)
    if not seller or seller.role != "seller":
        raise HTTPException(status_code=404, detail="Seller not found")

    prods = db.scalars(select(Product).where(Product.seller_id == seller_id).options(*product_options()).order_by(Product.id)).all()
    raw_orders = db.scalars(
        select(Order).join(Order.items).where(OrderItem.seller_id == seller_id).options(selectinload(Order.items)).order_by(Order.id.desc())
    ).unique().all()
    ords = [seller_order_payload(order, seller_id) for order in raw_orders]
    seller_items = [item for order in raw_orders for item in order.items if item.seller_id == seller_id]
    product_sales: dict[int, dict] = defaultdict(lambda: {"title": "", "units_sold": 0, "revenue": 0.0})
    product_lookup = {product.id: product for product in prods}
    for item in seller_items:
        sale = product_sales[item.product_id]
        sale["title"] = product_lookup.get(item.product_id).title if product_lookup.get(item.product_id) else item.title
        sale["units_sold"] += item.quantity
        sale["revenue"] += item.quantity * item.price
    top_products = [
        {
            "product_id": product_id,
            "title": data["title"],
            "units_sold": data["units_sold"],
            "revenue": round(data["revenue"], 2),
        }
        for product_id, data in sorted(product_sales.items(), key=lambda entry: (-entry[1]["units_sold"], -entry[1]["revenue"]))[:5]
    ]
    reviews = db.scalars(
        select(Review)
        .join(Review.product)
        .where(Product.seller_id == seller_id)
        .options(selectinload(Review.user), selectinload(Review.product))
        .order_by(Review.id.desc())
    ).all()
    stats = SellerStatsOut(
        product_count=len(prods),
        units_sold=sum(item.quantity for item in seller_items),
        revenue=round(sum(item.price * item.quantity for item in seller_items), 2),
        order_count=len(ords),
        low_stock_count=sum(1 for product in prods if product.stock <= product.low_stock_threshold),
        pending_products=sum(1 for product in prods if product.listing_status == "PENDING"),
    )
    return SellerDashboardOut(seller=seller, products=prods, orders=ords, reviews=reviews, stats=stats, top_products=top_products)


# ── Admin Dashboard ───────────────────────────────────────────────────────────
@app.get("/api/admin/dashboard", response_model=AdminDashboardOut)
def admin_dashboard(_: User = Depends(require_admin_user), db: Session = Depends(get_db)):
    all_users = db.scalars(select(User).order_by(User.id)).all()
    all_products = db.scalars(select(Product).options(*product_options()).order_by(Product.id)).all()
    all_orders = db.scalars(select(Order).options(selectinload(Order.items)).order_by(Order.id.desc())).all()
    transactions = db.scalars(select(PaymentTransaction).order_by(PaymentTransaction.id.desc())).all()
    complaints = db.scalars(select(Complaint).options(selectinload(Complaint.user)).order_by(Complaint.id.desc())).all()
    fraud_flags = db.scalars(select(FraudFlag).order_by(FraudFlag.id.desc())).all()

    total_revenue = round(sum(o.total_amount for o in all_orders), 2)
    paid_orders = [o for o in all_orders if o.payment_status == "PAID"]
    active_users = [user for user in all_users if user.is_active]
    pending_sellers = [user for user in all_users if user.role == "seller" and user.seller_status == "PENDING"]
    pending_products = [product for product in all_products if product.listing_status == "PENDING"]
    refunded_transactions = [transaction for transaction in transactions if transaction.refund_status == "REFUNDED"]

    now = datetime.utcnow()
    current_window_start = now - timedelta(days=7)
    previous_window_start = now - timedelta(days=14)
    users_current = sum(1 for user in all_users if getattr(user, "created_at", None) and user.created_at >= current_window_start)
    users_previous = sum(
        1
        for user in all_users
        if getattr(user, "created_at", None) and previous_window_start <= user.created_at < current_window_start
    )
    orders_current = [order for order in all_orders if order.created_at >= current_window_start]
    orders_previous = [order for order in all_orders if previous_window_start <= order.created_at < current_window_start]
    revenue_current = sum(order.total_amount for order in orders_current)
    revenue_previous = sum(order.total_amount for order in orders_previous)
    growth = GrowthStatsOut(
        users_last_7_days=users_current,
        orders_last_7_days=len(orders_current),
        revenue_last_7_days=round(revenue_current, 2),
        users_growth_percent=growth_percent(users_current, users_previous),
        orders_growth_percent=growth_percent(len(orders_current), len(orders_previous)),
        revenue_growth_percent=growth_percent(revenue_current, revenue_previous),
    )

    stats = AdminStatsOut(
        total_users=len(all_users),
        active_users=len(active_users),
        total_products=len(all_products),
        total_orders=len(all_orders),
        total_revenue=total_revenue,
        paid_orders=len(paid_orders),
        pending_orders=len(all_orders) - len(paid_orders),
        pending_sellers=len(pending_sellers),
        pending_products=len(pending_products),
        refunded_transactions=len(refunded_transactions),
    )

    return AdminDashboardOut(
        stats=stats,
        growth=growth,
        users=all_users,
        products=all_products,
        orders=all_orders,
        transactions=transactions,
        complaints=complaints,
        fraud_flags=fraud_flags,
    )


@app.patch("/api/admin/users/{user_id}", response_model=UserOut)
def admin_update_user(
    user_id: int,
    payload: AdminUserUpdateIn,
    _: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updates = payload.model_dump(exclude_none=True)
    if "role" in updates and updates["role"] == "seller" and user.role != "seller" and "seller_status" not in updates:
        updates["seller_status"] = "PENDING"
    for field, value in updates.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@app.patch("/api/admin/products/{product_id}", response_model=ProductOut)
def admin_moderate_product(
    product_id: int,
    payload: ProductModerationIn,
    _: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    product = db.scalar(select(Product).where(Product.id == product_id).options(*product_options()))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.listing_status = payload.listing_status
    product.approval_note = payload.approval_note or ""
    db.commit()
    return db.scalar(select(Product).where(Product.id == product.id).options(*product_options()))


@app.patch("/api/admin/transactions/{transaction_id}", response_model=PaymentTransactionOut)
def admin_update_transaction(
    transaction_id: int,
    payload: RefundUpdateIn,
    _: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    transaction = db.get(PaymentTransaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    transaction.refund_status = payload.refund_status
    if payload.refund_status == "REFUNDED":
        transaction.status = "REFUNDED"
        order = db.get(Order, transaction.order_id)
        if order:
            order.payment_status = "REFUNDED"
            order.refund_status = "REFUNDED"
    db.commit()
    db.refresh(transaction)
    return transaction


@app.patch("/api/admin/complaints/{complaint_id}", response_model=ComplaintOut)
def admin_update_complaint(
    complaint_id: int,
    payload: ComplaintUpdateIn,
    _: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    complaint = db.scalar(select(Complaint).where(Complaint.id == complaint_id).options(selectinload(Complaint.user)))
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    complaint.status = payload.status
    complaint.resolution_note = payload.resolution_note or complaint.resolution_note
    db.commit()
    db.refresh(complaint)
    return db.scalar(select(Complaint).where(Complaint.id == complaint.id).options(selectinload(Complaint.user)))


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, _: User = Depends(require_admin_user), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"deleted": True}


@app.delete("/api/admin/products/{product_id}")
def admin_delete_product(product_id: int, _: User = Depends(require_admin_user), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"deleted": True}
