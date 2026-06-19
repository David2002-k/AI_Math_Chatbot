"""
main.py
─────────────────────────────────────────────
Point d'entrée principal de l'API FastAPI.
Configuration du serveur, des middlewares et des routes.
─────────────────────────────────────────────
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Importation de la connexion BDD pour affichage au démarrage
from database import engine
from sqlalchemy.exc import OperationalError

# Importation des routeurs depuis le package 'routes'
from routes import auth, chats, messages, fichiers, parametres, recherche, admin

# Initialisation de l'application FastAPI
app = FastAPI(
    title="AI Math Chatbot API",
    description="Backend FastAPI pour l'application de Chatbot Mathématique avec support LaTeX",
    version="1.0.0"
)

# Configuration du Middleware CORS pour la communication avec le Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production (ex: ["http://localhost:3000"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Test de connexion à la base de données PostgreSQL au démarrage
try:
    with engine.connect() as connection:
        print("✅ Connexion à PostgreSQL réussie !")
except OperationalError as e:
    print(f"❌ Échec de la connexion à PostgreSQL : {str(e)}")

# Enregistrement des routes de l'API (sans le .router derrière car déjà aliasés)
app.include_router(auth)
app.include_router(chats)
app.include_router(messages)
app.include_router(fichiers)
app.include_router(parametres)
app.include_router(recherche)
app.include_router(admin)

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "Bienvenue sur l'API du AI Math Chatbot. Accédez à la documentation sur /docs"
    }