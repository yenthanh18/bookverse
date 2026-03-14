from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from models.models import db, Order, Book, OrderItem

admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.before_request
def restrict_admin():
    if session.get('user_role') != 'admin':
        flash('You must be an admin to access this page.', 'error')
        return redirect(url_for('public_bp.login'))

@admin_bp.route('/')
def dashboard():
    # Calculate basic sales summary
    total_orders = Order.query.count()
    total_sales_query = db.session.query(db.func.sum(Order.total_amount)).filter(Order.status != 'cancelled').scalar()
    total_sales = float(total_sales_query) if total_sales_query else 0.0
    
    # Recent orders for dashboard
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    # Low stock books count (arbitrary threshold e.g. < 5)
    low_stock_count = Book.query.filter(Book.stock_quantity < 5).count()
    
    return render_template('admin/dashboard.html', 
                           total_orders=total_orders,
                           total_sales=total_sales,
                           recent_orders=recent_orders,
                           low_stock_count=low_stock_count)

@admin_bp.route('/orders')
def manage_orders():
    # Fetch orders ordered by most recent first
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/admin_orders.html', orders=orders)

@admin_bp.route('/books')
def manage_books():
    books = Book.query.order_by(Book.id.desc()).all()
    return render_template('admin/admin_books.html', books=books)

@admin_bp.route('/orders/<int:order_id>', methods=['GET', 'POST'])
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    
    if request.method == 'POST':
        new_status = request.form.get('status')
        if new_status in ['pending', 'confirmed', 'shipping', 'delivered', 'cancelled']:
            order.status = new_status
            db.session.commit()
            flash(f'Order #BV-{order.id:06d} status updated to {new_status}.', 'success')
        return redirect(url_for('admin_bp.order_detail', order_id=order.id))
        
    return render_template('admin/admin_order_detail.html', order=order)
