# 🧮 AI Math Chatbot

Agent conversationnel mathématique intelligent — Projet Tutoré, Licence Mathématiques-Informatique 2025/2026.

> Université Virtuelle du Burkina Faso —   

---

## 📦 Stack technique

| Composant | Technologie |
|---|---|
| Backend | FastAPI (Python 3.9+) |
| Base de données | PostgreSQL + SQLAlchemy (repli automatique sur SQLite si PostgreSQL est indisponible) |
| Authentification | bcrypt (mots de passe) + PyJWT (sessions) |
| IA conversationnelle | Google Gemini 2.5 Flash/Pro (SDK Google Gen AI), réponses en streaming (Server-Sent Events) |
| Reconnaissance vocale | Web Speech API (navigateur, par défaut) + repli Whisper via Hugging Face Inference API |
| Extraction fichiers | pypdf (PDF), python-docx (DOCX), OCR multimodal Gemini Vision (images) |
| Rendu mathématique | KaTeX (LaTeX → formules, côté navigateur) |
| Frontend | HTML/CSS/JS vanilla + Bootstrap 5 (vendorisé localement, pas de CDN) |

---

## 🚀 Démarrage

### 1. Base de données

PostgreSQL est utilisé par défaut. Si aucune instance n'est joignable, `backend/database.py`
bascule automatiquement sur une base SQLite locale (`mathchatbot.db`) — aucune action requise
pour un démarrage rapide en local.

Pour utiliser PostgreSQL :
```bash
psql -U postgres
```
```sql
CREATE USER mathuser WITH PASSWORD 'mathpassword';
CREATE DATABASE mathchatbot OWNER mathuser;
\q
```

### 2. Configurer les clés API

```bash
cd backend
cp .env.example .env
```

Éditer `backend/.env` et renseigner `GEMINI_API_KEY` (https://aistudio.google.com),
`JWT_SECRET` (chaîne aléatoire longue) et, si besoin, `HF_API_TOKEN` (transcription Whisper de secours).

### 3. Créer l'environnement Python

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
```

### 4. Lancer le backend

```bash
uvicorn main:app --reload --port 8000
```
→ documentation interactive : http://localhost:8000/docs

Au premier démarrage, `main.py` initialise automatiquement les tables, les modèles IA par
défaut (Basique / Pro / Max) ainsi qu'un compte administrateur (`admin@mathchatbot.com` /
`admin123`, à changer dès la première connexion).

### 5. Lancer le frontend (nouveau terminal)

```bash
cd frontend
python -m http.server 3000
```
→ interface : http://localhost:3000

---

## 🗄️ Base de données

```
modeles_ia    → modèles IA disponibles (Basique / Pro / Max), activables par l'admin
utilisateurs  → comptes (anonyme ou authentifié)
admins        → profils administrateur (rôle : moderateur / superadmin)
sessions      → tokens JWT de connexion
parametres    → thème, langue, modèle par défaut (1↔1 avec utilisateurs)
chats         → conversations (titre auto-généré par l'IA)
messages      → questions / réponses + réactions like/dislike
fichiers      → PDF/image/DOCX uploadés, contenu extrait pour Gemini
recherches    → historique des mots-clés recherchés par utilisateur
```

---

## 🛣️ Routes API principales

```
POST   /api/auth/anonyme                    → crée un utilisateur anonyme + token
POST   /api/auth/inscription                 → crée un compte (conserve l'historique anonyme)
POST   /api/auth/connexion                    → connexion par email/mot de passe
POST   /api/auth/deconnexion                   → révoque la session
PATCH  /api/auth/mot-de-passe                   → changer son mot de passe

POST   /api/chats                                → nouvelle conversation
GET    /api/chats                                 → historique
GET    /api/chats/recherche?q=...                  → recherche (titre + contenu des messages)
GET    /api/chats/{id}                              → messages d'une conversation
PATCH  /api/chats/{id}                               → renommer
DELETE /api/chats/{id}                                → supprimer (et ses fichiers associés)

POST   /api/messages                                    → envoyer un message → réponse Gemini
POST   /api/messages/stream                              → envoi en streaming (effet de frappe)
PATCH  /api/messages/{id}/reaction                        → like/dislike

POST   /api/fichiers/upload                                → upload PDF/image/DOCX (max 5, 10 Mo chacun)
DELETE /api/fichiers/{id}                                    → supprimer un fichier

GET    /api/parametres / PATCH /api/parametres                → préférences utilisateur
GET    /api/modeles                                             → modèles IA actifs

GET    /api/admin/verifier                                       → l'utilisateur courant est-il admin ?
GET    /api/admin/stats                                           → statistiques globales
GET    /api/admin/utilisateurs                                     → liste des comptes
PATCH  /api/admin/utilisateurs/{id}/statut                           → activer/désactiver un compte
PATCH  /api/admin/utilisateurs/{id}/role                              → promouvoir/rétrograder (superadmin)
DELETE /api/admin/utilisateurs/{id}                                     → supprimer un compte
GET/POST/PATCH/DELETE /api/admin/modeles                                 → gestion des modèles IA
```

---

## 📁 Structure du projet

```
AI_Math_Chatbot/
├── backend/
│   ├── main.py                 → serveur FastAPI, init des données par défaut
│   ├── models.py                → tables SQLAlchemy
│   ├── database.py               → connexion PostgreSQL + repli SQLite
│   ├── schemas.py                  → validation Pydantic
│   ├── security.py                  → bcrypt + JWT
│   ├── dependencies.py               → utilisateur courant / admin courant
│   ├── services/
│   │   ├── gemini_service.py           → appels à l'API Gemini (streaming inclus)
│   │   └── whisper_service.py            → transcription vocale de secours
│   ├── routes/
│   │   ├── auth.py, chats.py, messages.py, fichiers.py, parametres.py, recherche.py, admin.py
│   ├── uploads/                          → fichiers uploadés par les utilisateurs
│   └── requirements.txt
└── frontend/
    ├── index.html                  → interface de chat
    ├── css/style.css                 → thèmes clair/sombre
    ├── js/
    │   ├── chat.js                     → envoi de messages, upload, streaming
    │   ├── audio.js                      → reconnaissance vocale (micro)
    │   ├── auth.js, theme.js, api.js, admin.js
    ├── pages/
    │   ├── connexion.html, inscription.html, parametres.html, admin.html
    └── vendor/                            → Bootstrap, Bootstrap Icons, KaTeX (locaux, sans CDN)
```

---

## 👤 Rôles & permissions

- **Utilisateur** : chat, upload de fichiers, historique, reconnaissance vocale, gestion de son propre compte.
- **Modérateur** (`admin.role = moderateur`) : tableau de bord, gestion des utilisateurs standards, gestion des modèles IA — ne peut pas agir sur un autre administrateur ni sur lui-même.
- **Superadmin** : en plus des droits du modérateur, peut promouvoir/rétrograder des modérateurs. Ne peut être ni désactivé ni supprimé.

---

## 🛣️ Prochaines étapes

- [ ] Export PDF de l'historique d'une conversation
- [ ] Cache des réponses fréquentes pour réduire la consommation de quota Gemini
- [ ] Notifications en temps réel (WebSocket) pour les actions d'administration
