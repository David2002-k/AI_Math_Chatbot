"""
models.py
─────────────────────────────────────────────
Définition des 9 tables de la base de données
avec SQLAlchemy (ORM Python).

Tables :
  1. ModeleIA       → niveaux IA (Basique / Pro / Max)
  2. Utilisateur    → comptes utilisateurs
  3. Session        → connexions JWT
  4. Parametre      → préférences utilisateur (1→1)
  5. Chat           → conversations (historique)
  6. Message        → messages dans chaque chat
  7. Fichier        → fichiers uploadés
  8. Recherche      → historique des recherches
  9. Admin          → profils administrateurs (1→1 avec Utilisateur)
─────────────────────────────────────────────
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    DateTime, ForeignKey, BigInteger
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


# ──────────────────────────────────────────────
# 1. MODELES_IA — Les niveaux IA disponibles
# ──────────────────────────────────────────────
class ModeleIA(Base):
    """
    Table de référence : Basique / Pro / Max.
    Le champ 'modele_gemini' contient le vrai nom technique
    envoyé à l'API Google (caché à l'utilisateur).
    """
    __tablename__ = "modeles_ia"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)              # "Basique", "Pro", "Max"
    description = Column(Text)                        # explication affichée à l'utilisateur
    modele_gemini = Column(String, nullable=False)    # ex: "gemini-2.5-flash"
    est_actif = Column(Boolean, default=True)
    date_ajout = Column(DateTime, default=datetime.now)

    # Relations inverses
    parametres = relationship("Parametre", back_populates="modele")
    chats = relationship("Chat", back_populates="modele")
    messages = relationship("Message", back_populates="modele")


# ──────────────────────────────────────────────
# 2. UTILISATEURS — Les comptes
# ──────────────────────────────────────────────
class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    mot_de_passe = Column(String, nullable=False)     # hashé bcrypt
    photo_profil = Column(String, nullable=True)
    type = Column(String, default="anonyme")          # "authentifie" | "anonyme"
    est_actif = Column(Boolean, default=True)
    derniere_connexion = Column(DateTime, nullable=True)
    date_inscription = Column(DateTime, default=datetime.now)

    # Relations — un utilisateur a plusieurs...
    sessions = relationship("Session", back_populates="utilisateur", cascade="all, delete")
    chats = relationship("Chat", back_populates="utilisateur", cascade="all, delete")
    recherches = relationship("Recherche", back_populates="utilisateur", cascade="all, delete")

    # Relations 1→1 (Un utilisateur a un seul profil paramètre et un seul profil admin s'il l'est)
    parametre = relationship("Parametre", back_populates="utilisateur", uselist=False, cascade="all, delete")
    admin_profile = relationship("Admin", back_populates="utilisateur", uselist=False, cascade="all, delete")


# ──────────────────────────────────────────────
# 3. SESSIONS — Connexions sécurisées (JWT)
# ──────────────────────────────────────────────
class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    token = Column(String, unique=True, nullable=False)
    est_actif = Column(Boolean, default=True)
    date_expiration = Column(DateTime, nullable=False)
    date_creation = Column(DateTime, default=datetime.now)

    utilisateur = relationship("Utilisateur", back_populates="sessions")


# ──────────────────────────────────────────────
# 4. PARAMETRES — Préférences (1 par utilisateur)
# ──────────────────────────────────────────────
class Parametre(Base):
    __tablename__ = "parametres"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), unique=True, nullable=False)
    modele_id = Column(Integer, ForeignKey("modeles_ia.id"), nullable=True)
    theme = Column(String, default="clair")           # "clair" | "sombre"
    langue = Column(String, default="fr")             # "fr" | "en"
    date_modification = Column(DateTime, default=datetime.now)

    utilisateur = relationship("Utilisateur", back_populates="parametre")
    modele = relationship("ModeleIA", back_populates="parametres")


# ──────────────────────────────────────────────
# 5. CHATS — Les conversations (historique)
# ──────────────────────────────────────────────
class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    modele_id = Column(Integer, ForeignKey("modeles_ia.id"), nullable=True)
    titre = Column(String, default="Nouvelle conversation")
    titre_modifie = Column(Boolean, default=False)
    est_epingle = Column(Boolean, default=False)
    est_archive = Column(Boolean, default=False)
    date_creation = Column(DateTime, default=datetime.now)
    date_modification = Column(DateTime, default=datetime.now)

    utilisateur = relationship("Utilisateur", back_populates="chats")
    modele = relationship("ModeleIA", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete")


# ──────────────────────────────────────────────
# 6. MESSAGES — Contenu des conversations
# ──────────────────────────────────────────────
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    modele_id = Column(Integer, ForeignKey("modeles_ia.id"), nullable=True)
    role = Column(String, nullable=False)             # "user" | "assistant"
    contenu = Column(Text, nullable=False)
    reaction = Column(String, nullable=True)          # "like" | "dislike" | None
    tokens_utilises = Column(Integer, default=0)
    date_creation = Column(DateTime, default=datetime.now)

    chat = relationship("Chat", back_populates="messages")
    modele = relationship("ModeleIA", back_populates="messages")
    fichiers = relationship("Fichier", back_populates="message", cascade="all, delete")


# ──────────────────────────────────────────────
# 7. FICHIERS — Documents uploadés
# ──────────────────────────────────────────────
class Fichier(Base):
    __tablename__ = "fichiers"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=True)  # lien temporaire avant la création du message
    nom_original = Column(String, nullable=False)     # ex: "exercice.pdf"
    nom_fichier = Column(String, nullable=False)      # nom unique sur le serveur
    type_fichier = Column(String, nullable=False)     # "pdf" | "image" | "docx"
    taille = Column(BigInteger, default=0)            # en octets
    chemin = Column(String, nullable=False)           # backend/uploads/...
    contenu_extrait = Column(Text, nullable=True)     # texte envoyé à Gemini
    date_upload = Column(DateTime, default=datetime.now)

    message = relationship("Message", back_populates="fichiers")


# ──────────────────────────────────────────────
# 8. RECHERCHES — Historique de recherche
# ──────────────────────────────────────────────
class Recherche(Base):
    __tablename__ = "recherches"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False)
    mot_cle = Column(String, nullable=False)
    date_recherche = Column(DateTime, default=datetime.now)

    utilisateur = relationship("Utilisateur", back_populates="recherches")


# ──────────────────────────────────────────────
# 9. ADMINS — Les rôles d'administration (Nouvelle Table)
# ──────────────────────────────────────────────
class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id", ondelete="CASCADE"), unique=True, nullable=False)
    role = Column(String, default="moderateur", nullable=False)  # "superadmin" | "moderateur"
    date_nomination = Column(DateTime, default=datetime.now)

    utilisateur = relationship("Utilisateur", back_populates="admin_profile")