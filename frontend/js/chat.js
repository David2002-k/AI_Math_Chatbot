/* ─────────────────────────────────────────────
   chat.js
   Logique du frontend — AI Math Chatbot
   Connecté au vrai backend FastAPI (voir backend/routes/)
───────────────────────────────────────────── */

const API_URL = "http://localhost:8000";

// ── Éléments du DOM ───────────────────────────
const inputMessage     = document.getElementById("input-message");
const btnEnvoyer       = document.getElementById("btn-envoyer");
const zoneMessages     = document.getElementById("zone-messages");
const btnUpload        = document.getElementById("btn-upload");
const inputFichier     = document.getElementById("input-fichier");
const apercuFichiers   = document.getElementById("apercu-fichiers");
const btnMicro         = document.getElementById("btn-micro");
const btnNouveauChat   = document.getElementById("btn-nouveau-chat");
const btnToggleSidebar = document.getElementById("btn-toggle-sidebar");
const sidebar          = document.querySelector(".sidebar");
const modeleActuel     = document.getElementById("modele-actuel");
const btnToggleTheme   = document.getElementById("btn-toggle-theme");
const listeChats       = document.getElementById("liste-chats");
const rechercheInput   = document.getElementById("recherche-chat");

let fichiersSelectionnes = [];
let chatActuelId = null;
let modeleIdActuel = null;
let modelesDisponibles = [];


// ══════════════════════════════════════════════
// AUTHENTIFICATION — récupère ou crée un token
// ══════════════════════════════════════════════
async function obtenirToken() {
  let token = localStorage.getItem("token");
  if (token) return token;

  // Premier passage : crée un utilisateur anonyme côté backend
  const reponse = await fetch(`${API_URL}/api/auth/anonyme`, { method: "POST" });
  const data = await reponse.json();
  localStorage.setItem("token", data.access_token);
  return data.access_token;
}

async function appelAPI(chemin, options = {}) {
  const token = await obtenirToken();
  const headers = {
    "Authorization": `Bearer ${token}`,
    ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...options.headers
  };

  const reponse = await fetch(`${API_URL}${chemin}`, { ...options, headers });

  if (!reponse.ok) {
    const erreur = await reponse.json().catch(() => ({ detail: "Erreur serveur" }));
    throw new Error(erreur.detail || "Erreur API");
  }

  return reponse.status === 204 ? null : reponse.json();
}


// ══════════════════════════════════════════════
// THÈME — clair/sombre, synchronisé avec /api/parametres
// ══════════════════════════════════════════════
function appliquerThemeLocal(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("theme", theme);
  if (btnToggleTheme) {
    btnToggleTheme.querySelector("i").className = theme === "sombre" ? "bi bi-sun" : "bi bi-moon";
  }
}

appliquerThemeLocal(localStorage.getItem("theme") || "sombre");

if (btnToggleTheme) {
  btnToggleTheme.addEventListener("click", async () => {
    const actuel = document.documentElement.getAttribute("data-theme");
    const nouveau = actuel === "sombre" ? "clair" : "sombre";
    appliquerThemeLocal(nouveau);
    try {
      await appelAPI("/api/parametres", {
        method: "PATCH",
        body: JSON.stringify({ theme: nouveau })
      });
    } catch (e) { console.error(e); }
  });
}


// ══════════════════════════════════════════════
// CHARGEMENT INITIAL
// ══════════════════════════════════════════════
async function initialiser() {
  try {
    modelesDisponibles = await appelAPI("/api/modeles");
    if (modelesDisponibles.length > 0) {
      modeleIdActuel = modelesDisponibles.find(m => m.nom === "Basique")?.id || modelesDisponibles[0].id;
    }
  } catch (e) {
    console.error("Impossible de charger les modèles IA :", e);
  }

  await chargerHistorique();
}

initialiser();


// ══════════════════════════════════════════════
// HISTORIQUE DES CONVERSATIONS
// ══════════════════════════════════════════════
async function chargerHistorique() {
  try {
    const chats = await appelAPI("/api/chats");
    afficherHistorique(chats);
  } catch (e) {
    console.error("Erreur chargement historique :", e);
  }
}

