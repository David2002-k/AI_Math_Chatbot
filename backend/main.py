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


# 1bis. Initialisation automatique des données essentielles au démarrage :
#       les modèles IA et un compte administrateur par défaut. Cela évite
#       l'erreur « Email ou mot de passe incorrect » quand seed.py n'a pas
#       été lancé manuellement avant le serveur.
def initialiser_donnees_essentielles():
    from database import SessionLocal
    from security import hasher_mot_de_passe

    ADMIN_EMAIL = "admin@mathchatbot.com"
    ADMIN_MDP = "admin123"

    db = SessionLocal()
    try:
        if db.query(models.ModeleIA).count() == 0:
            db.add_all([
                models.ModeleIA(nom="Basique", description="Rapide et efficace.", modele_gemini="gemini-2.5-flash"),
                models.ModeleIA(nom="Pro", description="Plus puissant.", modele_gemini="gemini-2.5-pro"),
                models.ModeleIA(nom="Max", description="Le plus performant.", modele_gemini="gemini-2.5-pro"),
            ])
            db.commit()

        admin_user = db.query(models.Utilisateur).filter(
            models.Utilisateur.email == ADMIN_EMAIL
        ).first()
        if not admin_user:
            admin_user = models.Utilisateur(
                nom="Administrateur",
                email=ADMIN_EMAIL,
                mot_de_passe=hasher_mot_de_passe(ADMIN_MDP),
                type="authentifie",
                est_actif=True,
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            db.add(models.Parametre(utilisateur_id=admin_user.id))
            db.commit()

        if not db.query(models.Admin).filter(models.Admin.utilisateur_id == admin_user.id).first():
            db.add(models.Admin(utilisateur_id=admin_user.id, role="superadmin"))
            db.commit()
            print(f"👑 Compte administrateur prêt → {ADMIN_EMAIL} / {ADMIN_MDP}")
    except Exception as e:
        print(f"⚠️  Initialisation des données essentielles ignorée : {e}")
    finally:
        db.close()


initialiser_donnees_essentielles()

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

    dossier_uploads = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    os.makedirs(dossier_uploads, exist_ok=True)
    chemin_temp = os.path.join(dossier_uploads, f"tmp_{uuid.uuid4().hex}.wav")
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