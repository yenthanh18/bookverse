import os
from flask import Flask
from config import Config
from models.models import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints (routes)
    from routes.public import public_bp
    from routes.admin import admin_bp
    from routes.api import api_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

    return app

app = create_app()

with app.app_context():
    try:
        print("[DIAGNOSTICS] Checking database connection...")
        db.engine.connect()
        print("[DIAGNOSTICS] Creating missing tables...")
        db.create_all()
        
        # Safe admin seed
        from models.models import User
        from werkzeug.security import generate_password_hash
        
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("[DIAGNOSTICS] Creating default admin user...")
            db.session.add(User(
                username='admin', 
                email='admin@bookverse.com', 
                password_hash=generate_password_hash('admin123'), 
                role='admin', 
                full_name='BookVerse Admin'
            ))
            db.session.commit()
            
        print("[DIAGNOSTICS] Database ready.")
    except Exception as e:
        print(f"[DIAGNOSTICS] Startup DB Error (Ignore during build): {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