function afficherHistorique(chats) {
  listeChats.innerHTML = "";

  if (chats.length === 0) {
    listeChats.innerHTML = `<div class="text-secondary small px-2 py-2">Aucune conversation pour l'instant.</div>`;
    return;
  }

  const epingles = chats.filter(c => c.est_epingle);
  const reste = chats.filter(c => !c.est_epingle);

  // ── Section Épinglés (toujours en premier, comme ChatGPT) ──
  if (epingles.length > 0) {
    ajouterSection("📌 Épinglés", epingles);
  }

  // ── Regroupe le reste par période (Aujourd'hui, Hier, 7 jours...) ──
  const groupes = grouperParPeriode(reste);

  for (const [titreGroupe, chatsGroupe] of groupes) {
    if (chatsGroupe.length > 0) {
      ajouterSection(titreGroupe, chatsGroupe);
    }
  }
}

function ajouterSection(titre, chats) {
  const titreDiv = document.createElement("div");
  titreDiv.className = "historique-section-titre";
  titreDiv.textContent = titre;
  listeChats.appendChild(titreDiv);

  chats.forEach(chat => listeChats.appendChild(creerElementChat(chat)));
}

// Regroupe les chats par période relative à aujourd'hui, comme ChatGPT.
// Retourne un Map ordonné : "Aujourd'hui" → [...], "Hier" → [...], etc.
function grouperParPeriode(chats) {
  const maintenant = new Date();
  const debutAujourdhui = new Date(maintenant.getFullYear(), maintenant.getMonth(), maintenant.getDate());
  const debutHier = new Date(debutAujourdhui);
  debutHier.setDate(debutHier.getDate() - 1);
  const debut7Jours = new Date(debutAujourdhui);
  debut7Jours.setDate(debut7Jours.getDate() - 7);
  const debut30Jours = new Date(debutAujourdhui);
  debut30Jours.setDate(debut30Jours.getDate() - 30);

  const groupes = new Map([
    ["Aujourd'hui", []],
    ["Hier", []],
    ["7 jours précédents", []],
    ["30 jours précédents", []],
  ]);

  // Tri du plus récent au plus ancien
  const chatsTries = [...chats].sort(
    (a, b) => new Date(b.date_modification) - new Date(a.date_modification)
  );

  for (const chat of chatsTries) {
    const dateChat = new Date(chat.date_modification);

    if (dateChat >= debutAujourdhui) {
      groupes.get("Aujourd'hui").push(chat);
    } else if (dateChat >= debutHier) {
      groupes.get("Hier").push(chat);
    } else if (dateChat >= debut7Jours) {
      groupes.get("7 jours précédents").push(chat);
    } else if (dateChat >= debut30Jours) {
      groupes.get("30 jours précédents").push(chat);
    } else {
      // Groupé par mois/année, ex: "Mars 2026" — comme ChatGPT pour les anciens chats
      const cle = dateChat.toLocaleDateString("fr-FR", { month: "long", year: "numeric" });
      const cleCapitalisee = cle.charAt(0).toUpperCase() + cle.slice(1);
      if (!groupes.has(cleCapitalisee)) groupes.set(cleCapitalisee, []);
      groupes.get(cleCapitalisee).push(chat);
    }
  }

  return groupes;
}

