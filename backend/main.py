"""
main.py
─────────────────────────────────────────────
Point d'entrée du serveur FastAPI.

Au démarrage :
- crée les tables de la base de données si elles n'existent pas
- configure le CORS (autorise le frontend à appeler l'API)
- branche les routes (routes/)

Lancer le serveur :
    uvicorn main:app --reload --port 8000

Documentation interactive :
    http://localhost:8000/docs
─────────────────────────────────────────────
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine

# Crée toutes les tables définies dans models.py (si absentes)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Math Chatbot API",
    description="API pour l'agent conversationnel mathématique intelligent",
    version="1.0.0"
)

# ── CORS ──────────────────────────────────────
# Autorise le frontend (Bootstrap, servi sur un autre port)
# à communiquer avec ce backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # à restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Route de test ─────────────────────────────
@app.get("/")
def accueil():
    """Vérifie que l'API fonctionne."""
    return {"message": "AI Math Chatbot API opérationnelle 🚀"}


# ── Branchement des routes ─────────────────────
from routes import auth, chats, messages, fichiers, parametres

app.include_router(auth.router)
app.include_router(chats.router)
app.include_router(messages.router)
app.include_router(fichiers.router)
app.include_router(parametres.router)
app.include_router(parametres.router_modeles)
