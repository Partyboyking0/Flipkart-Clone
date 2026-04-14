# Flipkart Clone - SDE Intern Fullstack Assignment

A functional e-commerce web application inspired by Flipkart's browsing, cart, checkout, and order placement flow.

## Tech Stack

- Frontend: React.js SPA with Vite
- Main Backend: Python FastAPI
- Companion Backend: Python Flask notification/health service
- Database: MySQL with SQLAlchemy ORM

## Features

- Product listing grid with Flipkart-like cards
- Search products by name
- Filter products by category
- Product detail page with image carousel, description, specs, stock, Add to Cart, and Buy Now
- Shopping cart with quantity update, remove item, subtotal, discount, delivery fee, and total
- Checkout page with shipping address form
- Payment step before order placement using UPI, card, or cash on delivery
- Order confirmation page with generated order ID
- Buyer dashboard with user details and past order summaries
- Seller dashboard with seller details, inventory, sales, and order summaries
- Seed data across multiple categories
- Responsive layout for mobile, tablet, and desktop

## Project Structure

```text
backend/
  app/
    database.py
    main.py
    models.py
    schemas.py
    seed.py
  flask_service.py
  requirements.txt
  schema.sql
  seed.sql
frontend/
  index.html
  package.json
  src/
    App.jsx
    api.js
    main.jsx
    styles.css
```

## MySQL Setup

```sql
CREATE DATABASE flipkart_clone CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

```powershell
$env:DATABASE_URL="mysql+pymysql://root:password@localhost:3306/flipkart_clone"
```

You can either let FastAPI create tables automatically on startup, or run:

```powershell
mysql -u root -p flipkart_clone < backend/schema.sql
mysql -u root -p flipkart_clone < backend/seed.sql
```

## Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

Run the Flask companion service in another terminal:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python flask_service.py
```

FastAPI runs at `http://localhost:8000`. Flask runs at `http://localhost:5001`.

## Frontend Setup

Install Node.js first if it is not available on your machine.

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`.

## Assumptions

- No login is required, as instructed in the assignment. The app seeds a demo buyer with ID `1` and seller with ID `2`.
- The FastAPI service owns product, cart, and order functionality.
- The Flask service represents a lightweight companion service for operational health and order notification handling.
- Product images use public remote image URLs so the repository stays lightweight.
