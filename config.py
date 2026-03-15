import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # Handle Render's postgres:// format requirement for SQLAlchemy
    db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:1806@localhost:5432/bookverse')
    if db_url and db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    AI_MODELS_DIR = os.environ.get('AI_MODELS_DIR', basedir)