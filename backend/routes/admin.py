"""
backend/routes/admin.py
─────────────────────────────────────────────
Points d'accès (Endpoints) sécurisés pour l'administration.
─────────────────────────────────────────────
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models

router = APIRouter(
    prefix="/admin",
    tags=["Administration"]
)

@router.get("/stats")
def obtenir_statistiques_globales(db: Session = Depends(get_db)):
    """
    Récupère les statistiques d'utilisation du Chatbot pour le tableau de bord Admin.
    URL : GET /api/admin/stats
    """
    try:
        # CORRECTION : Utilisation des bons noms de classes définis dans models.py
        total_utilisateurs = db.query(models.Utilisateur).count()
        total_messages = db.query(models.Message).count()
        total_conversations = db.query(models.Chat).count()
         
        return {
            "status": "success",
            "stats": {
                "total_etudiants_inscrits": total_utilisateurs,
                "total_conversations_creees": total_conversations,
                "total_messages_echanges": total_messages
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Impossible de récupérer les statistiques : {str(e)}"
        )