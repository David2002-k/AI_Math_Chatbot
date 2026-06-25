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


def _construire_url_postgres() -> str:
    """
    Construit l'URL de connexion PostgreSQL.
    Priorité à la variable DATABASE_URL (méthode standard, cohérente avec .env.example),
    sinon reconstruction à partir des identifiants découpés.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    db_user = os.getenv("DB_USER", "mathuser")
    db_password = os.getenv("DB_PASSWORD", "mathpassword")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "mathchatbot")
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


# URL SQLite locale utilisée comme repli automatique (aucune installation requise).
SQLITE_URL = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'mathchatbot.db')}"


def _creer_engine(url: str):
    """Crée un engine SQLAlchemy avec les bons arguments selon le type de base."""
    if url.startswith("sqlite"):
        # check_same_thread=False : nécessaire pour FastAPI (multi-thread).
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url)


# 1) On tente PostgreSQL (configuration de production)...
DATABASE_URL = _construire_url_postgres()
engine = _creer_engine(DATABASE_URL)

try:
    connection = engine.connect()
    connection.close()
    print("✅ Connexion à PostgreSQL réussie !")
except Exception as e:
    # 2) ...sinon repli transparent sur SQLite pour que l'application fonctionne
    #    immédiatement, même sans serveur PostgreSQL installé.
    print(f"⚠️  PostgreSQL indisponible ({e.__class__.__name__}). Bascule sur SQLite.")
    DATABASE_URL = SQLITE_URL
    engine = _creer_engine(DATABASE_URL)
    print(f"✅ Base SQLite locale prête : {DATABASE_URL}")

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