function creerElementChat(chat) {
  const div = document.createElement("div");
  div.className = `chat-item d-flex align-items-center justify-content-between${chat.id === chatActuelId ? " active" : ""}`;
  div.dataset.chatId = chat.id;
  div.title = chat.titre;

  div.innerHTML = `
    <span class="chat-titre-tronque"><i class="bi bi-chat-left-text me-2"></i>${chat.titre}</span>
    <div class="chat-actions">
      <i class="bi ${chat.est_epingle ? "bi-pin-angle-fill" : "bi-pin-angle"}" title="${chat.est_epingle ? "Désépingler" : "Épingler"}" data-action="epingler"></i>
      <i class="bi bi-pencil" title="Renommer" data-action="renommer"></i>
      <i class="bi ${chat.est_archive ? "bi-box-arrow-up" : "bi-archive"}" title="${chat.est_archive ? "Désarchiver" : "Archiver"}" data-action="archiver"></i>
      <i class="bi bi-trash" title="Supprimer" data-action="supprimer"></i>
    </div>
  `;

  div.addEventListener("click", (e) => {
    if (e.target.closest("[data-action]")) return;
    ouvrirChat(chat.id);
  });

  div.querySelector('[data-action="epingler"]').addEventListener("click", async (e) => {
    e.stopPropagation();
    await appelAPI(`/api/chats/${chat.id}`, {
      method: "PATCH",
      body: JSON.stringify({ est_epingle: !chat.est_epingle })
    });
    chargerHistorique();
  });

  div.querySelector('[data-action="archiver"]').addEventListener("click", async (e) => {
    e.stopPropagation();
    await appelAPI(`/api/chats/${chat.id}`, {
      method: "PATCH",
      body: JSON.stringify({ est_archive: !chat.est_archive })
    });
    if (chat.id === chatActuelId) demarrerNouvelleConversation();
    chargerHistorique();
  });

  div.querySelector('[data-action="renommer"]').addEventListener("click", async (e) => {
    e.stopPropagation();
    const nouveauTitre = prompt("Nouveau nom de la conversation :", chat.titre);
    if (nouveauTitre && nouveauTitre.trim()) {
      await appelAPI(`/api/chats/${chat.id}`, {
        method: "PATCH",
        body: JSON.stringify({ titre: nouveauTitre.trim() })
      });
      chargerHistorique();
    }
  });

  div.querySelector('[data-action="supprimer"]').addEventListener("click", async (e) => {
    e.stopPropagation();
    if (confirm("Supprimer définitivement cette conversation ?")) {
      await appelAPI(`/api/chats/${chat.id}`, { method: "DELETE" });
      if (chat.id === chatActuelId) demarrerNouvelleConversation();
      chargerHistorique();
    }
  });

  return div;
}

// Recherche dans l'historique
if (rechercheInput) {
  let timeoutRecherche;
  rechercheInput.addEventListener("input", () => {
    clearTimeout(timeoutRecherche);
    timeoutRecherche = setTimeout(async () => {
      const q = rechercheInput.value.trim();
      if (!q) return chargerHistorique();
      try {
        const resultats = await appelAPI(`/api/chats/recherche?q=${encodeURIComponent(q)}`);
        afficherHistorique(resultats);
      } catch (e) { console.error(e); }
    }, 300);
  });
}


// ══════════════════════════════════════════════
// OUVRIR UNE CONVERSATION EXISTANTE
// ══════════════════════════════════════════════
async function ouvrirChat(chatId) {
  chatActuelId = chatId;

  document.querySelectorAll(".chat-item").forEach(i => {
    i.classList.toggle("active", parseInt(i.dataset.chatId) === chatId);
  });

  try {
    const messages = await appelAPI(`/api/chats/${chatId}`);
    zoneMessages.innerHTML = "";
    messages.forEach(m => afficherMessage(m.role, m.contenu, m.id, m.reaction));
  } catch (e) {
    console.error("Erreur chargement messages :", e);
  }
}


// ══════════════════════════════════════════════
// NOUVELLE CONVERSATION
// ══════════════════════════════════════════════
function demarrerNouvelleConversation() {
  chatActuelId = null;
  zoneMessages.innerHTML = `
    <div class="text-center text-secondary mt-5">
      <i class="bi bi-calculator display-1"></i>
      <h4 class="mt-3">Bienvenue sur AI Math Chatbot</h4>
      <p>Posez une question, uploadez un exercice ou utilisez le micro pour commencer.</p>
    </div>
  `;
  document.querySelectorAll(".chat-item").forEach(i => i.classList.remove("active"));
}

btnNouveauChat.addEventListener("click", demarrerNouvelleConversation);


// ══════════════════════════════════════════════
// AGRANDISSEMENT AUTOMATIQUE DU TEXTAREA
// ══════════════════════════════════════════════
inputMessage.addEventListener("input", () => {
  inputMessage.style.height = "auto";
  inputMessage.style.height = inputMessage.scrollHeight + "px";
});

