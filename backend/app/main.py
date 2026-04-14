import os
from hashlib import sha256
from uuid import uuid4

import requests
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, select
from sqlalchemy.orm import Session, selectinload

from .database import Base, engine, get_db
from .models import CartItem, Category, Order, OrderItem, Product, Review, User, WishlistItem
from .schemas import (
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
    SellerDashboardOut,
    SellerStatsOut,
    SignupIn,
    UserOut,
    WishlistOut,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Flipkart Clone API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_USER_ID = 1
DEFAULT_SELLER_ID = 2
FLASK_NOTIFICATION_URL = os.getenv("FLASK_NOTIFICATION_URL", "http://localhost:5001/notifications/order")


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


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "fastapi"}


def hash_password(password: str) -> str:
    return sha256(password.encode("utf-8")).hexdigest()


def token_for(user: User) -> str:
    return f"demo-token-{user.id}-{uuid4().hex[:8]}"


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


@app.get("/api/categories", response_model=list[CategoryOut])
def categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.name)).all()


@app.get("/api/users", response_model=list[UserOut])
def users(db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.id)).all()


@app.get("/api/users/{user_id}", response_model=UserOut)
def user_detail(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


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
        select(CartItem).where(
            CartItem.user_id == DEFAULT_USER_ID,
            CartItem.product_id == payload.product_id,
        )
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
        select(CartItem)
        .where(CartItem.id == item_id, CartItem.user_id == DEFAULT_USER_ID)
        .options(selectinload(CartItem.product))
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
        select(WishlistItem).where(
            WishlistItem.user_id == DEFAULT_USER_ID,
            WishlistItem.product_id == product_id,
        )
    )
    if row:
        db.delete(row)
    else:
        db.add(WishlistItem(user_id=DEFAULT_USER_ID, product_id=product_id))
    db.commit()
    return get_wishlist(db)


@app.get("/api/products/{product_id}/reviews", response_model=list[ReviewOut])
def product_reviews(product_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(Review)
        .where(Review.product_id == product_id)
        .options(selectinload(Review.user))
        .order_by(Review.id.desc())
    ).all()


@app.post("/api/reviews", response_model=ReviewOut)
def add_review(payload: ReviewIn, db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    verified = db.scalar(
        select(OrderItem)
        .join(Order)
        .where(
            Order.user_id == DEFAULT_USER_ID,
            OrderItem.product_id == payload.product_id,
        )
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
        payment_reference=f"PAY{uuid4().hex[:10].upper()}",
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
    try:
        requests.post(
            FLASK_NOTIFICATION_URL,
            json={
                "order_number": order.order_number,
                "total_amount": order.total_amount,
                "payment_method": order.payment_method,
            },
            timeout=2,
        )
    except requests.RequestException:
        pass
    return db.scalar(select(Order).where(Order.id == order.id).options(selectinload(Order.items)))


@app.get("/api/orders", response_model=list[OrderOut])
def order_history(db: Session = Depends(get_db)):
    return db.scalars(
        select(Order)
        .where(Order.user_id == DEFAULT_USER_ID)
        .options(selectinload(Order.items))
        .order_by(Order.id.desc())
    ).all()


@app.get("/api/orders/{order_number}", response_model=OrderOut)
def order_by_number(order_number: str, db: Session = Depends(get_db)):
    order = db.scalar(select(Order).where(Order.order_number == order_number).options(selectinload(Order.items)))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/api/seller/{seller_id}/dashboard", response_model=SellerDashboardOut)
def seller_dashboard(seller_id: int, db: Session = Depends(get_db)):
    seller = db.get(User, seller_id)
    if not seller or seller.role != "seller":
        raise HTTPException(status_code=404, detail="Seller not found")

    products = db.scalars(
        select(Product)
        .where(Product.seller_id == seller_id)
        .options(*product_options())
        .order_by(Product.id)
    ).all()
    orders = db.scalars(
        select(Order)
        .join(Order.items)
        .where(OrderItem.seller_id == seller_id)
        .options(selectinload(Order.items))
        .order_by(Order.id.desc())
    ).unique().all()
    seller_items = [item for order in orders for item in order.items if item.seller_id == seller_id]
    stats = SellerStatsOut(
        product_count=len(products),
        units_sold=sum(item.quantity for item in seller_items),
        revenue=round(sum(item.price * item.quantity for item in seller_items), 2),
        order_count=len(orders),
    )
    return SellerDashboardOut(seller=seller, products=products, orders=orders, stats=stats)
