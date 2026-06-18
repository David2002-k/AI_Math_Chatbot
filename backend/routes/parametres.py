"""
routes/parametres.py
─────────────────────────────────────────────
Gestion des préférences utilisateur (table parametres) :

GET   /api/parametres   → récupérer mes préférences
PATCH /api/parametres   → modifier thème / langue / modèle par défaut
GET   /api/modeles       → lister les modèles IA disponibles (Basique/Pro/Max)
─────────────────────────────────────────────
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import Parametre, Utilisateur, ModeleIA
from schemas import ParametreModification, ParametreReponse, ModeleIAReponse
from dependencies import obtenir_utilisateur_courant

router = APIRouter(prefix="/api/parametres", tags=["Paramètres"])
router_modeles = APIRouter(prefix="/api/modeles", tags=["Modèles IA"])


@router.get("", response_model=ParametreReponse)
def obtenir_parametres(
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    parametre = db.query(Parametre).filter(Parametre.utilisateur_id == utilisateur.id).first()

    if not parametre:
        # Sécurité : crée les paramètres par défaut s'ils manquent
        parametre = Parametre(utilisateur_id=utilisateur.id)
        db.add(parametre)
        db.commit()
        db.refresh(parametre)

    return parametre


@router.patch("", response_model=ParametreReponse)
def modifier_parametres(
    donnees: ParametreModification,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db)
):
    parametre = db.query(Parametre).filter(Parametre.utilisateur_id == utilisateur.id).first()

    if donnees.theme is not None:
        parametre.theme = donnees.theme
    if donnees.langue is not None:
        parametre.langue = donnees.langue
    if donnees.modele_id is not None:
        parametre.modele_id = donnees.modele_id

    parametre.date_modification = datetime.now()
    db.commit()
    db.refresh(parametre)
    return parametre


@router_modeles.get("", response_model=list[ModeleIAReponse])
def lister_modeles(db: Session = Depends(get_db)):
    """Retourne les 3 niveaux IA actifs (Basique / Pro / Max)."""
    return db.query(ModeleIA).filter(ModeleIA.est_actif == True).all()