inputMessage.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    envoyerMessage();
  }
});


// ══════════════════════════════════════════════
// ENVOI D'UN MESSAGE — appelle /api/chats puis /api/messages
// ══════════════════════════════════════════════
btnEnvoyer.addEventListener("click", envoyerMessage);

async function envoyerMessage() {
  const texte = inputMessage.value.trim();
  if (!texte && fichiersSelectionnes.length === 0) return;

  const bienvenue = zoneMessages.querySelector(".text-center.text-secondary");
  if (bienvenue) bienvenue.remove();

  afficherMessage("user", texte);

  inputMessage.value = "";
  inputMessage.style.height = "auto";
  const fichiersAEnvoyer = [...fichiersSelectionnes];
  fichiersSelectionnes = [];
  apercuFichiers.innerHTML = "";

  const indicateurId = afficherMessage("assistant", "<em>L'IA réfléchit...</em>");

  try {
    // 1. Crée la conversation si c'est la première fois
    if (!chatActuelId) {
      const nouveauChat = await appelAPI("/api/chats", {
        method: "POST",
        body: JSON.stringify({ modele_id: modeleIdActuel })
      });
      chatActuelId = nouveauChat.id;
    }

    // 2. Envoie le message à l'IA
    const messageIA = await appelAPI("/api/messages", {
      method: "POST",
      body: JSON.stringify({
        chat_id: chatActuelId,
        contenu: texte,
        modele_id: modeleIdActuel
      })
    });

    // 3. Upload des fichiers liés (si présents) — sur le message IA reçu
    if (fichiersAEnvoyer.length > 0) {
      const formData = new FormData();
      fichiersAEnvoyer.forEach(f => formData.append("fichiers", f));
      await appelAPI(`/api/fichiers/upload?message_id=${messageIA.id}`, {
        method: "POST",
        body: formData
      });
    }

    document.getElementById(indicateurId)?.remove();
    afficherMessage("assistant", messageIA.contenu, messageIA.id, messageIA.reaction);

    chargerHistorique();

  } catch (e) {
    document.getElementById(indicateurId)?.remove();
    afficherMessage("assistant", `⚠️ Erreur : ${e.message}`);
    console.error(e);
  }
}


// ══════════════════════════════════════════════
// AFFICHAGE D'UN MESSAGE DANS LE CHAT
// ══════════════════════════════════════════════
function afficherMessage(role, contenu, messageId = null, reaction = null) {
  const idUnique = "msg-" + (messageId || Date.now());
  const div = document.createElement("div");
  div.id = idUnique;
  div.className = `message message-${role === "user" ? "user" : "assistant"}`;

  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";
  contentDiv.innerHTML = contenu;
  div.appendChild(contentDiv);

  if (role === "assistant" && messageId) {
    const actions = document.createElement("div");
    actions.className = "message-actions";
    actions.innerHTML = `
      <i class="bi bi-hand-thumbs-up${reaction === "like" ? " active-like" : ""}" title="Utile" data-reaction="like"></i>
      <i class="bi bi-hand-thumbs-down${reaction === "dislike" ? " active-dislike" : ""}" title="Pas utile" data-reaction="dislike"></i>
      <i class="bi bi-clipboard" title="Copier"></i>
    `;
    div.appendChild(actions);

    const btnLike = actions.querySelector('[data-reaction="like"]');
    const btnDislike = actions.querySelector('[data-reaction="dislike"]');

    btnLike.addEventListener("click", async () => {
      const actif = btnLike.classList.toggle("active-like");
      btnDislike.classList.remove("active-dislike");
      await appelAPI(`/api/messages/${messageId}/reaction`, {
        method: "PATCH",
        body: JSON.stringify({ reaction: actif ? "like" : null })
      });
    });

    btnDislike.addEventListener("click", async () => {
      const actif = btnDislike.classList.toggle("active-dislike");
      btnLike.classList.remove("active-like");
      await appelAPI(`/api/messages/${messageId}/reaction`, {
        method: "PATCH",
        body: JSON.stringify({ reaction: actif ? "dislike" : null })
      });
    });

    actions.querySelector(".bi-clipboard").addEventListener("click", (e) => {
      navigator.clipboard.writeText(contentDiv.innerText);
      e.target.className = "bi bi-clipboard-check";
      setTimeout(() => { e.target.className = "bi bi-clipboard"; }, 1500);
    });
  }

  zoneMessages.appendChild(div);
  zoneMessages.scrollTop = zoneMessages.scrollHeight;

  rendreLatex(contentDiv);

  return idUnique;
}

