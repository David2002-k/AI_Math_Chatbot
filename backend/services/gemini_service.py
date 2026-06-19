"""
gemini_service.py
─────────────────────────────────────────────
Intégration avec Google Gemini (google-generativeai).

Fonctions :
- generer_reponse()       → envoie une question à Gemini, retourne la réponse
- generer_titre_chat()     → génère un titre court à partir du 1er message
                              (table chats.titre, généré automatiquement par l'IA)
─────────────────────────────────────────────
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Correspondance entre nos niveaux (table modeles_ia) et les modèles Gemini réels
MODELES_GEMINI = {
    "Basique": "gemini-2.5-flash",
    "Pro": "gemini-2.5-pro",
    "Max": "gemini-2.5-pro",
}

INSTRUCTION_SYSTEME = """
Tu es un assistant mathématique pédagogique pour des étudiants en Licence MI.
Décompose toujours tes solutions en étapes numérotées et claires.
Utilise la syntaxe LaTeX pour toutes les formules :
- $...$ pour les formules en ligne
- $$...$$ pour les formules isolées
Sois rigoureux mais accessible.
"""


def generer_reponse(question: str, nom_modele: str = "Basique", contexte_fichiers: str = "") -> dict:
    """
    Envoie la question (+ contenu de fichiers éventuels) à Gemini.
    Retourne {"texte": ..., "tokens": ...}
    """
    modele_technique = MODELES_GEMINI.get(nom_modele, "gemini-2.5-flash")
    modele = genai.GenerativeModel(
        model_name=modele_technique,
        system_instruction=INSTRUCTION_SYSTEME
    )

    prompt = question
    if contexte_fichiers:
        prompt = f"{question}\n\n--- Contenu des fichiers joints ---\n{contexte_fichiers}"

    reponse = modele.generate_content(prompt)

    tokens = 0
    if hasattr(reponse, "usage_metadata") and reponse.usage_metadata:
        tokens = reponse.usage_metadata.total_token_count

    return {
        "texte": reponse.text,
        "tokens": tokens
    }


def generer_titre_chat(premier_message: str) -> str:
    """
    Génère un titre court (5 mots max) à partir du premier message
    de l'utilisateur — rempli automatiquement dans chats.titre.
    """
    modele = genai.GenerativeModel("gemini-2.5-flash")

    prompt = (
        f"Donne un titre très court (5 mots maximum, sans guillemets, sans ponctuation finale) "
        f"qui résume cette question mathématique :\n\n{premier_message}"
    )

    try:
        reponse = modele.generate_content(prompt)
        titre = reponse.text.strip().strip('"').strip("'")
        return titre[:60]  # sécurité longueur
    except Exception:
        return "Nouvelle conversation"
