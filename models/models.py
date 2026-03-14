from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Association tables
book_authors = db.Table('book_authors',
    db.Column('book_id', db.Integer, db.ForeignKey('books.id'), primary_key=True),
    db.Column('author_id', db.Integer, db.ForeignKey('authors.id'), primary_key=True)
)

book_categories = db.Table('book_categories',
    db.Column('book_id', db.Integer, db.ForeignKey('books.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'), primary_key=True)
)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    full_name = db.Column(db.String(128))
    password_hash = db.Column(db.String(256))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='user') # 'admin' or 'user'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', backref='user', lazy='dynamic')
    cart_items = db.relationship('CartItem', backref='user', lazy='dynamic')
    wishlist_items = db.relationship('WishlistItem', backref='user', lazy='dynamic')

class Author(db.Model):
    __tablename__ = 'authors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, index=True)

class Publisher(db.Model):
    __tablename__ = 'publishers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, index=True)

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    slug = db.Column(db.String(64), unique=True, index=True)

class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True) # Will map to book_id from csv
    title = db.Column(db.String(256), nullable=False, index=True)
    slug = db.Column(db.String(256), unique=True, index=True)
    publication_year = db.Column(db.Integer)
    average_rating = db.Column(db.Float)
    ratings_count = db.Column(db.Integer)
    image_url = db.Column(db.String(512))
    small_image_url = db.Column(db.String(512))
    description = db.Column(db.Text)
    sku = db.Column(db.String(64), unique=True, index=True)
    price = db.Column(db.Float, nullable=False)
    discount_price = db.Column(db.Float)
    stock_quantity = db.Column(db.Integer, default=0)
    format = db.Column(db.String(64))
    language = db.Column(db.String(64))
    isbn = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    publisher_id = db.Column(db.Integer, db.ForeignKey('publishers.id'))
    publisher = db.relationship('Publisher', backref='books')
    
    authors = db.relationship('Author', secondary=book_authors, lazy='subquery', backref=db.backref('books', lazy=True))
    categories = db.relationship('Category', secondary=book_categories, lazy='subquery', backref=db.backref('books', lazy=True))

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    session_id = db.Column(db.String(128)) # For guest checkouts if needed, but requirements imply logged in
    status = db.Column(db.String(32), default='pending') # pending, processing, shipped, delivered, cancelled
    subtotal_amount = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, default=0.0)
    shipping_fee = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(32), default='COD')
    receiver_name = db.Column(db.String(128), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    note = db.Column(db.Text)
    traffic_source = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('OrderItem', backref='order', lazy='dynamic')

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_purchase = db.Column(db.Float, nullable=False)

    book = db.relationship('Book')

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    session_id = db.Column(db.String(128)) # Used for anonymous users
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    
    book = db.relationship('Book')

class WishlistItem(db.Model):
    __tablename__ = 'wishlist_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    book = db.relationship('Book')

class RecentlyViewedBook(db.Model):
    __tablename__ = 'recently_viewed_books'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    session_id = db.Column(db.String(128))
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    book = db.relationship('Book')

class ChatbotLog(db.Model):
    __tablename__ = 'chatbot_logs'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(128), nullable=False)
    query = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RecommendationLog(db.Model):
    __tablename__ = 'recommendation_logs'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(128), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'))
    recommendations = db.Column(db.Text) # JSON string of recommended book IDs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
