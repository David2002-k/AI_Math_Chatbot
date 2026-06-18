"""
routes/chats.py
─────────────────────────────────────────────
Gestion des conversations (table chats) :

POST   /api/chats                 → créer une nouvelle conversation
GET    /api/chats                 → lister l'historique (épinglés/récents/archivés)
GET    /api/chats/{id}             → récupérer une conversation + ses messages
PATCH  /api/chats/{id}              → renommer / épingler / archiver
DELETE /api/chats/{id}                → supprimer une conversation
GET    /api/chats/recherche?q=...      → rechercher dans l'historique
─────────────────────────────────────────────
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime

from database import get_db
from models import Chat, Message, Utilisateur, Recherche
from schemas import ChatCreation, ChatModification, ChatReponse, MessageReponse
from dependencies import obtenir_utilisateur_courant

router = APIRouter(prefix="/api/chats", tags=["Chats"])


# ══════════════════════════════════════════════
# CRÉER UNE CONVERSATION
# ══════════════════════════════════════════════
@router.post("", response_model=ChatReponse)
def creer_chat(
    donnees: ChatCreation,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    chat = Chat(
        utilisateur_id=utilisateur.id,
        titre=donnees.titre or "Nouvelle conversation",
        modele_id=donnees.modele_id
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


# ══════════════════════════════════════════════
# LISTER L'HISTORIQUE (épinglés, récents, archivés)
# ══════════════════════════════════════════════
@router.get("", response_model=list[ChatReponse])
def lister_chats(
    archives: bool = False,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    """
    Par défaut retourne les chats actifs (épinglés en premier).
    Passer ?archives=true pour voir les conversations archivées.
    """
    chats = db.query(Chat).filter(
        Chat.utilisateur_id == utilisateur.id,
        Chat.est_archive == archives
    ).order_by(
        Chat.est_epingle.desc(),
        Chat.date_modification.desc()
    ).all()

    return chats


# ══════════════════════════════════════════════
# RECHERCHER DANS L'HISTORIQUE
# ══════════════════════════════════════════════
@router.get("/recherche", response_model=list[ChatReponse])
def rechercher_chats(
    q: str,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    """Filtre les conversations par mot-clé dans le titre, et sauvegarde la recherche."""
    # Sauvegarde dans la table recherches (historique des recherches)
    db.add(Recherche(utilisateur_id=utilisateur.id, mot_cle=q))
    db.commit()

    resultats = db.query(Chat).filter(
        Chat.utilisateur_id == utilisateur.id,
        Chat.titre.ilike(f"%{q}%")
    ).order_by(Chat.date_modification.desc()).all()

    return resultats


# ══════════════════════════════════════════════
# RÉCUPÉRER UNE CONVERSATION + SES MESSAGES
# ══════════════════════════════════════════════
@router.get("/{chat_id}", response_model=list[MessageReponse])
def obtenir_messages_chat(
    chat_id: int,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    chat = _verifier_proprietaire(chat_id, utilisateur, db)

    messages = db.query(Message).filter(
        Message.chat_id == chat.id
    ).order_by(Message.date_creation.asc()).all()

    return messages


# ══════════════════════════════════════════════
# RENOMMER / ÉPINGLER / ARCHIVER
# ══════════════════════════════════════════════
@router.patch("/{chat_id}", response_model=ChatReponse)
def modifier_chat(
    chat_id: int,
    donnees: ChatModification,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    chat = _verifier_proprietaire(chat_id, utilisateur, db)

    if donnees.titre is not None:
        chat.titre = donnees.titre
        chat.titre_modifie = True  # l'utilisateur a renommé manuellement

    if donnees.est_epingle is not None:
        chat.est_epingle = donnees.est_epingle

    if donnees.est_archive is not None:
        chat.est_archive = donnees.est_archive

    if donnees.modele_id is not None:
        chat.modele_id = donnees.modele_id

    chat.date_modification = datetime.now()
    db.commit()
    db.refresh(chat)
    return chat


# ══════════════════════════════════════════════
# SUPPRIMER UNE CONVERSATION
# ══════════════════════════════════════════════
@router.delete("/{chat_id}")
def supprimer_chat(
    chat_id: int,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    chat = _verifier_proprietaire(chat_id, utilisateur, db)

    db.delete(chat)  # cascade supprime aussi messages + fichiers liés
    db.commit()
    return {"message": "Conversation supprimée."}


# ── Fonction utilitaire interne ──────────────────
def _verifier_proprietaire(chat_id: int, utilisateur: Utilisateur, db: Session) -> Chat:
    """Vérifie que le chat existe et appartient bien à l'utilisateur courant."""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.utilisateur_id == utilisateur.id
    ).first()

    if not chat:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")

    return chat
