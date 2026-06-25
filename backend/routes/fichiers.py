"""
routes/fichiers.py
─────────────────────────────────────────────
Upload de fichiers (table fichiers) sécurisé et corrigé.
─────────────────────────────────────────────
"""

import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Fichier, Message, Chat, Utilisateur
from schemas import FichierReponse
from dependencies import obtenir_utilisateur_courant

router = APIRouter(prefix="/api/fichiers", tags=["Fichiers"])

# Dossier d'upload ancré au répertoire du backend (et non au répertoire courant
# du processus). Sans cela, si uvicorn est lancé depuis la racine du projet,
# les fichiers étaient écrits/lus à un autre endroit et Gemini ne « voyait »
# plus les images : l'upload semblait fonctionner mais restait sans effet.
_DOSSIER_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER_UPLOADS = os.path.join(_DOSSIER_BACKEND, "uploads")
EXTENSIONS_AUTORISEES = {".pdf", ".jpg", ".jpeg", ".png", ".docx"}
TAILLE_MAX_OCTETS = 10 * 1024 * 1024  # 10 Mo par fichier
MAX_FICHIERS = 5

os.makedirs(DOSSIER_UPLOADS, exist_ok=True)


def _type_fichier(extension: str) -> str:
    if extension == ".pdf":
        return "pdf"
    if extension in (".jpg", ".jpeg", ".png"):
        return "image"
    if extension == ".docx":
        return "docx"
    return "inconnu"


def _extraire_contenu(chemin: str, extension: str) -> str:
    """ Extrait le texte d'un fichier de mathématiques pour l'envoyer à Gemini. """
    try:
        if extension == ".pdf":
            from pypdf import PdfReader
            lecteur = PdfReader(chemin)
            return "\n".join(page.extract_text() or "" for page in lecteur.pages)

        if extension == ".docx":
            from docx import Document
            doc = Document(chemin)
            return "\n".join(p.text for p in doc.paragraphs)

    except Exception as e:
        print(f"Erreur d'extraction sur {chemin}: {str(e)}")
        return ""

    return ""


@router.post("", response_model=FichierReponse)
async def uploader_fichier(
    chat_id: int = Form(...),
    file: UploadFile = File(...),
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    """Upload un fichier lié à une conversation, avant que le message ne soit créé.
    Le fichier sera rattaché au message dès l'envoi du message (voir routes/messages.py)."""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.utilisateur_id == utilisateur.id
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")

    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in EXTENSIONS_AUTORISEES:
        raise HTTPException(status_code=400, detail=f"Type de fichier non autorisé : {extension}")

    contenu_bytes = await file.read()
    if len(contenu_bytes) > TAILLE_MAX_OCTETS:
        raise HTTPException(status_code=400, detail=f"{file.filename} dépasse les 10 Mo autorisés.")

    nom_unique = f"{uuid.uuid4().hex}{extension}"
    chemin_complet = os.path.join(DOSSIER_UPLOADS, nom_unique)

    with open(chemin_complet, "wb") as f:
        f.write(contenu_bytes)
        f.flush()
        os.fsync(f.fileno())

    contenu_extrait = _extraire_contenu(chemin_complet, extension)

    fichier_db = Fichier(
        message_id=None,
        chat_id=chat_id,
        nom_original=file.filename,
        nom_fichier=nom_unique,
        type_fichier=_type_fichier(extension),
        taille=len(contenu_bytes),
        chemin=chemin_complet,
        contenu_extrait=contenu_extrait
    )
    db.add(fichier_db)
    db.commit()
    db.refresh(fichier_db)
    return fichier_db


@router.delete("/{fichier_id}")
def supprimer_fichier(
    fichier_id: int,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    """Retire un fichier joint AVANT l'envoi du message (badge ✕ côté interface).

    On ne peut supprimer qu'un fichier encore « en attente » (non rattaché à un
    message déjà envoyé) et appartenant à une conversation de l'utilisateur, afin
    de ne jamais altérer l'historique d'un message existant."""
    fichier = (
        db.query(Fichier)
        .join(Chat, Fichier.chat_id == Chat.id)
        .filter(
            Fichier.id == fichier_id,
            Fichier.message_id == None,
            Chat.utilisateur_id == utilisateur.id,
        )
        .first()
    )
    if not fichier:
        raise HTTPException(status_code=404, detail="Fichier introuvable ou déjà envoyé.")

    # Supprime le fichier physique du disque s'il existe encore.
    try:
        if fichier.chemin and os.path.exists(fichier.chemin):
            os.remove(fichier.chemin)
    except OSError as e:
        print(f"Suppression disque impossible pour {fichier.chemin}: {e}")

    db.delete(fichier)
    db.commit()
    return {"detail": "Fichier supprimé."}


@router.post("/upload", response_model=list[FichierReponse])
async def uploader_fichiers(
    message_id: int,
    fichiers: list[UploadFile] = File(...),
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    # Vérifie que le message appartient bien à l'utilisateur
    message = db.query(Message).join(Chat).filter(
        Message.id == message_id,
        Chat.utilisateur_id == utilisateur.id
    ).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message introuvable.")

    if len(fichiers) > MAX_FICHIERS:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FICHIERS} fichiers autorisés.")

    # ÉTAPE 1 : Pré-vérification de TOURS les fichiers avant écriture (Évite les fichiers orphelins)
    for fichier in fichiers:
        extension = os.path.splitext(fichier.filename)[1].lower()
        if extension not in EXTENSIONS_AUTORISEES:
            raise HTTPException(
                status_code=400,
                detail=f"Type de fichier non autorisé dans {fichier.filename} : {extension}"
            )

    fichiers_crees = []

    # ÉTAPE 2 : Traitement et écriture sécurisée
    for fichier in fichiers:
        extension = os.path.splitext(fichier.filename)[1].lower()
        contenu_bytes = await fichier.read()

        if len(contenu_bytes) > TAILLE_MAX_OCTETS:
            raise HTTPException(status_code=400, detail=f"{fichier.filename} dépasse les 10 Mo autorisés.")

        # Nom unique sur le serveur pour éviter les collisions
        nom_unique = f"{uuid.uuid4().hex}{extension}"
        chemin_complet = os.path.join(DOSSIER_UPLOADS, nom_unique)

        # block with/open garantit la fermeture complète du fichier à la sortie
        with open(chemin_complet, "wb") as f:
            f.write(contenu_bytes)
            f.flush() # Force l'écriture immédiate sur le disque dur
            os.fsync(f.fileno()) # Aligne le système d'exploitation

        # L'extraction peut maintenant lire le fichier fermé en toute sécurité
        contenu_extrait = _extraire_contenu(chemin_complet, extension)

        fichier_db = Fichier(
            message_id=message_id,
            nom_original=fichier.filename,
            nom_fichier=nom_unique,
            type_fichier=_type_fichier(extension),
            taille=len(contenu_bytes),
            chemin=chemin_complet,
            contenu_extrait=contenu_extrait
        )
        db.add(fichier_db)
        fichiers_crees.append(fichier_db)

    db.commit()
    
    # Rafraîchissement des instances SQLAlchemy
    for f in fichiers_crees:
        db.refresh(f)

    return fichiers_crees