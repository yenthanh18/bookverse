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
        
        from models.models import Book
        if not Book.query.first():
            print("[SEED] Books table empty, starting import...")
            from seed.seed_books import seed_database
            seed_database()
            print("[SEED] Categories/Authors/Publishers ready")
            
        import pickle
        import os
        base_dir = app.config.get('AI_MODELS_DIR', '.')
        vectorizer_path = os.path.join(base_dir, 'chatbot_vectorizer.pkl')
        rebuild_needed = False
        if not os.path.exists(vectorizer_path):
            rebuild_needed = True
        else:
            try:
                with open(vectorizer_path, 'rb') as f:
                    pickle.load(f)
            except Exception as e:
                print(f"[AI BUILD] Error loading artifacts: {e}. Forcing rebuild.")
                rebuild_needed = True
                
        if rebuild_needed:
            from seed.build_ai_models import build_models
            build_models()
            
    except Exception as e:
        print(f"[DIAGNOSTICS] Startup Error (Ignore during initial build metadata parsing): {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
