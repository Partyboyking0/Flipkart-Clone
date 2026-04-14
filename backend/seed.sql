INSERT INTO categories (id, name, slug) VALUES
(1, 'Mobiles', 'mobiles'),
(2, 'Electronics', 'electronics'),
(3, 'Fashion', 'fashion'),
(4, 'Home', 'home'),
(5, 'Appliances', 'appliances'),
(6, 'Grocery', 'grocery')
ON DUPLICATE KEY UPDATE name = VALUES(name), slug = VALUES(slug);

INSERT INTO users (id, name, email, phone, role, address_line, city, state, pincode, store_name) VALUES
(1, 'Aarav Sharma', 'aarav.buyer@example.com', '9876543210', 'buyer', '42, MG Road', 'Bengaluru', 'Karnataka', '560001', ''),
(2, 'Priya Retail Partner', 'seller@example.com', '9123456780', 'seller', 'Warehouse 12, Market Yard', 'Bengaluru', 'Karnataka', '560100', 'Priya Digital & Daily Needs')
ON DUPLICATE KEY UPDATE name = VALUES(name), phone = VALUES(phone), role = VALUES(role), store_name = VALUES(store_name);

INSERT INTO products (id, title, brand, description, price, mrp, rating, reviews, stock, assured, category_id, seller_id) VALUES
(1, 'Motorola Edge 50 Fusion (Marshmallow Blue, 128 GB)', 'Motorola', 'A slim 5G smartphone with a curved pOLED display, fast charging, and a dependable camera setup for everyday photography.', 22999, 27999, 4.4, 18452, 18, TRUE, 1, 2),
(2, 'Sony WH-CH720N Wireless Noise Cancelling Headphones', 'Sony', 'Lightweight wireless headphones with active noise cancellation, rich sound, and long battery life.', 8990, 14990, 4.3, 7350, 25, TRUE, 2, 2),
(3, 'Roadster Men Solid Casual Jacket', 'Roadster', 'A regular-fit casual jacket designed for everyday layering and a clean streetwear look.', 1499, 3999, 4.1, 2201, 40, TRUE, 3, 2),
(4, 'Prestige Electric Kettle 1.5 L', 'Prestige', 'Fast boiling electric kettle with auto cut-off, cool-touch handle, and stainless steel body.', 799, 1495, 4.2, 10892, 60, TRUE, 4, 2),
(5, 'Samsung 253 L Frost Free Double Door Refrigerator', 'Samsung', 'Energy efficient double door refrigerator with digital inverter compressor and spacious storage.', 27490, 36999, 4.5, 4160, 12, TRUE, 5, 2),
(6, 'Tata Sampann Unpolished Toor Dal 1 kg', 'Tata Sampann', 'Protein-rich unpolished toor dal for everyday Indian cooking.', 169, 220, 4.4, 5291, 100, TRUE, 6, 2)
ON DUPLICATE KEY UPDATE title = VALUES(title), price = VALUES(price), mrp = VALUES(mrp), stock = VALUES(stock);

INSERT INTO product_images (product_id, url, alt) VALUES
(1, 'https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=900&q=80', 'Motorola phone front'),
(1, 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=900&q=80', 'Motorola phone angle'),
(2, 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80', 'Sony headphones'),
(2, 'https://images.unsplash.com/photo-1484704849700-f032a568e944?auto=format&fit=crop&w=900&q=80', 'Wireless headphones'),
(3, 'https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=900&q=80', 'Casual jacket'),
(4, 'https://images.unsplash.com/photo-1594213114663-d94db9b17125?auto=format&fit=crop&w=900&q=80', 'Electric kettle'),
(5, 'https://images.unsplash.com/photo-1571175443880-49e1d25b2bc5?auto=format&fit=crop&w=900&q=80', 'Refrigerator'),
(6, 'https://images.unsplash.com/photo-1615485500704-8e990f9900f7?auto=format&fit=crop&w=900&q=80', 'Toor dal');

INSERT INTO product_specs (product_id, name, value) VALUES
(1, 'RAM', '8 GB'), (1, 'Storage', '128 GB'), (1, 'Battery', '5000 mAh'),
(2, 'Playback', 'Up to 35 hours'), (2, 'Connectivity', 'Bluetooth 5.2'),
(3, 'Fabric', 'Polyester Blend'), (3, 'Fit', 'Regular'),
(4, 'Capacity', '1.5 L'), (4, 'Power', '1500 W'),
(5, 'Capacity', '253 L'), (5, 'Type', 'Double Door'),
(6, 'Weight', '1 kg'), (6, 'Diet', 'Vegetarian');
