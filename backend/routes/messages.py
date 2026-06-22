"""
routes/messages.py
─────────────────────────────────────────────
Gestion des messages (table messages) sécurisée et optimisée.
─────────────────────────────────────────────
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Message, Chat, Fichier, Utilisateur, ModeleIA
from schemas import MessageCreation, MessageReponse, MessageReaction
from dependencies import obtenir_utilisateur_courant

from services.gemini_service import generer_reponse, generer_reponse_stream, generer_titre_chat

router = APIRouter(prefix="/api/messages", tags=["Messages"])


# ── Préparation commune : sauvegarde le message utilisateur, rattache les
#    fichiers en attente, et détermine le modèle + l'historique à envoyer à Gemini ──
def _preparer_envoi(donnees: MessageCreation, utilisateur: Utilisateur, db: Session):
    chat = db.query(Chat).filter(
        Chat.id == donnees.chat_id,
        Chat.utilisateur_id == utilisateur.id
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")

    message_user = Message(
        chat_id=chat.id,
        modele_id=donnees.modele_id or chat.modele_id,
        role="user",
        contenu=donnees.contenu
    )
    db.add(message_user)
    db.commit()
    db.refresh(message_user)

    # Récupère les fichiers déjà liés à ce message, plus ceux uploadés
    # avant la création du message et rattachés temporairement à ce chat précis.
    fichiers = db.query(Fichier).filter(
        (Fichier.message_id == message_user.id) |
        ((Fichier.message_id == None) & (Fichier.chat_id == chat.id))
    ).all()

    contexte_fichiers = "\n".join(f.contenu_extrait for f in fichiers if f.contenu_extrait)
    # Les images ne sont pas extraites en texte : elles sont envoyées telles quelles
    # à Gemini (vision) pour qu'il puisse réellement "voir" les exercices photographiés.
    chemins_images = [f.chemin for f in fichiers if f.type_fichier == "image"]

    for f in fichiers:
        if f.message_id is None:
            f.message_id = message_user.id
    if fichiers:
        db.commit()

    nom_modele = "Basique"
    modele_id_utilise = donnees.modele_id or chat.modele_id
    if modele_id_utilise:
        modele_ia = db.query(ModeleIA).filter(ModeleIA.id == modele_id_utilise).first()
        if modele_ia:
            nom_modele = modele_ia.nom

    # Historique du chat (mémoire de conversation), EXCLUANT le message courant
    messages_precedents = db.query(Message).filter(
        Message.chat_id == chat.id,
        Message.id != message_user.id
    ).order_by(Message.date_creation.asc()).all()
    historique = [{"role": m.role, "contenu": m.contenu} for m in messages_precedents]

    return chat, message_user, nom_modele, modele_id_utilise, contexte_fichiers, historique, chemins_images


# ══════════════════════════════════════════════
# ENVOYER UN MESSAGE → RÉPONSE GEMINI (sans streaming, conservé pour compatibilité)
# ══════════════════════════════════════════════
@router.post("", response_model=MessageReponse)
def envoyer_message(
    donnees: MessageCreation,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    chat, message_user, nom_modele, modele_id_utilise, contexte_fichiers, historique, chemins_images = _preparer_envoi(donnees, utilisateur, db)

    try:
        resultat = generer_reponse(donnees.contenu, nom_modele, contexte_fichiers, historique, chemins_images)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Gemini : {str(e)}")

    message_ia = Message(
        chat_id=chat.id,
        modele_id=modele_id_utilise,
        role="assistant",
        contenu=resultat["texte"],
        tokens_utilises=resultat["tokens"]
    )
    db.add(message_ia)

    if chat.titre == "Nouvelle conversation" and not chat.titre_modifie:
        try:
            chat.titre = generer_titre_chat(donnees.contenu)
        except Exception:
            chat.titre = donnees.contenu[:30] + "..." if len(donnees.contenu) > 30 else donnees.contenu

    db.commit()
    db.refresh(message_ia)

    return message_ia


# ══════════════════════════════════════════════
# ENVOYER UN MESSAGE → RÉPONSE GEMINI EN STREAMING (effet de frappe en direct)
# ══════════════════════════════════════════════
@router.post("/stream")
def envoyer_message_stream(
    donnees: MessageCreation,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    chat, message_user, nom_modele, modele_id_utilise, contexte_fichiers, historique, chemins_images = _preparer_envoi(donnees, utilisateur, db)

    def flux_reponse():
        texte_complet = ""
        tokens = 0
        try:
            for morceau in generer_reponse_stream(donnees.contenu, nom_modele, contexte_fichiers, historique, chemins_images):
                if isinstance(morceau, tuple) and morceau[0] == "__usage__":
                    tokens = morceau[1]
                    continue
                texte_complet += morceau
                yield f"data: {json.dumps({'delta': morceau})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'erreur': str(e)})}\n\n"
            return

        # Sauvegarde la réponse complète une fois le flux terminé
        message_ia = Message(
            chat_id=chat.id,
            modele_id=modele_id_utilise,
            role="assistant",
            contenu=texte_complet,
            tokens_utilises=tokens
        )
        db.add(message_ia)

        nouveau_titre = None
        if chat.titre == "Nouvelle conversation" and not chat.titre_modifie:
            try:
                chat.titre = generer_titre_chat(donnees.contenu)
            except Exception:
                chat.titre = donnees.contenu[:30] + "..." if len(donnees.contenu) > 30 else donnees.contenu
            nouveau_titre = chat.titre

        db.commit()
        db.refresh(message_ia)

        yield f"data: {json.dumps({'fin': True, 'message_id': message_ia.id, 'titre': nouveau_titre})}\n\n"

    return StreamingResponse(flux_reponse(), media_type="text/event-stream")


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