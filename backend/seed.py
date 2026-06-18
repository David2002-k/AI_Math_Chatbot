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
        print("ℹ️ Les données existent déjà, rien à faire.")
finally:
    db.close()