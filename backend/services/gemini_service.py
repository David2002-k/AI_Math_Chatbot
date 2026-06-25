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
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def _verifier_cle_api():
    """
    Vérifie que la clé API Gemini est bien configurée et lève une erreur
    explicite (et lisible par l'utilisateur) si ce n'est pas le cas.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "Clé API Gemini manquante. Ajoutez GEMINI_API_KEY dans le fichier "
            "backend/.env (voir backend/.env.example) puis redémarrez le serveur."
        )

# Correspondance entre nos niveaux (table modeles_ia) et les modèles Gemini réels
MODELES_GEMINI = {
    "Basique": "gemini-2.5-flash",
    "Pro": "gemini-2.5-pro",
    "Max": "gemini-2.5-pro",
}

# --- INSTRUCTION SYSTÈME OPTIMISÉE POUR LE RENDU KATEX ---
INSTRUCTION_SYSTEME = r"""
Tu es un assistant mathématique pédagogique et rigoureux pour des étudiants en Licence MI.
Décompose toujours tes solutions en étapes numérotées et claires.

CONSIGNE STRICTE DE FORMATAGE MATHÉMATIQUE (LaTeX) :
N'utilise JAMAIS les symboles '$' ou '$$' pour encadrer tes formules mathématiques.
Utilise un SEUL antislash (pas de double antislash) pour les délimiteurs :
- Pour les formules intégrées dans le texte (en ligne), utilise exclusivement les délimiteurs \( et \). Exemple : \( \det(A) = ad - bc \).
- Pour les formules isolées, centrées ou les matrices complexes, utilise exclusivement les délimiteurs \[ et \] placés sur des lignes dédiées. Exemple :
\[
A = \begin{pmatrix} a & b \\ c & d \end{pmatrix}
\]
"""


def _construire_parts(question: str, contexte_fichiers: str, chemins_images: list[str] | None):
    """
    Construit la liste de "parts" envoyée à Gemini : le texte (question + contenu
    extrait des PDF/DOCX), suivi des images ouvertes via Pillow (vision), afin que
    l'IA "voie" réellement les photos d'exercices et pas seulement leur nom.
    """
    prompt = question
    if contexte_fichiers:
        prompt = f"{question}\n\n--- Contenu des fichiers joints ---\n{contexte_fichiers}"

    parts = [prompt]
    for chemin in (chemins_images or []):
        try:
            parts.append(Image.open(chemin))
        except Exception as e:
            print(f"Erreur d'ouverture de l'image {chemin}: {str(e)}")
    return parts


def generer_reponse(question: str, nom_modele: str = "Basique", contexte_fichiers: str = "", historique: list[dict] | None = None, chemins_images: list[str] | None = None) -> dict:
    """
    Envoie la question (+ contenu de fichiers éventuels) à Gemini, en tenant compte
    de l'historique des messages précédents du même chat (mémoire de conversation).
    `historique` est une liste de dicts {"role": "user"|"assistant", "contenu": str},
    triée du plus ancien au plus récent, EXCLUANT le message courant.
    Retourne {"texte": ..., "tokens": ...}
    """
    _verifier_cle_api()
    modele_technique = MODELES_GEMINI.get(nom_modele, "gemini-2.5-flash")
    modele = genai.GenerativeModel(
        model_name=modele_technique,
        system_instruction=INSTRUCTION_SYSTEME
    )

    contenu_historique = []
    for msg in (historique or []):
        role_gemini = "model" if msg["role"] == "assistant" else "user"
        contenu_historique.append({"role": role_gemini, "parts": [msg["contenu"]]})

    chat_session = modele.start_chat(history=contenu_historique)

    parts = _construire_parts(question, contexte_fichiers, chemins_images)
    reponse = chat_session.send_message(parts)

    tokens = 0
    if hasattr(reponse, "usage_metadata") and reponse.usage_metadata:
        tokens = reponse.usage_metadata.total_token_count

    return {
        "texte": reponse.text,
        "tokens": tokens
    }


def generer_reponse_stream(question: str, nom_modele: str = "Basique", contexte_fichiers: str = "", historique: list[dict] | None = None, chemins_images: list[str] | None = None):
    """
    Variante en streaming de generer_reponse() : envoie la question à Gemini et
    yield chaque fragment de texte au fur et à mesure qu'il arrive (effet de frappe).
    Le dernier élément yield est un tuple ("__usage__", tokens) pour signaler la fin.
    """
    _verifier_cle_api()
    modele_technique = MODELES_GEMINI.get(nom_modele, "gemini-2.5-flash")
    modele = genai.GenerativeModel(
        model_name=modele_technique,
        system_instruction=INSTRUCTION_SYSTEME
    )

    contenu_historique = []
    for msg in (historique or []):
        role_gemini = "model" if msg["role"] == "assistant" else "user"
        contenu_historique.append({"role": role_gemini, "parts": [msg["contenu"]]})

    chat_session = modele.start_chat(history=contenu_historique)

    parts = _construire_parts(question, contexte_fichiers, chemins_images)
    flux = chat_session.send_message(parts, stream=True)

    tokens = 0
    for fragment in flux:
        if fragment.text:
            yield fragment.text
        if hasattr(fragment, "usage_metadata") and fragment.usage_metadata:
            tokens = fragment.usage_metadata.total_token_count

    yield ("__usage__", tokens)


def generer_titre_chat(premier_message: str) -> str:
    """
    Génère un titre court (5 mots max) à partir du premier message
    de l'utilisateur — rempli automatiquement dans chats.titre.
    """
    _verifier_cle_api()
    modele = genai.GenerativeModel("gemini-2.5-flash")

    prompt = (
        f"Donne un titre très court (5 mots maximum, sans guillemets, sans ponctuation finale) "
        f"qui résume cette question mathématique :\n\n{premier_message}"
    )

    try:
        reponse = modele.generate_content(prompt)
        titre = reponse.text.strip().strip('"').strip("'")
        return titre[:60]
    except Exception:
        return "Nouvelle conversation"