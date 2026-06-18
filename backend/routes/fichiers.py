"""
routes/fichiers.py
─────────────────────────────────────────────
Upload de fichiers (table fichiers) :

POST /api/fichiers/upload   → upload jusqu'à 5 fichiers (PDF, image, DOCX)
                                liés à un message_id existant.

Le contenu est extrait et stocké dans fichiers.contenu_extrait
pour être envoyé à Gemini avec la question (voir routes/messages.py).
─────────────────────────────────────────────
"""

import os
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Fichier, Message, Chat, Utilisateur
from schemas import FichierReponse
from dependencies import obtenir_utilisateur_courant

router = APIRouter(prefix="/api/fichiers", tags=["Fichiers"])

DOSSIER_UPLOADS = "uploads"
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
    """
    Extrait le texte d'un fichier pour l'envoyer à Gemini.
    PDF/DOCX → extraction texte. Images → laissées vides ici,
    Gemini multimodal peut aussi les lire directement si besoin.
    """
    try:
        if extension == ".pdf":
            from pypdf import PdfReader
            lecteur = PdfReader(chemin)
            return "\n".join(page.extract_text() or "" for page in lecteur.pages)

        if extension == ".docx":
            from docx import Document
            doc = Document(chemin)
            return "\n".join(p.text for p in doc.paragraphs)

    except Exception:
        return ""

    return ""


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

    fichiers_crees = []

    for fichier in fichiers:
        extension = os.path.splitext(fichier.filename)[1].lower()

        if extension not in EXTENSIONS_AUTORISEES:
            raise HTTPException(
                status_code=400,
                detail=f"Type de fichier non autorisé : {extension}"
            )

        contenu_bytes = await fichier.read()

        if len(contenu_bytes) > TAILLE_MAX_OCTETS:
            raise HTTPException(status_code=400, detail=f"{fichier.filename} dépasse 10 Mo.")

        # Nom unique sur le serveur pour éviter les collisions
        nom_unique = f"{uuid.uuid4().hex}{extension}"
        chemin_complet = os.path.join(DOSSIER_UPLOADS, nom_unique)

        with open(chemin_complet, "wb") as f:
            f.write(contenu_bytes)

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
    for f in fichiers_crees:
        db.refresh(f)

    return fichiers_crees
