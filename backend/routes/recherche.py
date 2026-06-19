"""
backend/routes/recherche.py
─────────────────────────────────────────────
Points d'accès (Endpoints) pour la recherche de messages ou formules.
─────────────────────────────────────────────
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# CORRECTION : Retrait de 'backend.' pour correspondre au contexte d'exécution
from database import get_db
import models

router = APIRouter(
    prefix="/recherche",
    tags=["Recherche"]
)

@router.get("/")
def rechercher_messages(q: str, db: Session = Depends(get_db)):
    """
    Recherche un terme ou une formule LaTeX dans la base de données.
    URL : GET /api/recherche/?q=terme_a_chercher
    """
    # CORRECTION : On applique .strip() sur la chaîne q avant de vérifier sa longueur
    if not q or len(q.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le terme de recherche doit contenir au moins 2 caractères."
        )
        
    # Recherche insensible à la casse (%q% permet de chercher n'importe où dans le texte)
    resultats = db.query(models.Message).filter(
        models.Message.contenu.ilike(f"%{q}%")
    ).limit(50).all()
    
    # Transformation des résultats en un format JSON propre pour le frontend
    retour = []
    for msg in resultats:
        retour.append({
            "id": msg.id,
            "chat_id": msg.chat_id,
            "role": msg.role,          # 'user' ou 'assistant'
            "contenu": msg.contenu,    # Le texte (avec les formules LaTeX)
            "cree_le": msg.cree_le
        })
        
    return {"status": "success", "count": len(retour), "results": retour}