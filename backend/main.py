"""
backend/main.py
─────────────────────────────────────────────
Point d'entrée principal de l'API FastAPI.
Regroupe et enregistre proprement toutes les routes du Chatbot.
─────────────────────────────────────────────
"""

from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import shutil
import uuid

# Importation de la connexion à la base de données
from database import engine
import models

# Importation correcte des fichiers de routes (méthode explicite pour éviter les conflits d'attributs)
from routes.auth import router as auth_router
from routes.chats import router as chats_router
from routes.messages import router as messages_router
from routes.fichiers import router as fichiers_router
from routes.parametres import router as parametres_router
from routes.recherche import router as recherche_router
from routes.admin import router as admin_router

# 1. Création automatique des tables dans PostgreSQL au démarrage si elles n'existent pas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Math Chatbot API",
    description="Backend FastAPI avec support PostgreSQL et rendu KaTeX pour les mathématiques",
    version="1.0.0"
)

# 2. Configuration du CORS
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "null",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Enregistrement des routes avec leurs préfixes exacts
app.include_router(auth_router)
app.include_router(chats_router)
app.include_router(messages_router)
app.include_router(fichiers_router)
app.include_router(parametres_router)
app.include_router(recherche_router, prefix="/api")
app.include_router(admin_router, prefix="/api")

# 4. Route de test rapide
@app.get("/", tags=["Santé"])
def verifier_statut_api():
    return {
        "status": "online",
        "message": "Le serveur du Chatbot Mathématique fonctionne parfaitement.",
        "database": "PostgreSQL Connected"
    }

# 4bis. Transcription audio
@app.post("/api/transcribe", tags=["Audio"])
async def transcrire_audio(file: UploadFile = File(...)):
    from services.whisper_service import transcrire_audio_en_texte

    os.makedirs("uploads", exist_ok=True)
    chemin_temp = os.path.join("uploads", f"tmp_{uuid.uuid4().hex}.wav")
    with open(chemin_temp, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        texte = transcrire_audio_en_texte(chemin_temp)
    finally:
        if os.path.exists(chemin_temp):
            os.remove(chemin_temp)

    return {"text": texte}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)