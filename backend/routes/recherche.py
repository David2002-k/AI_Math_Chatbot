"""
backend/routes/recherche.py
─────────────────────────────────────────────
Points d'accès (Endpoints) pour la recherche de messages ou formules corrigés.
─────────────────────────────────────────────
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models

router = APIRouter(
    prefix="/recherche",
    tags=["Recherche"]
)

@router.get("/")
def rechercher_messages(q: str = "", db: Session = Depends(get_db)):
    """
    Recherche un terme ou une formule LaTeX dans la base de données.
    URL : GET /api/recherche/?q=terme_a_chercher
    """
    # CORRECTION : Sécurité si q est None + application du strip()
    terme = q.strip() if q else ""
    
    if len(terme) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le terme de recherche doit contenir au moins 2 caractères."
        )
        
    # Recherche insensible à la casse dans le contenu des messages
    resultats = db.query(models.Message).filter(
        models.Message.contenu.ilike(f"%{terme}%")
    ).limit(50).all()
    
    # Transformation des résultats en un format JSON propre pour le frontend
    retour = []
    for msg in resultats:
        retour.append({
            "id": msg.id,
            "chat_id": msg.chat_id,
            "role": msg.role,          # 'user' ou 'assistant'
            "contenu": msg.contenu,    # Le texte (avec les formules KaTeX)
            "date_creation": msg.date_creation  # CORRECTION : Utilisation du bon attribut de modèle
        })
        
    return {"status": "success", "count": len(retour), "results": retour}