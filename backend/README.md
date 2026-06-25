# 🧮 AI Math Chatbot

Agent conversationnel mathématique intelligent — Projet Tutoré, Licence MI 2025/2026.

---

## 📦 Stack technique

| Composant | Technologie |
|---|---|
| Backend | FastAPI (Python) |
| Base de données | PostgreSQL + SQLAlchemy |
| Authentification | bcrypt (mots de passe) + PyJWT (sessions) |
| IA | Google Gemini 2.5 (Flash / Pro) |
| Extraction fichiers | pypdf (PDF) + python-docx (DOCX) |
| Frontend | Bootstrap 5 + KaTeX (HTML/CSS/JS) |

---

## 🚀 Démarrage (sans Docker)

### 1. Créer la base PostgreSQL

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

Éditer `backend/.env` et renseigner `GEMINI_API_KEY` (https://aistudio.google.com)
et `JWT_SECRET` (une chaîne aléatoire longue).

### 3. Créer l'environnement Python

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
```

### 4. Initialiser la base de données

```bash
python seed.py
```
→ crée les 8 tables + remplit les 3 niveaux IA (Basique, Pro, Max)

### 5. Lancer le backend

```bash
uvicorn main:app --reload --port 8000
```
→ documentation interactive : http://localhost:8000/docs

### 6. Lancer le frontend (nouveau terminal)

```bash
cd frontend
python -m http.server 3000
```
→ interface : http://localhost:3000

---

## 🗄️ Base de données — 8 tables

```
modeles_ia    → Basique / Pro / Max
utilisateurs  → comptes (anonyme ou authentifié)
sessions      → tokens JWT de connexion
parametres    → thème, langue, modèle par défaut (1↔1 avec utilisateurs)
chats         → conversations (titre auto-généré par l'IA)
messages      → questions / réponses + réactions like/dislike
fichiers      → PDF/image/DOCX uploadés, contenu extrait pour Gemini
recherches    → historique des recherches dans le chat
```

---

## 🛣️ Routes API

```
POST   /api/auth/anonyme           → crée un utilisateur anonyme + token
POST   /api/auth/inscription        → crée un compte (conserve l'historique anonyme)
POST   /api/auth/connexion           → connexion par email/mot de passe
POST   /api/auth/deconnexion          → révoque la session

POST   /api/chats                      → nouvelle conversation
GET    /api/chats                       → historique (épinglés/récents/archivés)
GET    /api/chats/recherche?q=...        → recherche par mot-clé
GET    /api/chats/{id}                    → messages d'une conversation
PATCH  /api/chats/{id}                     → renommer/épingler/archiver
DELETE /api/chats/{id}                      → supprimer

POST   /api/messages                          → envoyer message → réponse Gemini
PATCH  /api/messages/{id}/reaction              → like/dislike

POST   /api/fichiers/upload?message_id=...       → upload PDF/image/DOCX (max 5)

GET    /api/parametres                              → mes préférences
PATCH  /api/parametres                               → modifier thème/langue/modèle
GET    /api/modeles                                   → liste Basique/Pro/Max
```

---

## 📁 Structure du projet

```
ai-math-chatbot/
├── backend/
│   ├── main.py            → serveur FastAPI + branchement des routes
│   ├── models.py           → 8 tables SQLAlchemy
│   ├── database.py          → connexion PostgreSQL
│   ├── schemas.py             → validation Pydantic
│   ├── security.py             → bcrypt + JWT
│   ├── dependencies.py          → identification utilisateur (auth/anonyme)
│   ├── gemini_service.py         → appels à l'API Gemini
│   ├── seed.py                    → données initiales (modèles IA)
│   ├── routes/
│   │   ├── auth.py
│   │   ├── chats.py
│   │   ├── messages.py
│   │   ├── fichiers.py
│   │   └── parametres.py
│   ├── uploads/                    → fichiers uploadés par les utilisateurs
│   ├── requirements.txt
│   └── .env
└── frontend/
    ├── index.html              → interface chat
    ├── css/style.css            → thème clair/sombre
    ├── js/chat.js                → connecté aux routes API ci-dessus
    └── pages/
        ├── connexion.html
        ├── inscription.html
        └── parametres.html
```

---

## 🛣️ Prochaines étapes

- [ ] Reconnaissance vocale (Whisper) — bouton micro déjà présent côté frontend
- [ ] Streaming des réponses Gemini (effet de frappe en temps réel)
- [ ] Export PDF de l'historique
