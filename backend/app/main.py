import os
from uuid import uuid4

import requests
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, select
from sqlalchemy.orm import Session, selectinload

from .database import Base, engine, get_db
from .models import CartItem, Category, Order, OrderItem, Product, User
from .schemas import (
    CartAdd,
    CartOut,
    CartSummaryOut,
    CartUpdate,
    CategoryOut,
    CheckoutIn,
    OrderOut,
    ProductOut,
    SellerDashboardOut,
    SellerStatsOut,
    UserOut,
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
        "ALTER TABLE products ADD COLUMN seller_id INT DEFAULT 2",
        "ALTER TABLE orders ADD COLUMN payment_method VARCHAR(40) DEFAULT 'UPI'",
        "ALTER TABLE orders ADD COLUMN payment_status VARCHAR(40) DEFAULT 'PAID'",
        "ALTER TABLE orders ADD COLUMN payment_reference VARCHAR(80) DEFAULT ''",
        "ALTER TABLE order_items ADD COLUMN seller_id INT DEFAULT 2",
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
def products(search: str | None = Query(default=None), category: str | None = Query(default=None), db: Session = Depends(get_db)):
    stmt = select(Product).options(*product_options()).join(Product.category)
    if search:
        stmt = stmt.where(Product.title.ilike(f"%{search}%"))
    if category and category != "all":
        stmt = stmt.where(Category.slug == category)
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
