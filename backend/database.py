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

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Charge les variables du fichier .env
load_dotenv()

# URL de connexion — vient de docker-compose.yml ou .env
# URL de connexion — connexion directe à PostgreSQL local (sans Docker)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mathuser:mathpassword@localhost:5432/mathchatbot"
)

# Moteur de connexion à la base de données
engine = create_engine(DATABASE_URL)

# Fabrique de sessions — chaque requête API aura sa propre session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe de base — tous les modèles (models.py) en hériteront
Base = declarative_base()


def get_db():
    """
    Dépendance FastAPI.
    Ouvre une session de base de données, la fournit à la route,
    puis la ferme automatiquement à la fin (même en cas d'erreur).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
