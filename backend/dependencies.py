"""
dependencies.py
─────────────────────────────────────────────
Dépendance FastAPI partagée par toutes les routes :
identifie l'utilisateur courant à partir du token
envoyé dans le header "Authorization: Bearer <token>".

Logique :
- Token présent et valide → retourne l'utilisateur existant
- Token absent/invalide   → crée un utilisateur "anonyme"
                             + une nouvelle session, et les retourne

Voir routes/auth.py pour la création initiale du token anonyme.
─────────────────────────────────────────────
"""

from fastapi import Header, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import Utilisateur, Session as SessionModel, Parametre
from security import decoder_token, generer_token


def obtenir_utilisateur_courant(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
) -> Utilisateur:
    """
    Récupère l'utilisateur associé au token JWT.

    - Un token EST fourni mais invalide / expiré / sans session active en base
      → on lève une erreur 401 pour que le frontend redirige proprement vers
      la page de connexion. (NE PAS créer d'anonyme ici : sinon on détache
      l'utilisateur de ses conversations, ce qui provoquait des 404 silencieux
      sur l'envoi des messages — symptôme « pas de réponse » après un upload.)
    - AUCUN token n'est fourni → on crée un utilisateur anonyme
      (cohérent avec utilisateurs.type = "anonyme").
    """

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()

    # Le frontend envoie littéralement "Bearer null"/"Bearer undefined" quand
    # aucun token n'est en mémoire : on traite ces valeurs comme une absence.
    if token in ("", "null", "undefined", "None"):
        token = None

    # ── Cas 1 : un token est fourni → il DOIT être valide ──
    if token:
        payload = decoder_token(token)
        session = None
        if payload:
            session = db.query(SessionModel).filter(
                SessionModel.token == token,
                SessionModel.est_actif == True
            ).first()

        utilisateur = None
        if payload and session:
            utilisateur = db.query(Utilisateur).filter(
                Utilisateur.id == payload["utilisateur_id"],
                Utilisateur.est_actif == True
            ).first()

        if utilisateur:
            utilisateur.derniere_connexion = datetime.now()
            db.commit()
            return utilisateur

        # Token présent mais inexploitable : session expirée / révoquée /
        # base réinitialisée. On force une reconnexion au lieu de fabriquer
        # un utilisateur anonyme fantôme.
        raise HTTPException(
            status_code=401,
            detail="Session expirée ou invalide. Veuillez vous reconnecter."
        )

    # ── Cas 2 : aucun token fourni → on crée un utilisateur anonyme ──
    import uuid
    identifiant_unique = str(uuid.uuid4())[:8]
    nouvel_utilisateur = Utilisateur(
        nom="Utilisateur Anonyme",
        email=f"anonyme_{identifiant_unique}@chatbot.local",  # email unique requis (NOT NULL + UNIQUE)
        mot_de_passe="",
        type="anonyme",
        est_actif=True
    )
    db.add(nouvel_utilisateur)
    db.commit()
    db.refresh(nouvel_utilisateur)

    # Crée ses paramètres par défaut (relation 1→1)
    parametre = Parametre(utilisateur_id=nouvel_utilisateur.id)
    db.add(parametre)
    db.commit()

    return nouvel_utilisateur