// Rend les formules LaTeX ($...$ et $$...$$) avec KaTeX.
// Réessaie si la librairie n'est pas encore chargée (script "defer").
function rendreLatex(element, tentatives = 0) {
  if (window.renderMathInElement) {
    renderMathInElement(element, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false }
      ],
      throwOnError: false
    });
  } else if (tentatives < 10) {
    setTimeout(() => rendreLatex(element, tentatives + 1), 200);
  }


// ══════════════════════════════════════════════
// UPLOAD DE FICHIERS (max 5) — envoyés avec le prochain message
// ══════════════════════════════════════════════
btnUpload.addEventListener("click", () => inputFichier.click());

inputFichier.addEventListener("change", () => {
  const fichiers = Array.from(inputFichier.files);

  if (fichiersSelectionnes.length + fichiers.length > 5) {
    alert("Vous pouvez joindre au maximum 5 fichiers.");
    return;
  }

  fichiers.forEach(fichier => {
    fichiersSelectionnes.push(fichier);
    afficherApercuFichier(fichier);
  });

  inputFichier.value = "";
});

function afficherApercuFichier(fichier) {
  const badge = document.createElement("div");
  badge.className = "fichier-badge";

  const icone = fichier.type.includes("pdf") ? "bi-file-earmark-pdf"
              : fichier.type.includes("image") ? "bi-file-earmark-image"
              : "bi-file-earmark-word";

  badge.innerHTML = `
    <i class="bi ${icone}"></i>
    <span>${fichier.name}</span>
    <i class="bi bi-x-circle" title="Retirer"></i>
  `;

  badge.querySelector(".bi-x-circle").addEventListener("click", () => {
    fichiersSelectionnes = fichiersSelectionnes.filter(f => f !== fichier);
    badge.remove();
  });

  apercuFichiers.appendChild(badge);
}


// ══════════════════════════════════════════════
// ENREGISTREMENT VOCAL (micro) — Whisper à connecter
// ══════════════════════════════════════════════
let enregistrementEnCours = false;

btnMicro.addEventListener("click", () => {
  enregistrementEnCours = !enregistrementEnCours;
  btnMicro.classList.toggle("recording", enregistrementEnCours);

  if (enregistrementEnCours) {
    btnMicro.querySelector("i").className = "bi bi-stop-fill";
    // TODO : MediaRecorder API → envoyer à un futur /api/transcription (Whisper)
  } else {
    btnMicro.querySelector("i").className = "bi bi-mic";
  }
});


// ══════════════════════════════════════════════
// AFFICHAGE/MASQUAGE BARRE LATÉRALE (mobile)
// ══════════════════════════════════════════════
if (btnToggleSidebar) {
  btnToggleSidebar.addEventListener("click", () => {
    sidebar.classList.toggle("show");
  });
}


// ══════════════════════════════════════════════
// SÉLECTION DU MODÈLE IA (Basique/Pro/Max)
// ══════════════════════════════════════════════
document.querySelectorAll("[data-modele]").forEach(item => {
  item.addEventListener("click", async (e) => {
    e.preventDefault();
    const nomModele = item.getAttribute("data-modele");
    modeleActuel.textContent = nomModele;

    const modele = modelesDisponibles.find(m => m.nom === nomModele);
    if (modele) {
      modeleIdActuel = modele.id;
      if (chatActuelId) {
        await appelAPI(`/api/chats/${chatActuelId}`, {
          method: "PATCH",
          body: JSON.stringify({ modele_id: modele.id })
        });
      }
    }
  });
});
