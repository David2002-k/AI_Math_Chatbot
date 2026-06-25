"""
backend/routes/admin.py
─────────────────────────────────────────────
Points d'accès sécurisés pour l'administration.

Toutes les routes (sauf indication contraire) exigent un profil
administrateur, vérifié par la dépendance obtenir_admin_courant.
Couvre les cas d'utilisation prévus au cahier des charges :
« Gérer les utilisateurs » et « Gérer les modèles IA ».
─────────────────────────────────────────────
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies import obtenir_admin_courant, obtenir_utilisateur_courant
from schemas import (
    UtilisateurAdminReponse,
    UtilisateurStatutModification,
    ModeleIACreation,
    ModeleIAModification,
    ModeleIAAdminReponse,
)
import models

router = APIRouter(prefix="/admin", tags=["Administration"])


# ══════════════════════════════════════════════
# VÉRIFICATION DU RÔLE (utilisée par le frontend)
# ══════════════════════════════════════════════
@router.get("/verifier")
def verifier_acces_admin(
    utilisateur: models.Utilisateur = Depends(obtenir_utilisateur_courant),
    db: Session = Depends(get_db),
):
    """
    Indique si l'utilisateur connecté est administrateur.
    Accessible à tout utilisateur authentifié : sert au frontend à décider
    s'il affiche ou non le lien vers le tableau de bord.
    """
    profil = db.query(models.Admin).filter(
        models.Admin.utilisateur_id == utilisateur.id
    ).first()
    return {"est_admin": bool(profil), "role": profil.role if profil else None}


# ══════════════════════════════════════════════
# STATISTIQUES GLOBALES
# ══════════════════════════════════════════════
@router.get("/stats")
def obtenir_statistiques_globales(
    admin: models.Admin = Depends(obtenir_admin_courant),
    db: Session = Depends(get_db),
):
    """Statistiques d'utilisation pour le tableau de bord. GET /api/admin/stats"""
    return {
        "status": "success",
        "stats": {
            "total_utilisateurs": db.query(models.Utilisateur).count(),
            "total_utilisateurs_actifs": db.query(models.Utilisateur).filter(
                models.Utilisateur.est_actif == True
            ).count(),
            "total_conversations": db.query(models.Chat).count(),
            "total_messages": db.query(models.Message).count(),
            "total_fichiers": db.query(models.Fichier).count(),
        },
    }


# ══════════════════════════════════════════════
# GESTION DES UTILISATEURS
# ══════════════════════════════════════════════
def _vers_reponse_utilisateur(u: models.Utilisateur, db: Session) -> UtilisateurAdminReponse:
    profil = db.query(models.Admin).filter(
        models.Admin.utilisateur_id == u.id
    ).first()
    return UtilisateurAdminReponse(
        id=u.id, nom=u.nom, email=u.email, type=u.type,
        est_actif=u.est_actif, est_admin=profil is not None,
        role=profil.role if profil else None,
        date_inscription=u.date_inscription,
    )


def _verifier_droits_sur_cible(admin: models.Admin, cible: models.Utilisateur, db: Session, action: str):
    """Règles de protection partagées par la suppression et la désactivation :
    - on ne peut pas agir sur son propre compte ;
    - le superadmin ne peut être ni supprimé ni désactivé ;
    - un modérateur ne peut pas agir sur un autre administrateur
      (seul le superadmin le peut)."""
    if cible.id == admin.utilisateur_id:
        raise HTTPException(status_code=400, detail=f"Vous ne pouvez pas {action} votre propre compte.")

    profil_cible = db.query(models.Admin).filter(
        models.Admin.utilisateur_id == cible.id
    ).first()
    if profil_cible:
        if profil_cible.role == "superadmin":
            raise HTTPException(status_code=403, detail=f"Le superadmin ne peut pas être {action.replace('er', 'é') if action.endswith('er') else action}.")
        if admin.role != "superadmin":
            raise HTTPException(status_code=403, detail=f"Un modérateur ne peut pas {action} un administrateur.")


@router.get("/utilisateurs", response_model=list[UtilisateurAdminReponse])
def lister_utilisateurs(
    admin: models.Admin = Depends(obtenir_admin_courant),
    db: Session = Depends(get_db),
):
    """Liste tous les comptes. GET /api/admin/utilisateurs"""
    utilisateurs = db.query(models.Utilisateur).order_by(
        models.Utilisateur.date_inscription.desc()
    ).all()
    return [_vers_reponse_utilisateur(u, db) for u in utilisateurs]


