# BookVerse - AI-Powered E-Commerce Bookstore 🚀

BookVerse is a full-stack, AI-integrated e-commerce bookstore designed to demonstrate modern web development capabilities. Built with Python, Flask, PostgreSQL, Bootstrap 5, and Jinja2 templates, this platform features a realistic UI, a robust relational database, and smart AI models that recommend books and drive an intelligent chatbot.

[📚 Live Demo](https://github.com/yenthanh18/bookverse) | [✨ Watch Walkthrough](https://github.com/yenthanh18/bookverse)

---

## 📸 Screenshots

| Homepage & Categories | AI Recommendations | Checkout Funnel |
|:---:|:---:|:---:|
| <img src="https://via.placeholder.com/400x250?text=Homepage" alt="Homepage view" width="300"/> | <img src="https://via.placeholder.com/400x250?text=AI+Recommendations" alt="Similar Books" width="300"/> | <img src="https://via.placeholder.com/400x250?text=Checkout" alt="Checkout view" width="300"/> |

| Floating AI Chatbot | Admin Dashboard | Book Inventory |
|:---:|:---:|:---:|
| <img src="https://via.placeholder.com/400x250?text=Chatbot" alt="Floating Chatbot" width="300"/> | <img src="https://via.placeholder.com/400x250?text=Dashboard+Stats" alt="Dashboard Statistics" width="300"/> | <img src="https://via.placeholder.com/400x250?text=Inventory+Tracker" alt="Inventory tracking" width="300"/> |

---

## 🌟 Key Features

- **Storefront**: Responsive UI built with Tailwind/Bootstrap-inspired utilities, featuring paginated catalogs and category filtering.
- **Dynamic Cart & Checkout**: Robust session-based shopping cart seamlessly migrating to database relations during checkout.
- **Admin Dashboard**: Real-time sales metrics, comprehensive order management with status updates, and visual low-stock inventory alerts.
- **AI Recommendation Engine**: "Similar Books" algorithms powered by Cosine Similarity across book metadata matrices.
- **Smart NLP Chatbot**: Fuzzy-matching intent routers that answer product queries instantly without hitting third-party LLM APIs.
- **Data Analytics**: Complete Google Analytics 4 (GA4) e-commerce funnel tracking (`page_view`, `search`, `view_item`, `add_to_cart`, `begin_checkout`, `purchase`).

---

## 🏗 Architecture Overview

```mermaid
graph TD
    Client[Web Browser] -->|HTTP Requests| Flask[Flask Backend]
    Flask -->|Reads/Writes| DB[(PostgreSQL Database)]
    Flask -->|Queries Intents| NLP[Chatbot Service TF-IDF]
    Flask -->|Fetches Arrays| Recs[Recommendation Service Matrix]
    
    DB -.->|10K+ Books, Orders, Users| DB
```

---

## 🚀 Setup & Local Installation

### 1. Prerequisites
- Python 3.9+ 
- PostgreSQL 13+

### 2. Environment Variables
Create a `.env` file in the project root containing your database URI:
```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/bookverse
SECRET_KEY=dev_secret_key_change_in_production
```

### 3. Install Dependencies
Initialize a virtual environment and load requirements:
```bash
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Mac/Linux
pip install -r requirements.txt
```

### 4. Database Initialization & Seeding
The project ships with a massive dataset of ~10,000 real books. Use the custom seed file to parse the dataset, clean up duplication, and automatically inject proper PostgreSQL relations (Authors, Publishers, Pricing):
```bash
python seed/seed_books.py
```
*Note: This script dynamically generates the administrative user:*
- **Email:** `admin@bookverse.com`
- **Password:** `admin123`

### 5. Running the Application
```bash
python app.py
```
Navigate to `http://localhost:5000` to start exploring!

---

## 🧠 AI Modules Explained

### 1. Intent Routing Chatbot (`services/chatbot_service.py`)
Our chatbot widget floating in the UI doesn't require a generic LLM. Instead, it uses `scikit-learn` and `RapidFuzz` for offline NLP logic:
- **Taxonomy Normalization**: Translates raw slang ("sci-fi", "ya") into system categories ("science fiction", "young adult").
- **Intent Recognition**: Flags predefined patterns ("find books by", "similar to") and parses the target subject.
- **Semantic Fallbacks**: Leverages a pre-trained `TF-IDF Matrix` over book descriptions to calculate cosine-similarity comparisons, guaranteeing 3-5 hyper-relevant responses to vague queries.

### 2. Item-Item Similarities (`services/recommendation_service.py`)
Content-based recommendation arrays are pre-computed and stored in `.pkl` assets. When a user requests a Book Detail page (`/book/<slug>`), the system accesses these arrays to instantly serve visually appealing "Similar Books" carousels without the overhead of real-time heavy math computation.

---

## ☁️ Deployment (Render)

This application is configured for production serverless deployment on Render using Gunicorn.

1. **Connect GitHub to Render**
   - Create a new "Web Service" in your Render dashboard and connect your GitHub repository (`https://github.com/yenthanh18/bookverse`).

2. **Configure Build & Start Commands**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`

3. **Environment Variables**
   Add the following variables to your Render Web Service settings:
   - `DATABASE_URL` (Required): Your external PostgreSQL connection string (Render provides a hosted Postgres addon). Must start with `postgresql://`
   - `SECRET_KEY` (Required): A secure randomized string for session management.
   - `PYTHON_VERSION` (Required): Set to `3.10.13` to ensure pandas and ML libraries compile correctly. The project also includes a `.python-version` file.

4. **Live URL**
   - After setting exactly `PYTHON_VERSION=3.10.13`, manually trigger **"Clear build cache & deploy"** in the Render dashboard.
   - Your application will then be available at `https://bookverse.onrender.com` 

*(Note: Pushing code to the `main` branch will seamlessly trigger an automatic build and manual redeploys can be fired directly through the Render Dashboard.)*

---

## 🔮 Future Improvements
- [ ] Incorporate Stripe API for live payment processing.
- [ ] Migrate AI models to vector databases (e.g., Pinecone/Milvus) for >1M item scalability.
- [ ] Add Redis caching to offload complex Catalog/Search SQL queries.
- [ ] Introduce User Reviews and collaborative-filtering recommendations.

---
*Created as part of the BookVerse Capstone Project.*
