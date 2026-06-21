"""
routes/parametres.py
─────────────────────────────────────────────
Gestion des préférences utilisateur et modèles IA (table parametres & modeles_ia).
─────────────────────────────────────────────
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import Parametre, Utilisateur, ModeleIA
from schemas import ParametreModification, ParametreReponse, ModeleIAReponse
from dependencies import obtenir_utilisateur_courant

# Un seul routeur de base, on gèrera le préfixe propre à chaque groupe de routes
router = APIRouter()


# ══════════════════════════════════════════════
# GESTION DES PRÉFÉRENCES (Prefix: /api/parametres)
# ══════════════════════════════════════════════

@router.get("/api/parametres", response_model=ParametreReponse, tags=["Paramètres"])
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


@router.patch("/api/parametres", response_model=ParametreReponse, tags=["Paramètres"])
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


# ══════════════════════════════════════════════
# MODÈLES IA (Prefix: /api/modeles)
# ══════════════════════════════════════════════

@router.get("/api/modeles", response_model=list[ModeleIAReponse], tags=["Modèles IA"])
def lister_modeles(db: Session = Depends(get_db)):
    """Retourne les 3 niveaux IA actifs (Basique / Pro / Max)."""
    return db.query(ModeleIA).filter(ModeleIA.est_actif == True).all()