import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:1806@localhost:5432/bookverse'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    AI_MODELS_DIR = os.environ.get('AI_MODELS_DIR', basedir)