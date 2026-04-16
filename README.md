# Flipkart Clone

Full-stack Flipkart-style demo store built with React, FastAPI, Flask, and MySQL.
### Live Demo: 
- https://flipkart-clone-five-beryl.vercel.app/

## Stack

- Frontend: React + Vite
- Main API: FastAPI + SQLAlchemy
- Companion service: Flask
- Database: MySQL
- AI support bot: OpenAI Responses API

## What The App Includes

- Buyer login, signup, and demo Google sign-in
- Product listing with categories
- Search and filters for category, price, and rating
- Product detail page with gallery, specs, reviews, and ratings
- Cart and wishlist
- Checkout with address capture
- Payment step before order placement
- Payment methods: Razorpay, Stripe, PayPal, UPI, card, COD
- Order history and tracking status
- Buyer and seller views
- Admin dashboard
- Verified-purchase reviews
- OpenAI-powered chat widget for shopping help

## Project Structure

```text
backend/
  app/
    database.py
    main.py
    models.py
    schemas.py
    seed.py
  .env.example
  flask_service.py
  requirements.txt
frontend/
  src/
    App.jsx
    api.js
    main.jsx
    styles.css
  package.json
README.md
```

## Demo Accounts

- Buyer
  - Email: `aarav.buyer@example.com`
  - Password: `password123`
- Seller
  - Email: `seller@example.com`
  - Password: `seller123`
- Admin
  - Email: `admin@flipkart.com`
  - Password: `admin123`

## 1. Create The Database

Open MySQL and create the database:

```sql
CREATE DATABASE flipkart_clone CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 2. Create `backend/.env`

Use [`backend/.env.example`](/c:/Users/Acer/Desktop/Flipkart/backend/.env.example) as the template.

Quick copy commands:

```powershell
Copy-Item backend\.env.example backend\.env
```

```cmd
copy backend\.env.example backend\.env
```

Example:

```env
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/flipkart_clone
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini

RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=
EMAIL_PASSWORD=

ADMIN_EMAIL=admin@flipkart.com
ADMIN_PASSWORD=admin123
```

Notes:

- `OPENAI_API_KEY` is required for the chatbot.
- Razorpay and email settings are optional for local demo runs.

## 3. Install Backend Dependencies

From the repo root:

```powershell
python -m pip install -r backend\requirements.txt
```

## 4. Seed The Database

From the repo root:

```powershell
$env:DATABASE_URL="mysql+pymysql://root:password@localhost:3306/flipkart_clone"
python -m backend.app.seed
```

CMD version:

```cmd
set DATABASE_URL=mysql+pymysql://root:password@localhost:3306/flipkart_clone
python -m backend.app.seed
```

## 5. Start FastAPI

PowerShell:

```powershell
cd backend
$env:DATABASE_URL="mysql+pymysql://root:password@localhost:3306/flipkart_clone"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

CMD:

```cmd
cd backend
set DATABASE_URL=mysql+pymysql://root:password@localhost:3306/flipkart_clone
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

## 6. Start Flask

Open a second terminal:

```powershell
cd backend
python flask_service.py
```

CMD:

```cmd
cd backend
python flask_service.py
```

Health check:

```text
http://127.0.0.1:5001/health
```

## 7. Start Frontend

Open a third terminal:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

CMD:

```cmd
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

App URL:

```text
http://127.0.0.1:5173/
```

Do not open `frontend/index.html` directly. Run Vite and use the local dev URL.

## Quick Run Order

Start things in this order:

1. MySQL
2. `python -m backend.app.seed`
3. FastAPI on `127.0.0.1:8000`
4. Flask on `127.0.0.1:5001`
5. Vite on `127.0.0.1:5173`

## Render Backend Deploy

If you deploy the backend on Render, this repo's [`render.yaml`](/c:/Users/Acer/Desktop/Flipkart/render.yaml) now does three important things for you:

- pins Python to `3.11.11`
- installs dependencies with writable Cargo temp directories
- avoids `uvicorn[standard]`, which can pull in extra build-time native dependencies that are not needed on Render

If your Render service was created manually instead of from the blueprint, copy these settings into the Render dashboard:

```bash
export CARGO_HOME=/tmp/cargo
export RUSTUP_HOME=/tmp/rustup
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Also set:

```env
PYTHON_VERSION=3.11.11
```

If your build log shows `python3.14`, `maturin`, `cargo metadata`, or `/usr/local/cargo` read-only errors, the service is still using the wrong Python/runtime settings and needs to be redeployed after updating them.

## Useful Endpoints

- Health: `http://127.0.0.1:8000/api/health`
- Products: `http://127.0.0.1:8000/api/products`
- Orders: `http://127.0.0.1:8000/api/orders`
- AI chat: `http://127.0.0.1:8000/api/ai/chat`
- Flask health: `http://127.0.0.1:5001/health`

## Chatbot Setup

The chat widget is built into the frontend and calls the FastAPI route at `/api/ai/chat`.

If `OPENAI_API_KEY` is missing, the app will return a helpful backend error instead of silently failing.

The chatbot uses the store catalog, current cart, and recent orders as context so it can answer questions about:

- product suggestions
- checkout and payment options
- recent orders
- buyer and seller workflows

## What I Verified

- Backend import works
- `python -m compileall backend` passes
- Frontend production build passes

## Troubleshooting

- Blank frontend page:
  - Make sure you opened `http://127.0.0.1:5173/`
  - Hard refresh with `Ctrl + Shift + R`
- `mysqladmin` not recognized:
  - Add your MySQL `bin` directory to `PATH`
- Chatbot says OpenAI is not configured:
  - Add `OPENAI_API_KEY` to `backend/.env`
- Products or cart fail to load:
  - Confirm MySQL is running
  - Rerun `python -m backend.app.seed`
  - Check `http://127.0.0.1:8000/api/health`
