from sqlalchemy import text

from .database import Base, SessionLocal, engine
from .models import Category, Product, ProductImage, ProductSpec, User


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
]


def run():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        statements = [
            "CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(160) NOT NULL, email VARCHAR(180) NOT NULL UNIQUE, phone VARCHAR(20) NOT NULL, role VARCHAR(20) NOT NULL, address_line VARCHAR(255) DEFAULT '', city VARCHAR(100) DEFAULT '', state VARCHAR(100) DEFAULT '', pincode VARCHAR(12) DEFAULT '', store_name VARCHAR(160) DEFAULT '')",
            "ALTER TABLE products ADD COLUMN seller_id INT DEFAULT 2",
            "ALTER TABLE orders ADD COLUMN payment_method VARCHAR(40) DEFAULT 'UPI'",
            "ALTER TABLE orders ADD COLUMN payment_status VARCHAR(40) DEFAULT 'PAID'",
            "ALTER TABLE orders ADD COLUMN payment_reference VARCHAR(80) DEFAULT ''",
            "ALTER TABLE order_items ADD COLUMN seller_id INT DEFAULT 2",
        ]
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception:
                pass
        connection.execute(text("UPDATE products SET seller_id = 2 WHERE seller_id IS NULL"))
        connection.execute(text("UPDATE order_items SET seller_id = 2 WHERE seller_id IS NULL"))
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
                    address_line="Warehouse 12, Market Yard",
                    city="Bengaluru",
                    state="Karnataka",
                    pincode="560100",
                    store_name="Priya Digital & Daily Needs",
                )
            )
        db.commit()

        if db.query(Product).count():
            db.query(Product).filter(Product.seller_id.is_(None)).update({"seller_id": 2})
            db.commit()
            return

        categories: dict[str, Category] = {}
        for item in PRODUCTS:
            name, slug = item["category"]
            if slug not in categories:
                category = Category(name=name, slug=slug)
                db.add(category)
                db.flush()
                categories[slug] = category

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
            )
            product.images = [
                ProductImage(url=url, alt=f"{item['title']} image {index + 1}")
                for index, url in enumerate(item["images"])
            ]
            product.specs = [ProductSpec(name=name, value=value) for name, value in item["specs"].items()]
            db.add(product)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
    print("Database seeded.")