@router.patch("/utilisateurs/{utilisateur_id}/statut", response_model=UtilisateurAdminReponse)
def changer_statut_utilisateur(
    utilisateur_id: int,
    donnees: UtilisateurStatutModification,
    admin: models.Admin = Depends(obtenir_admin_courant),
    db: Session = Depends(get_db),
):
    """Active ou désactive un compte. PATCH /api/admin/utilisateurs/{id}/statut"""
    u = db.query(models.Utilisateur).filter(models.Utilisateur.id == utilisateur_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    _verifier_droits_sur_cible(admin, u, db, "désactiver")
    u.est_actif = donnees.est_actif
    db.commit()
    db.refresh(u)
    return _vers_reponse_utilisateur(u, db)


@router.patch("/utilisateurs/{utilisateur_id}/role", response_model=UtilisateurAdminReponse)
def changer_role_admin(
    utilisateur_id: int,
    donnees: UtilisateurStatutModification,  # réutilise est_actif comme "est_admin"
    admin: models.Admin = Depends(obtenir_admin_courant),
    db: Session = Depends(get_db),
):
    """Promeut ou rétrograde un utilisateur au rang d'administrateur.
    Réservé au superadmin. PATCH /api/admin/utilisateurs/{id}/role
    Le corps {est_actif:true} promeut, {est_actif:false} rétrograde."""
    if admin.role != "superadmin":
        raise HTTPException(status_code=403, detail="Seul un superadmin peut modifier les rôles.")

    u = db.query(models.Utilisateur).filter(models.Utilisateur.id == utilisateur_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    if u.id == admin.utilisateur_id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas modifier votre propre rôle.")

    profil = db.query(models.Admin).filter(models.Admin.utilisateur_id == u.id).first()
    promouvoir = donnees.est_actif
    if promouvoir and not profil:
        db.add(models.Admin(utilisateur_id=u.id, role="moderateur"))
    elif not promouvoir and profil:
        db.delete(profil)
    db.commit()
    return _vers_reponse_utilisateur(u, db)


@router.delete("/utilisateurs/{utilisateur_id}")
def supprimer_utilisateur(
    utilisateur_id: int,
    admin: models.Admin = Depends(obtenir_admin_courant),
    db: Session = Depends(get_db),
):
    """Supprime un compte et tout ce qui s'y rattache. DELETE /api/admin/utilisateurs/{id}"""
    u = db.query(models.Utilisateur).filter(models.Utilisateur.id == utilisateur_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    _verifier_droits_sur_cible(admin, u, db, "supprimer")
    db.delete(u)
    db.commit()
    return {"detail": "Utilisateur supprimé."}


# ══════════════════════════════════════════════
# GESTION DES MODÈLES IA
# ══════════════════════════════════════════════
@router.get("/modeles", response_model=list[ModeleIAAdminReponse])
def lister_modeles(
    admin: models.Admin = Depends(obtenir_admin_courant),
    db: Session = Depends(get_db),
):
    """Liste tous les modèles (actifs et inactifs). GET /api/admin/modeles"""
    return db.query(models.ModeleIA).order_by(models.ModeleIA.id.asc()).all()


@router.post("/modeles", response_model=ModeleIAAdminReponse, status_code=status.HTTP_201_CREATED)
def creer_modele(
    donnees: ModeleIACreation,
    admin: models.Admin = Depends(obtenir_admin_courant),
    db: Session = Depends(get_db),
):
    """Ajoute un modèle IA. POST /api/admin/modeles"""
    modele = models.ModeleIA(
        nom=donnees.nom,
        description=donnees.description,
        modele_gemini=donnees.modele_gemini,
        est_actif=donnees.est_actif,
    )
    db.add(modele)
    db.commit()
    db.refresh(modele)
    return modele


@router.patch("/modeles/{modele_id}", response_model=ModeleIAAdminReponse)
def modifier_modele(
    modele_id: int,
    donnees: ModeleIAModification,
    admin: models.Admin = Depends(obtenir_admin_courant),
    db: Session = Depends(get_db),
):
    """Modifie un modèle (nom, description, modèle Gemini, activation). PATCH /api/admin/modeles/{id}"""
    modele = db.query(models.ModeleIA).filter(models.ModeleIA.id == modele_id).first()
    if not modele:
        raise HTTPException(status_code=404, detail="Modèle introuvable.")
    for champ, valeur in donnees.model_dump(exclude_unset=True).items():
        setattr(modele, champ, valeur)
    db.commit()
    db.refresh(modele)
    return modele


@router.delete("/modeles/{modele_id}")
def supprimer_modele(
    modele_id: int,
    admin: models.Admin = Depends(obtenir_admin_courant),
    db: Session = Depends(get_db),
):
    """Supprime un modèle IA. DELETE /api/admin/modeles/{id}"""
    modele = db.query(models.ModeleIA).filter(models.ModeleIA.id == modele_id).first()
    if not modele:
        raise HTTPException(status_code=404, detail="Modèle introuvable.")
    db.delete(modele)
    db.commit()
    return {"detail": "Modèle supprimé."}
