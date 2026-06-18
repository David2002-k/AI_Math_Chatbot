"""
schemas.py
─────────────────────────────────────────────
Schémas Pydantic — définissent la forme des données
échangées entre le frontend et l'API (JSON).

FastAPI utilise ces classes pour :
- valider automatiquement les données reçues
- générer la documentation interactive (/docs)
- sérialiser les réponses envoyées au frontend
─────────────────────────────────────────────
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


# ── UTILISATEURS ──────────────────────────────
class InscriptionSchema(BaseModel):
    nom: str
    email: EmailStr
    mot_de_passe: str


class ConnexionSchema(BaseModel):
    email: EmailStr
    mot_de_passe: str


class UtilisateurReponse(BaseModel):
    id: int
    nom: str
    email: Optional[str] = None
    type: str
    photo_profil: Optional[str] = None

    class Config:
        from_attributes = True


class TokenReponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    utilisateur: UtilisateurReponse


# ── CHATS ──────────────────────────────────────
class ChatCreation(BaseModel):
    titre: Optional[str] = "Nouvelle conversation"
    modele_id: Optional[int] = None


class ChatModification(BaseModel):
    titre: Optional[str] = None
    est_epingle: Optional[bool] = None
    est_archive: Optional[bool] = None
    modele_id: Optional[int] = None


class ChatReponse(BaseModel):
    id: int
    titre: str
    titre_modifie: bool
    est_epingle: bool
    est_archive: bool
    date_creation: datetime
    date_modification: datetime

    class Config:
        from_attributes = True


# ── MESSAGES ───────────────────────────────────
class MessageCreation(BaseModel):
    chat_id: int
    contenu: str
    modele_id: Optional[int] = None


class MessageReaction(BaseModel):
    reaction: Optional[str] = None  # "like" | "dislike" | None


class MessageReponse(BaseModel):
    id: int
    chat_id: int
    role: str
    contenu: str
    reaction: Optional[str] = None
    tokens_utilises: int
    date_creation: datetime

    class Config:
        from_attributes = True


# ── FICHIERS ───────────────────────────────────
class FichierReponse(BaseModel):
    id: int
    nom_original: str
    type_fichier: str
    taille: int
    date_upload: datetime

    class Config:
        from_attributes = True


# ── PARAMETRES ─────────────────────────────────
class ParametreModification(BaseModel):
    theme: Optional[str] = None       # "clair" | "sombre"
    langue: Optional[str] = None      # "fr" | "en"
    modele_id: Optional[int] = None


class ParametreReponse(BaseModel):
    theme: str
    langue: str
    modele_id: Optional[int] = None

    class Config:
        from_attributes = True


# ── MODELES IA ─────────────────────────────────
class ModeleIAReponse(BaseModel):
    id: int
    nom: str
    description: Optional[str] = None
    est_actif: bool

    class Config:
        from_attributes = True
