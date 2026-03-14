from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models.models import db, Book, Category, Order, OrderItem, User, Author
from services.recommendation_service import recommendation_service

public_bp = Blueprint('public_bp', __name__)

@public_bp.context_processor
def inject_global_data():
    """Injects categories and cart count into all templates."""
    categories = Category.query.order_by(Category.name).all()
    cart_count = 0
    if 'cart' in session:
        cart_count = sum(session['cart'].values())
    
    current_user = None
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        
    return dict(global_categories=categories, cart_count=cart_count, current_user=current_user)

@public_bp.route('/')
def index():
    # Top 5 popular books
    popular_books_data = recommendation_service.get_popular_books(top_n=5)
    
    return render_template('homepage.html', 
                           popular_books=popular_books_data)

@public_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')

        if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
            flash('Email or username already exists.', 'error')
            return redirect(url_for('public_bp.register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password, full_name=full_name)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('public_bp.login'))

    return render_template('register.html')

@public_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('Account is suspended.', 'error')
                return redirect(url_for('public_bp.login'))
            
            session['user_id'] = user.id
            session['user_role'] = user.role
            flash('Logged in successfully.', 'success')
            
            # Map session cart to user cart logic here in future.
            
            # Redirect admin to dashboard, users to home.
            if user.role == 'admin':
                return redirect(url_for('admin_bp.dashboard'))
            return redirect(url_for('public_bp.index'))
            
        flash('Invalid email or password.', 'error')

    return render_template('login.html')

@public_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('public_bp.index'))

@public_bp.route('/catalog')
def catalog():
    page = request.args.get('page', 1, type=int)
    category_slug = request.args.get('category')
    search_query = request.args.get('q')
    
    query = Book.query

    if category_slug:
        category = Category.query.filter_by(slug=category_slug).first()
        if category:
            query = query.filter(Book.categories.contains(category))
    
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Book.title.ilike(search_term),
                Book.authors.any(Author.name.ilike(search_term)),
                Book.isbn.ilike(search_term)
            )
        )
        
    # Order by newest first or any default logic
    query = query.order_by(Book.id.desc())
    
    # Paginate, 12 items per page
    pagination = query.paginate(page=page, per_page=12, error_out=False)
    books = pagination.items
    
    return render_template('catalog.html', 
                           books=books, 
                           pagination=pagination, 
                           current_category=category_slug,
                           search_query=search_query)
    
@public_bp.route('/book/<slug>')
def book_detail(slug):
    book = Book.query.filter_by(slug=slug).first_or_404()
    
    # Get similar books logic
    similar_books_data = recommendation_service.recommend_similar_books(book.id, top_n=5)
    
    return render_template('bookdetail.html', 
                           book=book,
                           similar_books=similar_books_data)
    
@public_bp.route('/add-to-cart/<int:book_id>', methods=['POST'])
def add_to_cart(book_id):
    book = Book.query.get_or_404(book_id)
    quantity = int(request.form.get('quantity', 1))

    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']
    book_id_str = str(book_id)

    if book_id_str in cart:
        cart[book_id_str] += quantity
    else:
        cart[book_id_str] = quantity

    session.modified = True
    flash(f'Added {quantity} x "{book.title}" to your cart.', 'success')
    return redirect(url_for('public_bp.cart'))

@public_bp.route('/cart')
def cart():
    cart_session = session.get('cart', {})
    cart_items = []
    subtotal = 0.0

    for book_id_str, quantity in cart_session.items():
        book = Book.query.get(int(book_id_str))
        if book:
            item_price = book.discount_price if book.discount_price else book.price
            item_total = item_price * quantity
            subtotal += item_total
            cart_items.append({
                'book': book,
                'quantity': quantity,
                'item_total': item_total
            })

    return render_template('cart.html', cart_items=cart_items, subtotal=subtotal)

@public_bp.route('/update-cart/<int:book_id>', methods=['POST'])
def update_cart(book_id):
    action = request.form.get('action')
    cart = session.get('cart', {})
    book_id_str = str(book_id)

    if book_id_str in cart:
        if action == 'increase':
            book = Book.query.get(book_id)
            if book and cart[book_id_str] < book.stock_quantity:
                cart[book_id_str] += 1
        elif action == 'decrease' and cart[book_id_str] > 1:
            cart[book_id_str] -= 1

        session['cart'] = cart
        session.modified = True

    return redirect(url_for('public_bp.cart'))

@public_bp.route('/remove-from-cart/<int:book_id>', methods=['POST'])
def remove_from_cart(book_id):
    cart = session.get('cart', {})
    book_id_str = str(book_id)
    if book_id_str in cart:
        del cart[book_id_str]
        session['cart'] = cart
        session.modified = True
    return redirect(url_for('public_bp.cart'))

@public_bp.route('/clear-cart', methods=['POST'])
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('public_bp.cart'))

@public_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart_session = session.get('cart', {})
    if not cart_session:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('public_bp.cart'))

    cart_items = []
    subtotal = 0.0
    for book_id_str, quantity in cart_session.items():
        book = Book.query.get(int(book_id_str))
        if book:
            item_price = float(book.discount_price) if book.discount_price else float(book.price)
            subtotal = subtotal + (item_price * quantity)
            cart_items.append({'book': book, 'quantity': quantity})

    shipping_fee = 5.0
    total_amount = subtotal + shipping_fee

    if request.method == 'POST':
        # Create Order
        new_order = Order(
            user_id=session.get('user_id'),
            status='pending',
            subtotal_amount=subtotal,
            shipping_fee=shipping_fee,
            total_amount=total_amount,
            receiver_name=f"{request.form.get('first_name', '')} {request.form.get('last_name', '')}".strip() or "Guest",
            phone_number=request.form.get('phone', 'N/A'),
            address=request.form.get('address', 'N/A'),
            payment_method='COD' # Cash on delivery
        )
        try:
            db.session.add(new_order)
            db.session.flush() # Get order ID

            for item in cart_items:
                order_item = OrderItem(
                    order_id=new_order.id,
                    book_id=item['book'].id,
                    quantity=item['quantity'],
                    price_at_purchase=item['book'].discount_price if item['book'].discount_price else item['book'].price
                )
                db.session.add(order_item)
                
                # Reduce stock
                if item['book'].stock_quantity is not None:
                    item['book'].stock_quantity = max(0, item['book'].stock_quantity - item['quantity'])

            db.session.commit()
            # Clear cart
            session.pop('cart', None)
            flash("Order placed successfully via Cash on Delivery!", "success")
            return redirect(url_for('public_bp.order_confirmation', order_id=new_order.id))
            
        except Exception as e:
            db.session.rollback()
            flash("An error occurred during checkout. Please try again.", "error")
            print(f"Checkout Error: {e}")
            return redirect(url_for('public_bp.checkout'))

    return render_template('checkout.html', cart_items=cart_items, subtotal=subtotal, shipping_fee=shipping_fee, total_amount=total_amount)
    
@public_bp.route('/order-confirmation/<int:order_id>')
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order_confirmation.html', order=order)

@public_bp.route('/order-history')
def order_history():
    if 'user_id' not in session:
        flash('Please log in to view your order history.', 'warning')
        return redirect(url_for('public_bp.login'))
        
    user_id = session['user_id']
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    
    return render_template('order_history.html', orders=orders)
