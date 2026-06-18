"""
security.py
─────────────────────────────────────────────
Fonctions de sécurité utilisées par routes/auth.py :

- bcrypt   → hash et vérifie les mots de passe
- pyjwt    → génère et vérifie les tokens de connexion

Personne d'autre que ce fichier ne devrait manipuler
des mots de passe en clair ou des tokens directement.
─────────────────────────────────────────────
"""

import bcrypt
import jwt
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "cle_par_defaut_a_changer")
JWT_ALGORITHM = "HS256"
DUREE_TOKEN_JOURS = 7


# ══════════════════════════════════════════════
# MOTS DE PASSE — bcrypt
# ══════════════════════════════════════════════
def hasher_mot_de_passe(mot_de_passe: str) -> str:
    """Transforme un mot de passe en clair en hash sécurisé bcrypt."""
    sel = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(mot_de_passe.encode("utf-8"), sel)
    return hash_bytes.decode("utf-8")


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
    """Compare un mot de passe en clair avec le hash stocké en base."""
    return bcrypt.checkpw(mot_de_passe.encode("utf-8"), hash_stocke.encode("utf-8"))


# ══════════════════════════════════════════════
# TOKENS JWT — pyjwt
# ══════════════════════════════════════════════
def generer_token(utilisateur_id: int) -> tuple[str, datetime]:
    """
    Crée un token JWT contenant l'id de l'utilisateur.
    Retourne (token, date_expiration) pour les sauvegarder
    dans la table 'sessions'.
    """
    date_expiration = datetime.utcnow() + timedelta(days=DUREE_TOKEN_JOURS)

    payload = {
        "utilisateur_id": utilisateur_id,
        "exp": date_expiration
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, date_expiration


def decoder_token(token: str) -> dict | None:
    """
    Vérifie et décode un token JWT.
    Retourne le contenu (payload) si valide, None si invalide/expiré.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
