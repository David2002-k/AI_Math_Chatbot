"""
whisper_service.py
─────────────────────────────────────────────
Intégration avec OpenAI Whisper via l'API Hugging Face.

Fonctions :
- transcrire_audio_en_texte() → convertit un fichier audio (.wav, .mp3, etc.)
                                en texte brut grâce à l'API Hugging Face.
─────────────────────────────────────────────
"""

import os
import requests
from dotenv import load_dotenv

# Chargement des variables d'environnement (.env)
load_dotenv()

# Récupération du token Hugging Face
HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

# URL de l'API pour le modèle Whisper de OpenAI hébergé sur Hugging Face
API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}


def transcrire_audio_en_texte(chemin_fichier_audio: str) -> str:
    """
    Envoie le fichier audio à l'API d'inférence de Hugging Face 
    pour transcrire le son en texte avec Whisper.
    """
    # 1. Sécurité : Vérifier si le fichier audio existe bien sur le serveur
    if not os.path.exists(chemin_fichier_audio):
        print(f"❌ Erreur : Le fichier {chemin_fichier_audio} est introuvable.")
        return "Erreur : Fichier audio introuvable."

    try:
        # 2. Lecture du fichier audio en mode binaire
        with open(chemin_fichier_audio, "rb") as f:
            data = f.read()
            
        # 3. Appel à l'API d'inférence Hugging Face
        reponse = requests.post(API_URL, headers=headers, data=data)
        
        # 4. Vérification et retour du résultat
        if reponse.status_code == 200:
            resultat = reponse.json()
            # Hugging Face renvoie un dictionnaire contenant la clé 'text'
            return resultat.get("text", "").strip()
        else:
            print(f"❌ Erreur Hugging Face ({reponse.status_code}) : {reponse.text}")
            return "Désolé, l'analyse vocale a échoué."

    except Exception as e:
        print(f"❌ Erreur lors de la transcription : {str(e)}")
        return "Désolé, impossible de transcrire le message vocal."