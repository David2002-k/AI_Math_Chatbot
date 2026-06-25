from sqlalchemy import inspect
from database import SessionLocal, engine, Base
import models  # Charge l'intégralité du fichier models.py d'un coup

print("🔄 1. Connexion à PostgreSQL...")
Base.metadata.create_all(bind=engine)

inspecteur = inspect(engine)
tables_creees = inspecteur.get_table_names()

print("\n📊 2. Liste des tables installées :")
for i, table in enumerate(tables_creees, 1):
    print(f"   [{i}] Table détectée : '{table}'")

print(f"\n✨ Total : {len(tables_creees)}/9 tables prêtes.")

db = SessionLocal()
try:
    if db.query(models.ModeleIA).count() == 0:
        modeles = [
            models.ModeleIA(nom="Basique", description="Rapide et efficace.", modele_gemini="gemini-2.5-flash"),
            models.ModeleIA(nom="Pro", description="Plus puissant.", modele_gemini="gemini-2.5-pro"),
            models.ModeleIA(nom="Max", description="Le plus performant.", modele_gemini="gemini-2.5-pro"),
        ]
        db.add_all(modeles)
        db.commit()
        print("🌱 Modèles initialisés !")
    else:
        print("ℹ️ Les modèles existent déjà, rien à faire.")

    # ── Compte administrateur par défaut ──
    from security import hasher_mot_de_passe

    ADMIN_EMAIL = "admin@mathchatbot.com"
    ADMIN_MDP = "admin123"

    admin_user = db.query(models.Utilisateur).filter(
        models.Utilisateur.email == ADMIN_EMAIL
    ).first()

    if not admin_user:
        admin_user = models.Utilisateur(
            nom="Administrateur",
            email=ADMIN_EMAIL,
            mot_de_passe=hasher_mot_de_passe(ADMIN_MDP),
            type="authentifie",
            est_actif=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        db.add(models.Parametre(utilisateur_id=admin_user.id))
        db.commit()

    # Garantit le profil admin (rôle superadmin)
    if not db.query(models.Admin).filter(models.Admin.utilisateur_id == admin_user.id).first():
        db.add(models.Admin(utilisateur_id=admin_user.id, role="superadmin"))
        db.commit()
        print(f"👑 Administrateur prêt → {ADMIN_EMAIL} / {ADMIN_MDP}")
    else:
        print("ℹ️ Administrateur déjà présent.")
finally:
    db.close()