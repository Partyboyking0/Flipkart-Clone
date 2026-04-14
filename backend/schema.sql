CREATE TABLE IF NOT EXISTS categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  slug VARCHAR(120) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(160) NOT NULL,
  email VARCHAR(180) NOT NULL UNIQUE,
  phone VARCHAR(20) NOT NULL,
  role VARCHAR(20) NOT NULL,
  address_line VARCHAR(255) DEFAULT '',
  city VARCHAR(100) DEFAULT '',
  state VARCHAR(100) DEFAULT '',
  pincode VARCHAR(12) DEFAULT '',
  store_name VARCHAR(160) DEFAULT ''
);

CREATE TABLE IF NOT EXISTS products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  brand VARCHAR(120) NOT NULL,
  description TEXT NOT NULL,
  price DOUBLE NOT NULL,
  mrp DOUBLE NOT NULL,
  rating DOUBLE DEFAULT 4.2,
  reviews INT DEFAULT 1000,
  stock INT DEFAULT 0,
  assured BOOLEAN DEFAULT TRUE,
  category_id INT NOT NULL,
  seller_id INT DEFAULT 2,
  INDEX ix_products_title (title),
  CONSTRAINT fk_products_categories FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS product_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  product_id INT NOT NULL,
  url VARCHAR(600) NOT NULL,
  alt VARCHAR(255) NOT NULL,
  CONSTRAINT fk_images_products FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS product_specs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  product_id INT NOT NULL,
  name VARCHAR(160) NOT NULL,
  value VARCHAR(255) NOT NULL,
  CONSTRAINT fk_specs_products FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cart_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT DEFAULT 1,
  product_id INT NOT NULL,
  quantity INT DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_cart_user (user_id),
  CONSTRAINT fk_cart_products FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS orders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  order_number VARCHAR(40) NOT NULL UNIQUE,
  user_id INT DEFAULT 1,
  customer_name VARCHAR(160) NOT NULL,
  phone VARCHAR(20) NOT NULL,
  address_line VARCHAR(255) NOT NULL,
  city VARCHAR(100) NOT NULL,
  state VARCHAR(100) NOT NULL,
  pincode VARCHAR(12) NOT NULL,
  total_amount DOUBLE NOT NULL,
  payment_method VARCHAR(40) DEFAULT 'UPI',
  payment_status VARCHAR(40) DEFAULT 'PAID',
  payment_reference VARCHAR(80) DEFAULT '',
  status VARCHAR(40) DEFAULT 'PLACED',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_orders_user (user_id)
);

CREATE TABLE IF NOT EXISTS order_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  order_id INT NOT NULL,
  product_id INT NOT NULL,
  title VARCHAR(255) NOT NULL,
  price DOUBLE NOT NULL,
  quantity INT NOT NULL,
  seller_id INT DEFAULT 2,
  CONSTRAINT fk_order_items_orders FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
  CONSTRAINT fk_order_items_products FOREIGN KEY (product_id) REFERENCES products(id)
);
