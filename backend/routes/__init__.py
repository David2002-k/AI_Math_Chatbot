"""
routes/__init__.py
─────────────────────────────────────────────
Initialisation du package des routes et export des routeurs.
─────────────────────────────────────────────
"""

from .auth import router as auth
from .chats import router as chats
from .messages import router as messages
from .fichiers import router as fichiers
from .parametres import router as parametres
from .recherche import router as recherche
from .admin import router as admin