"""
database.py
─────────────────────────────────────────────
Connexion à la base de données PostgreSQL.

Ce fichier crée :
- le moteur de connexion (engine)
- la fabrique de sessions (SessionLocal)
- la classe de base pour tous les modèles (Base)
- la fonction get_db() utilisée par FastAPI
─────────────────────────────────────────────
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Charge les variables du fichier .env
load_dotenv()

# Récupération des identifiants découpés (méthode propre de votre collaborateur)
DB_USER = os.getenv("DB_USER", "mathuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mathpassword")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mathchatbot")

# Reconstruction de l'URL PostgreSQL officielle pour SQLAlchemy
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Moteur de connexion à la base de données
engine = create_engine(DATABASE_URL)

# Test de connexion rapide au démarrage pour vérifier que PostgreSQL répond
try:
    connection = engine.connect()
    print("✅ Connexion à PostgreSQL réussie !")
    connection.close()
except Exception as e:
    print(f"❌ Erreur de connexion à PostgreSQL : {e}")

# Fabrique de sessions — chaque requête API aura sa propre session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe de base — tous les modèles (models.py) en hériteront
Base = declarative_base()


def get_db():
    """
    Dépendance FastAPI.
    Ouvre une session de base de données, la fournit à la route,
    puis la ferme automatiquement à la fin.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()