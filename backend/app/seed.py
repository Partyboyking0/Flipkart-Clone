import hashlib
import os

from sqlalchemy import text

from .database import Base, SessionLocal, engine
from .models import (
    Category,
    Complaint,
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
)


PRODUCTS = [
    {
        "category": ("Mobiles", "mobiles"),
        "title": "Motorola Edge 50 Fusion (Marshmallow Blue, 128 GB)",
        "brand": "Motorola",
        "description": "A slim 5G smartphone with a curved pOLED display, fast charging, and a dependable camera setup for everyday photography.",
        "price": 22999,
        "mrp": 27999,
        "rating": 4.4,
        "reviews": 18452,
        "stock": 18,
        "images": [
            "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1580910051074-3eb694886505?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"RAM": "8 GB", "Storage": "128 GB", "Display": "6.7 inch pOLED", "Battery": "5000 mAh"},
    },
    {
        "category": ("Electronics", "electronics"),
        "title": "Sony WH-CH720N Wireless Noise Cancelling Headphones",
        "brand": "Sony",
        "description": "Lightweight wireless headphones with active noise cancellation, rich sound, and long battery life.",
        "price": 8990,
        "mrp": 14990,
        "rating": 4.3,
        "reviews": 7350,
        "stock": 25,
        "images": [
            "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1484704849700-f032a568e944?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Playback": "Up to 35 hours", "Connectivity": "Bluetooth 5.2", "Charging": "USB Type-C"},
    },
    {
        "category": ("Fashion", "fashion"),
        "title": "Roadster Men Solid Casual Jacket",
        "brand": "Roadster",
        "description": "A regular-fit casual jacket designed for everyday layering and a clean streetwear look.",
        "price": 1499,
        "mrp": 3999,
        "rating": 4.1,
        "reviews": 2201,
        "stock": 40,
        "images": [
            "https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1520975954732-35dd22299614?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Fabric": "Polyester Blend", "Fit": "Regular", "Pattern": "Solid"},
    },
    {
        "category": ("Home", "home"),
        "title": "Prestige Electric Kettle 1.5 L",
        "brand": "Prestige",
        "description": "Fast boiling electric kettle with auto cut-off, cool-touch handle, and stainless steel body.",
        "price": 799,
        "mrp": 1495,
        "rating": 4.2,
        "reviews": 10892,
        "stock": 60,
        "images": [
            "https://images.unsplash.com/photo-1594213114663-d94db9b17125?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1571552879083-e93b6ea70d1d?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Capacity": "1.5 L", "Power": "1500 W", "Material": "Stainless Steel"},
    },
    {
        "category": ("Appliances", "appliances"),
        "title": "Samsung 253 L Frost Free Double Door Refrigerator",
        "brand": "Samsung",
        "description": "Energy efficient double door refrigerator with digital inverter compressor and spacious storage.",
        "price": 27490,
        "mrp": 36999,
        "rating": 4.5,
        "reviews": 4160,
        "stock": 12,
        "images": [
            "https://images.unsplash.com/photo-1571175443880-49e1d25b2bc5?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1584568694244-14fbdf83bd30?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Capacity": "253 L", "Type": "Double Door", "Compressor": "Digital Inverter"},
    },
    {
        "category": ("Grocery", "grocery"),
        "title": "Tata Sampann Unpolished Toor Dal 1 kg",
        "brand": "Tata Sampann",
        "description": "Protein-rich unpolished toor dal for everyday Indian cooking.",
        "price": 169,
        "mrp": 220,
        "rating": 4.4,
        "reviews": 5291,
        "stock": 100,
        "images": [
            "https://images.unsplash.com/photo-1615485500704-8e990f9900f7?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Weight": "1 kg", "Type": "Toor Dal", "Diet": "Vegetarian"},
    },
    {
        "category": ("Mobiles", "mobiles"),
        "title": "Apple iPhone 15 (Black, 128 GB)",
        "brand": "Apple",
        "description": "A premium smartphone with Dynamic Island, A16 Bionic performance, and advanced dual cameras.",
        "price": 64999,
        "mrp": 79900,
        "rating": 4.6,
        "reviews": 12840,
        "stock": 14,
        "images": [
            "https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1695048133141-b7e5341d4573?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Storage": "128 GB", "Display": "6.1 inch Super Retina XDR", "Processor": "A16 Bionic"},
    },
    {
        "category": ("Electronics", "electronics"),
        "title": "boAt Airdopes 141 Bluetooth Earbuds",
        "brand": "boAt",
        "description": "Compact true wireless earbuds with low-latency audio, fast charging, and clear calling.",
        "price": 1299,
        "mrp": 4490,
        "rating": 4.0,
        "reviews": 34291,
        "stock": 80,
        "images": [
            "https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Playback": "Up to 42 hours", "Water Resistance": "IPX4", "Charging": "USB Type-C"},
    },
    {
        "category": ("Fashion", "fashion"),
        "title": "Nike Revolution 7 Running Shoes",
        "brand": "Nike",
        "description": "Lightweight running shoes with breathable mesh and cushioned daily comfort.",
        "price": 3295,
        "mrp": 4995,
        "rating": 4.2,
        "reviews": 6810,
        "stock": 32,
        "images": [
            "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1608231387042-66d1773070a5?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Type": "Running Shoes", "Upper": "Mesh", "Sole": "Rubber"},
    },
    {
        "category": ("Home", "home"),
        "title": "Wakefit Orthopedic Memory Foam Mattress",
        "brand": "Wakefit",
        "description": "A medium-firm orthopedic mattress with pressure relief and breathable comfort layers.",
        "price": 8999,
        "mrp": 15999,
        "rating": 4.4,
        "reviews": 9120,
        "stock": 19,
        "images": [
            "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1616594039964-ae9021a400a0?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Size": "Queen", "Firmness": "Medium Firm", "Warranty": "10 years"},
    },
    {
        "category": ("Appliances", "appliances"),
        "title": "LG 7 kg 5 Star Front Load Washing Machine",
        "brand": "LG",
        "description": "Energy efficient front load washing machine with inverter motor and multiple wash programs.",
        "price": 30990,
        "mrp": 42990,
        "rating": 4.5,
        "reviews": 3188,
        "stock": 11,
        "images": [
            "https://images.unsplash.com/photo-1626806819282-2c1dc01a5e0c?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1610557892470-55d9e80c0bce?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Capacity": "7 kg", "Energy Rating": "5 Star", "Motor": "Inverter"},
    },
    {
        "category": ("Grocery", "grocery"),
        "title": "Fortune Sunlite Refined Sunflower Oil 1 L",
        "brand": "Fortune",
        "description": "Light refined sunflower oil suitable for everyday Indian cooking.",
        "price": 145,
        "mrp": 180,
        "rating": 4.3,
        "reviews": 15120,
        "stock": 120,
        "images": [
            "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1620706857370-e1b9770e8bb1?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Volume": "1 L", "Type": "Sunflower Oil", "Diet": "Vegetarian"},
    },
    {
        "category": ("Mobiles", "mobiles"),
        "title": "Nothing Phone (2a) 5G (Milk, 256 GB)",
        "brand": "Nothing",
        "description": "A clean Android smartphone with Glyph design, smooth AMOLED display, and balanced all-day performance.",
        "price": 25999,
        "mrp": 29999,
        "rating": 4.4,
        "reviews": 8450,
        "stock": 26,
        "images": [
            "https://images.unsplash.com/photo-1512499617640-c2f999098c01?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1565849904461-04a58ad377e0?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"RAM": "12 GB", "Storage": "256 GB", "Display": "6.7 inch AMOLED", "Battery": "5000 mAh"},
    },
    {
        "category": ("Mobiles", "mobiles"),
        "title": "OnePlus Nord CE 4 (Dark Chrome, 128 GB)",
        "brand": "OnePlus",
        "description": "A fast-charging 5G phone with a fluid AMOLED display and dependable day-to-day performance.",
        "price": 24999,
        "mrp": 27999,
        "rating": 4.3,
        "reviews": 6240,
        "stock": 21,
        "images": [
            "https://images.unsplash.com/photo-1583573636246-18cb2246697f?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"RAM": "8 GB", "Storage": "128 GB", "Display": "6.7 inch AMOLED", "Charging": "100 W SUPERVOOC"},
    },
    {
        "category": ("Electronics", "electronics"),
        "title": "JBL Flip 6 Portable Bluetooth Speaker",
        "brand": "JBL",
        "description": "A compact waterproof Bluetooth speaker with punchy bass and solid battery life for indoor and outdoor listening.",
        "price": 8999,
        "mrp": 11999,
        "rating": 4.5,
        "reviews": 4180,
        "stock": 34,
        "images": [
            "https://images.unsplash.com/photo-1545454675-3531b543be5d?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1589003077984-894e133dabab?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Output": "30 W", "Battery": "Up to 12 hours", "Water Resistance": "IP67"},
    },
    {
        "category": ("Electronics", "electronics"),
        "title": "Kindle Paperwhite 11th Gen E-Reader",
        "brand": "Amazon",
        "description": "A glare-free e-reader with adjustable warm light and long battery life for comfortable reading.",
        "price": 14999,
        "mrp": 16999,
        "rating": 4.6,
        "reviews": 3025,
        "stock": 17,
        "images": [
            "https://images.unsplash.com/photo-1544717305-2782549b5136?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Display": "6.8 inch glare-free", "Storage": "16 GB", "Battery": "Up to 10 weeks"},
    },
    {
        "category": ("Fashion", "fashion"),
        "title": "Puma Essentials Men Logo Hoodie",
        "brand": "Puma",
        "description": "A soft fleece hoodie for daily comfort with ribbed hems and an easy casual fit.",
        "price": 2199,
        "mrp": 3999,
        "rating": 4.3,
        "reviews": 2811,
        "stock": 46,
        "images": [
            "https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Fabric": "Cotton Blend", "Fit": "Regular", "Sleeve": "Full Sleeve"},
    },
    {
        "category": ("Fashion", "fashion"),
        "title": "Levi's 512 Slim Tapered Jeans",
        "brand": "Levi's",
        "description": "Everyday slim tapered jeans with stretch comfort and a clean modern silhouette.",
        "price": 2799,
        "mrp": 4999,
        "rating": 4.2,
        "reviews": 3920,
        "stock": 38,
        "images": [
            "https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Fit": "Slim Tapered", "Fabric": "Denim Stretch", "Rise": "Mid Rise"},
    },
    {
        "category": ("Home", "home"),
        "title": "Cello Stainless Steel Insulated Flask 1 L",
        "brand": "Cello",
        "description": "Vacuum insulated flask that keeps beverages hot or cold for long hours and is easy to carry.",
        "price": 899,
        "mrp": 1499,
        "rating": 4.3,
        "reviews": 5770,
        "stock": 72,
        "images": [
            "https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1514228742587-6b1558fcf93a?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Capacity": "1 L", "Material": "Stainless Steel", "Insulation": "Vacuum"},
    },
    {
        "category": ("Home", "home"),
        "title": "Sleepyhead Office Chair with Lumbar Support",
        "brand": "Sleepyhead",
        "description": "Ergonomic office chair with breathable mesh back, lumbar support, and adjustable height.",
        "price": 6499,
        "mrp": 9999,
        "rating": 4.1,
        "reviews": 2140,
        "stock": 23,
        "images": [
            "https://images.unsplash.com/photo-1505843513577-22bb7d21e455?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1592078615290-033ee584e267?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Type": "Office Chair", "Support": "Lumbar Support", "Material": "Mesh Back"},
    },
    {
        "category": ("Appliances", "appliances"),
        "title": "Philips Air Fryer NA120/00 4.2 L",
        "brand": "Philips",
        "description": "Large-capacity air fryer for healthier frying, roasting, and baking with rapid air technology.",
        "price": 6999,
        "mrp": 10995,
        "rating": 4.5,
        "reviews": 4678,
        "stock": 29,
        "images": [
            "https://images.unsplash.com/photo-1585515656336-9d7d7bfb2aa5?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Capacity": "4.2 L", "Power": "1400 W", "Technology": "Rapid Air"},
    },
    {
        "category": ("Appliances", "appliances"),
        "title": "Voltas 1.5 Ton 3 Star Inverter Split AC",
        "brand": "Voltas",
        "description": "Inverter split AC with fast cooling, copper condenser, and efficient summer performance.",
        "price": 34990,
        "mrp": 46990,
        "rating": 4.2,
        "reviews": 2895,
        "stock": 10,
        "images": [
            "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1621905252507-b35492cc74b4?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Capacity": "1.5 Ton", "Energy Rating": "3 Star", "Condenser": "Copper"},
    },
    {
        "category": ("Grocery", "grocery"),
        "title": "Aashirvaad Superior MP Atta 5 kg",
        "brand": "Aashirvaad",
        "description": "Whole wheat atta milled for soft rotis and everyday family meals.",
        "price": 289,
        "mrp": 355,
        "rating": 4.5,
        "reviews": 17810,
        "stock": 140,
        "images": [
            "https://images.unsplash.com/photo-1603048297172-c92544798d5a?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1586444248902-2f64eddc13df?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Weight": "5 kg", "Type": "Whole Wheat Atta", "Diet": "Vegetarian"},
    },
    {
        "category": ("Grocery", "grocery"),
        "title": "Taj Mahal Tea 1 kg",
        "brand": "Taj Mahal",
        "description": "Premium tea blend with rich aroma and full-bodied flavor for daily chai.",
        "price": 549,
        "mrp": 690,
        "rating": 4.4,
        "reviews": 9630,
        "stock": 88,
        "images": [
            "https://images.unsplash.com/photo-1597481499750-3e6b22637e12?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=900&q=80",
        ],
        "specs": {"Weight": "1 kg", "Type": "Black Tea", "Flavor": "Strong Aroma"},
    },
]
PBKDF2_ITERATIONS = 390000


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def run():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
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
            "CREATE TABLE IF NOT EXISTS user_addresses (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, label VARCHAR(60) DEFAULT 'Home', customer_name VARCHAR(160) NOT NULL, phone VARCHAR(20) NOT NULL, address_line VARCHAR(255) NOT NULL, city VARCHAR(100) NOT NULL, state VARCHAR(100) NOT NULL, pincode VARCHAR(12) NOT NULL, is_default BOOLEAN DEFAULT FALSE, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_user_addresses_user (user_id), CONSTRAINT fk_user_addresses_user FOREIGN KEY (user_id) REFERENCES users(id))",
            "CREATE TABLE IF NOT EXISTS saved_payment_methods (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, provider VARCHAR(40) NOT NULL, label VARCHAR(80) NOT NULL, upi_id VARCHAR(120) DEFAULT '', card_last4 VARCHAR(4) DEFAULT '', is_default BOOLEAN DEFAULT FALSE, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_saved_payment_user (user_id), CONSTRAINT fk_saved_payment_user FOREIGN KEY (user_id) REFERENCES users(id))",
            "CREATE TABLE IF NOT EXISTS recently_viewed_products (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, product_id INT NOT NULL, viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_recently_viewed_user (user_id), INDEX ix_recently_viewed_product (product_id), CONSTRAINT fk_recently_viewed_user FOREIGN KEY (user_id) REFERENCES users(id), CONSTRAINT fk_recently_viewed_product FOREIGN KEY (product_id) REFERENCES products(id))",
            "CREATE TABLE IF NOT EXISTS payment_transactions (id INT AUTO_INCREMENT PRIMARY KEY, order_id INT NOT NULL, user_id INT NOT NULL, provider VARCHAR(40) NOT NULL, amount FLOAT NOT NULL, status VARCHAR(40) DEFAULT 'PAID', reference VARCHAR(120) DEFAULT '', refund_status VARCHAR(40) DEFAULT 'NONE', created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_payment_transactions_order (order_id), INDEX ix_payment_transactions_user (user_id), CONSTRAINT fk_payment_transactions_order FOREIGN KEY (order_id) REFERENCES orders(id), CONSTRAINT fk_payment_transactions_user FOREIGN KEY (user_id) REFERENCES users(id))",
            "CREATE TABLE IF NOT EXISTS complaints (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, order_id INT NULL, product_id INT NULL, subject VARCHAR(160) NOT NULL, message TEXT NOT NULL, status VARCHAR(40) DEFAULT 'OPEN', resolution_note TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, INDEX ix_complaints_user (user_id), CONSTRAINT fk_complaints_user FOREIGN KEY (user_id) REFERENCES users(id), CONSTRAINT fk_complaints_order FOREIGN KEY (order_id) REFERENCES orders(id), CONSTRAINT fk_complaints_product FOREIGN KEY (product_id) REFERENCES products(id))",
        ]
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
    db = SessionLocal()
    try:
        if not db.get(User, 1):
            db.add(
                User(
                    id=1,
                    name="Aarav Sharma",
                    email="aarav.buyer@example.com",
                    phone="9876543210",
                    role="buyer",
                    password_hash=hash_password("password123"),
                    oauth_provider="",
                    google_sub="",
                    is_active=True,
                    seller_status="APPROVED",
                    address_line="42, MG Road",
                    city="Bengaluru",
                    state="Karnataka",
                    pincode="560001",
                    store_name="",
                )
            )
        if not db.get(User, 2):
            db.add(
                User(
                    id=2,
                    name="Priya Retail Partner",
                    email="seller@example.com",
                    phone="9123456780",
                    role="seller",
                    password_hash=hash_password("seller123"),
                    oauth_provider="",
                    google_sub="",
                    is_active=True,
                    seller_status="APPROVED",
                    address_line="Warehouse 12, Market Yard",
                    city="Bengaluru",
                    state="Karnataka",
                    pincode="560100",
                    store_name="Priya Digital & Daily Needs",
                )
            )
        db.commit()
        buyer = db.get(User, 1)
        seller = db.get(User, 2)
        if buyer and (not buyer.password_hash or not buyer.password_hash.startswith("pbkdf2_sha256$")):
            buyer.password_hash = hash_password("password123")
        if seller and (not seller.password_hash or not seller.password_hash.startswith("pbkdf2_sha256$")):
            seller.password_hash = hash_password("seller123")
        db.commit()

        db.query(Product).filter(Product.seller_id.is_(None)).update({"seller_id": 2})
        db.query(Product).filter(Product.listing_status.is_(None)).update({"listing_status": "APPROVED"})
        db.commit()

        categories: dict[str, Category] = {}
        for item in PRODUCTS:
            name, slug = item["category"]
            if slug not in categories:
                category = db.query(Category).filter(Category.slug == slug).first()
                if not category:
                    category = Category(name=name, slug=slug)
                    db.add(category)
                    db.flush()
                categories[slug] = category

            if db.query(Product).filter(Product.title == item["title"]).first():
                continue

            product = Product(
                category_id=categories[slug].id,
                title=item["title"],
                brand=item["brand"],
                description=item["description"],
                price=item["price"],
                mrp=item["mrp"],
                rating=item["rating"],
                reviews=item["reviews"],
                stock=item["stock"],
                seller_id=2,
                listing_status="APPROVED",
                approval_note="Approved for storefront",
                low_stock_threshold=5,
            )
            product.images = [
                ProductImage(url=url, alt=f"{item['title']} image {index + 1}")
                for index, url in enumerate(item["images"])
            ]
            product.specs = [ProductSpec(name=name, value=value) for name, value in item["specs"].items()]
            db.add(product)
        db.commit()
        seed_reviews(db)
        seed_account_data(db)
        seed_demo_order_data(db)
    finally:
        db.close()


def seed_reviews(db):
    if db.query(Review).count():
        return
    reviews = [
        (1, 1, 5, "Excellent display and battery backup. Delivery was quick.", True),
        (1, 2, 4, "Noise cancellation is good for this price range.", True),
        (1, 3, 4, "Comfortable fit and looks premium.", False),
        (1, 4, 5, "Heats water fast and feels sturdy.", True),
        (1, 5, 4, "Spacious refrigerator and silent operation.", False),
        (1, 6, 5, "Good quality dal, clean packaging.", True),
    ]
    for user_id, product_id, rating, comment, verified in reviews:
        db.add(
            Review(
                user_id=user_id,
                product_id=product_id,
                rating=rating,
                comment=comment,
                verified_purchase=verified,
                seller_response="Thanks for your feedback!" if verified else "",
            )
        )
    db.commit()


def seed_account_data(db):
    if not db.scalar(text("SELECT COUNT(*) FROM user_addresses")):
        db.add_all(
            [
                UserAddress(
                    user_id=1,
                    label="Home",
                    customer_name="Aarav Sharma",
                    phone="9876543210",
                    address_line="42, MG Road",
                    city="Bengaluru",
                    state="Karnataka",
                    pincode="560001",
                    is_default=True,
                ),
                UserAddress(
                    user_id=1,
                    label="Office",
                    customer_name="Aarav Sharma",
                    phone="9876543210",
                    address_line="18, Residency Road",
                    city="Bengaluru",
                    state="Karnataka",
                    pincode="560025",
                    is_default=False,
                ),
            ]
        )
    if not db.scalar(text("SELECT COUNT(*) FROM saved_payment_methods")):
        db.add_all(
            [
                SavedPaymentMethod(user_id=1, provider="UPI", label="Personal UPI", upi_id="aarav@upi", is_default=True),
                SavedPaymentMethod(user_id=1, provider="CARD", label="Visa ending 4242", card_last4="4242", is_default=False),
            ]
        )
    if not db.scalar(text("SELECT COUNT(*) FROM recently_viewed_products")):
        for product_id in [1, 2, 7, 13]:
            db.add(RecentlyViewedProduct(user_id=1, product_id=product_id))
    db.commit()


def seed_demo_order_data(db):
    if db.query(Order).count():
        return
    product = db.get(Product, 2)
    if not product:
        return
    order = Order(
        order_number="ODDEMO000001",
        user_id=1,
        customer_name="Aarav Sharma",
        phone="9876543210",
        address_line="42, MG Road",
        city="Bengaluru",
        state="Karnataka",
        pincode="560001",
        total_amount=product.price,
        payment_method="UPI",
        payment_status="PAID",
        payment_reference="PAYDEMO0001",
        status="DELIVERED",
        tracking_status="Delivered",
        refund_status="NONE",
    )
    order.items = [
        OrderItem(
            product_id=product.id,
            title=product.title,
            price=product.price,
            quantity=1,
            seller_id=product.seller_id,
            status="DELIVERED",
            tracking_status="Delivered",
        )
    ]
    db.add(order)
    db.commit()
    db.refresh(order)
    db.add(
        PaymentTransaction(
            order_id=order.id,
            user_id=1,
            provider="UPI",
            amount=order.total_amount,
            status="PAID",
            reference=order.payment_reference,
            refund_status="NONE",
        )
    )
    db.add(
        Complaint(
            user_id=1,
            order_id=order.id,
            product_id=product.id,
            subject="Demo delivery feedback",
            message="This is a seeded demo complaint for admin moderation testing.",
            status="IN_REVIEW",
            resolution_note="Assigned for review",
        )
    )
    db.commit()


if __name__ == "__main__":
    run()
    print("Database seeded.")
