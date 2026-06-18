"""
routes/messages.py
─────────────────────────────────────────────
Gestion des messages (table messages) :

POST  /api/messages              → envoyer un message, obtenir la réponse IA
PATCH /api/messages/{id}/reaction  → like / dislike sur une réponse IA
─────────────────────────────────────────────
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Message, Chat, Fichier, Utilisateur, ModeleIA
from schemas import MessageCreation, MessageReponse, MessageReaction
from dependencies import obtenir_utilisateur_courant
from gemini_service import generer_reponse, generer_titre_chat

router = APIRouter(prefix="/api/messages", tags=["Messages"])


# ══════════════════════════════════════════════
# ENVOYER UN MESSAGE → RÉPONSE GEMINI
# ══════════════════════════════════════════════
@router.post("", response_model=MessageReponse)
def envoyer_message(
    donnees: MessageCreation,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    # Vérifie que le chat appartient bien à l'utilisateur
    chat = db.query(Chat).filter(
        Chat.id == donnees.chat_id,
        Chat.utilisateur_id == utilisateur.id
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")

    # ── 1. Sauvegarde le message de l'utilisateur ──
    message_user = Message(
        chat_id=chat.id,
        modele_id=donnees.modele_id or chat.modele_id,
        role="user",
        contenu=donnees.contenu
    )
    db.add(message_user)
    db.commit()
    db.refresh(message_user)

    # Récupère le contenu extrait des fichiers déjà liés à ce message (s'il y en a)
    fichiers = db.query(Fichier).filter(Fichier.message_id == message_user.id).all()
    contexte_fichiers = "\n".join(f.contenu_extrait for f in fichiers if f.contenu_extrait)

    # ── 2. Détermine quel modèle IA utiliser ──
    nom_modele = "Basique"
    modele_id_utilise = donnees.modele_id or chat.modele_id
    if modele_id_utilise:
        modele_ia = db.query(ModeleIA).filter(ModeleIA.id == modele_id_utilise).first()
        if modele_ia:
            nom_modele = modele_ia.nom

    # ── 3. Appelle Gemini ──
    try:
        resultat = generer_reponse(donnees.contenu, nom_modele, contexte_fichiers)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Gemini : {str(e)}")

    # ── 4. Sauvegarde la réponse de l'IA ──
    message_ia = Message(
        chat_id=chat.id,
        modele_id=modele_id_utilise,
        role="assistant",
        contenu=resultat["texte"],
        tokens_utilises=resultat["tokens"]
    )
    db.add(message_ia)

    # ── 5. Si c'est le 1er message du chat → génère le titre automatiquement ──
    nb_messages = db.query(Message).filter(Message.chat_id == chat.id).count()
    if nb_messages <= 1 and not chat.titre_modifie:
        chat.titre = generer_titre_chat(donnees.contenu)

    db.commit()
    db.refresh(message_ia)

    return message_ia


# ══════════════════════════════════════════════
# RÉACTION SUR UN MESSAGE (like / dislike)
# ══════════════════════════════════════════════
@router.patch("/{message_id}/reaction", response_model=MessageReponse)
def reagir_message(
    message_id: int,
    donnees: MessageReaction,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    message = db.query(Message).join(Chat).filter(
        Message.id == message_id,
        Chat.utilisateur_id == utilisateur.id
    ).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message introuvable.")

    message.reaction = donnees.reaction
    db.commit()
    db.refresh(message)
    return message
