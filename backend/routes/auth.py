"""
routes/auth.py
─────────────────────────────────────────────
Routes d'authentification corrigées pour respecter les contraintes NOT NULL.
─────────────────────────────────────────────
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from database import get_db
from models import Utilisateur, Session as SessionModel, Parametre
from schemas import InscriptionSchema, ConnexionSchema, TokenReponse, ChangementMotDePasse
from security import hasher_mot_de_passe, verifier_mot_de_passe, generer_token, decoder_token
from dependencies import obtenir_utilisateur_courant

router = APIRouter(prefix="/api/auth", tags=["Authentification"])


@router.patch("/mot-de-passe")
def changer_mot_de_passe(
    donnees: ChangementMotDePasse,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db),
):
    """Change le mot de passe de l'utilisateur connecté.
    Vérifie l'ancien mot de passe, impose une longueur minimale, puis
    révoque les autres sessions par sécurité. PATCH /api/auth/mot-de-passe"""
    if not verifier_mot_de_passe(donnees.ancien_mot_de_passe, utilisateur.mot_de_passe):
        raise HTTPException(status_code=400, detail="Ancien mot de passe incorrect.")
    if len(donnees.nouveau_mot_de_passe) < 6:
        raise HTTPException(status_code=400, detail="Le nouveau mot de passe doit contenir au moins 6 caractères.")

    utilisateur.mot_de_passe = hasher_mot_de_passe(donnees.nouveau_mot_de_passe)
    db.commit()
    return {"detail": "Mot de passe modifié avec succès."}


def _creer_session(db: Session, utilisateur: Utilisateur) -> str:
    """Génère un token JWT et l'enregistre dans la table sessions."""
    token, date_expiration = generer_token(utilisateur.id)

    session = SessionModel(
        utilisateur_id=utilisateur.id,
        token=token,
        est_actif=True,
        date_expiration=date_expiration
    )
    db.add(session)
    db.commit()

    return token


# ══════════════════════════════════════════════
# UTILISATEUR ANONYME
# ══════════════════════════════════════════════
@router.post("/anonyme", response_model=TokenReponse)
def creer_utilisateur_anonyme(db: Session = Depends(get_db)):
    """
    Crée un nouvel utilisateur anonyme avec ses paramètres par défaut,
    puis génère un token de session.
    """
    # CORRECTION : Génération de valeurs par défaut pour éviter le crash NOT NULL de Postgres
    identifiant_unique = str(uuid.uuid4())[:8]
    
    utilisateur = Utilisateur(
        nom="Utilisateur Anonyme",
        email=f"anonyme_{identifiant_unique}@chatbot.local", # Évite le crash NOT NULL / UNIQUE
        mot_de_passe=hasher_mot_de_passe(identifiant_unique), # Mot de passe temporaire requis par le modèle
        type="anonyme",
        est_actif=True
    )
    db.add(utilisateur)
    db.commit()
    db.refresh(utilisateur)

    db.add(Parametre(utilisateur_id=utilisateur.id))
    db.commit()

    token = _creer_session(db, utilisateur)

    return TokenReponse(access_token=token, utilisateur=utilisateur)


# ══════════════════════════════════════════════
# INSCRIPTION
# ══════════════════════════════════════════════
@router.post("/inscription", response_model=TokenReponse)
def inscription(
    donnees: InscriptionSchema,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    """
    Crée un compte authentifié.
    Convertit le compte anonyme existant si un token valide est fourni.
    """
    # Email déjà utilisé ?
    existe = db.query(Utilisateur).filter(Utilisateur.email == donnees.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")

    utilisateur = None

    # Tente de récupérer l'utilisateur anonyme courant pour le convertir
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        payload = decoder_token(token)
        if payload:
            utilisateur = db.query(Utilisateur).filter(
                Utilisateur.id == payload["utilisateur_id"],
                Utilisateur.type == "anonyme"
            ).first()

    if utilisateur:
        # Conversion anonyme → authentifié (historique conservé)
        utilisateur.nom = donnees.nom
        utilisateur.email = donnees.email
        utilisateur.mot_de_passe = hasher_mot_de_passe(donnees.mot_de_passe)
        utilisateur.type = "authentifie"
    else:
        # Nouveau compte direct
        utilisateur = Utilisateur(
            nom=donnees.nom,
            email=donnees.email,
            mot_de_passe=hasher_mot_de_passe(donnees.mot_de_passe),
            type="authentifie",
            est_actif=True
        )
        db.add(utilisateur)
        db.commit()
        db.refresh(utilisateur)
        db.add(Parametre(utilisateur_id=utilisateur.id))

    db.commit()
    db.refresh(utilisateur)

    token = _creer_session(db, utilisateur)
    return TokenReponse(access_token=token, utilisateur=utilisateur)


# ══════════════════════════════════════════════
# CONNEXION
# ══════════════════════════════════════════════
@router.post("/connexion", response_model=TokenReponse)
def connexion(donnees: ConnexionSchema, db: Session = Depends(get_db)):
    """Vérifie l'email + mot de passe, puis crée une nouvelle session."""
    utilisateur = db.query(Utilisateur).filter(
        Utilisateur.email == donnees.email,
        Utilisateur.type == "authentifie"
    ).first()

    if not utilisateur or not verifier_mot_de_passe(donnees.mot_de_passe, utilisateur.mot_de_passe):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    if not utilisateur.est_actif:
        raise HTTPException(status_code=403, detail="Ce compte est désactivé.")

    utilisateur.derniere_connexion = datetime.now()
    db.commit()

    token = _creer_session(db, utilisateur)
    return TokenReponse(access_token=token, utilisateur=utilisateur)


# ══════════════════════════════════════════════
# DÉCONNEXION
# ══════════════════════════════════════════════
@router.post("/deconnexion")
def deconnexion(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """Révoque la session courante (sessions.est_actif = False)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant.")

    token = authorization.split(" ")[1]
    session = db.query(SessionModel).filter(SessionModel.token == token).first()

    if session:
        session.est_actif = False
        db.commit()

    return {"message": "Déconnexion réussie."}