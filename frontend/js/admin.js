// ============================================================
//  admin.js — Tableau de bord administrateur (version pro)
//  Routes /api/admin/* (protégées côté serveur).
// ============================================================

let estSuperadmin = false;
let monId = null;      // id du compte connecté (pour bloquer les actions sur soi-même)
let cacheUsers = [];   // garde la liste pour le filtrage côté client

const headersAuth = () => ({ "Authorization": `Bearer ${localStorage.getItem("token")}` });
const headersJSON = () => ({ "Content-Type": "application/json", ...headersAuth() });

function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, c => (
        { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
}

// ── Notifications (toasts) ──
function toast(message, type = "info") {
    const couleurs = { info: "toast-info", success: "toast-success", danger: "toast-danger", warning: "toast-warning" };
    const icones = { info: "bi-info-circle", success: "bi-check-circle", danger: "bi-x-circle", warning: "bi-exclamation-triangle" };
    const el = document.createElement("div");
    el.className = `admin-toast ${couleurs[type] || couleurs.info}`;
    el.innerHTML = `<i class="bi ${icones[type] || icones.info}"></i> <span>${esc(message)}</span>`;
    document.getElementById("admin-toasts").appendChild(el);
    setTimeout(() => el.classList.add("visible"), 10);
    setTimeout(() => { el.classList.remove("visible"); setTimeout(() => el.remove(), 300); }, 3200);
}

// ── Garde d'accès ──
async function verifierAcces() {
    try {
        const r = await fetch(`${API_URL}/api/admin/verifier`, { headers: headersAuth() });
        if (r.status === 401) { redirigerVersConnexion(); return false; }
        const data = await r.json();
        if (!data.est_admin) {
            alert("⛔ Accès réservé aux administrateurs.");
            window.location.href = "../index.html";
            return false;
        }
        estSuperadmin = data.role === "superadmin";

        // Renseigne le bloc utilisateur de la sidebar à partir du compte connecté.
        let user = {};
        try { user = JSON.parse(localStorage.getItem("user") || "{}"); } catch (e) {}
        monId = user.id ?? null;
        const nomEl = document.getElementById("admin-nom");
        const avEl = document.getElementById("admin-avatar");
        const roleEl = document.getElementById("admin-bienvenue");
        if (nomEl) nomEl.textContent = user.nom || "Administrateur";
        if (avEl) avEl.textContent = initiales(user.nom || "Administrateur");
        if (roleEl) roleEl.textContent = data.role || "administrateur";
        return true;
    } catch (e) {
        alert("❌ Serveur injoignable.");
        window.location.href = "../index.html";
        return false;
    }
}

// ── Statistiques ──
async function chargerStats() {
    const r = await fetch(`${API_URL}/api/admin/stats`, { headers: headersAuth() });
    if (!r.ok) return;
    const { stats } = await r.json();
    const cartes = [
        ["Utilisateurs", stats.total_utilisateurs, "bi-people-fill"],
        ["Actifs", stats.total_utilisateurs_actifs, "bi-person-check-fill"],
        ["Conversations", stats.total_conversations, "bi-chat-dots-fill"],
        ["Messages", stats.total_messages, "bi-envelope-fill"],
        ["Fichiers", stats.total_fichiers, "bi-paperclip"],
    ];
    document.getElementById("zone-stats").innerHTML = cartes.map(([titre, val, ic]) => `
        <div class="stat-card">
          <span class="stat-ic"><i class="bi ${ic}"></i></span>
          <div class="stat-val">${val ?? 0}</div>
          <div class="stat-lbl">${titre}</div>
        </div>`).join("");
}

// ── Utilisateurs ──
function initiales(nom) {
    const parts = String(nom || "?").trim().split(/\s+/);
    return ((parts[0]?.[0] || "") + (parts[1]?.[0] || "")).toUpperCase() || "?";
}

function ligneUtilisateur(u) {
    const estMoi = u.id === monId;
    // Cible protégée : on ne peut ni désactiver ni supprimer :
    //  - soi-même, - le superadmin (jamais), - un administrateur si on n'est
    //    pas superadmin (un modérateur ne touche pas les admins).
    const protege = estMoi || u.role === "superadmin" || (!estSuperadmin && u.est_admin);

    // Bouton de rôle : réservé au superadmin, sur les comptes authentifiés,
    // jamais sur soi-même ni sur un autre superadmin.
    const actionRole = (estSuperadmin && u.type === "authentifie" && !estMoi && u.role !== "superadmin")
        ? `<button class="btn btn-sm ${u.est_admin ? 'btn-outline-secondary' : 'btn-outline-warning'} me-1"
                  onclick="basculerRole(${u.id}, ${!u.est_admin})"
                  title="${u.est_admin ? 'Retirer le rôle admin' : 'Promouvoir admin'}">
             <i class="bi ${u.est_admin ? 'bi-shield-minus' : 'bi-shield-plus'}"></i>
           </button>`
        : "";

    const actionStatut = protege ? "" :
        `<button class="btn btn-sm btn-outline-warning me-1" onclick="basculerStatut(${u.id}, ${!u.est_actif})" title="${u.est_actif ? 'Désactiver' : 'Activer'}">
           <i class="bi ${u.est_actif ? 'bi-pause-fill' : 'bi-play-fill'}"></i>
         </button>`;
    const actionSuppr = protege ? "" :
        `<button class="btn btn-sm btn-outline-danger" onclick="supprimerUtilisateur(${u.id}, '${esc(u.nom)}')" title="Supprimer">
           <i class="bi bi-trash"></i>
         </button>`;

    const actions = (actionRole + actionStatut + actionSuppr) ||
        `<span class="text-secondary" title="Compte protégé"><i class="bi bi-lock-fill"></i></span>`;

    const roleLabel = u.role === "superadmin"
        ? '<span class="pill pill-admin"><i class="bi bi-shield-fill-check"></i> Superadmin</span>'
        : (u.est_admin
            ? '<span class="pill pill-admin"><i class="bi bi-shield-check"></i> Modérateur</span>'
            : '<span class="text-secondary">Utilisateur</span>');

    return `
        <tr>
          <td>
            <div class="cellule-user">
              <span class="admin-avatar sm">${esc(initiales(u.nom))}</span>
              <div class="cellule-user-txt">
                <strong>${esc(u.nom)}${estMoi ? ' <span class="tag">vous</span>' : ''}</strong>
                <small>${esc(u.email || "—")}</small>
              </div>
            </div>
          </td>
          <td><span class="tag">${esc(u.type)}</span></td>
          <td>${u.est_actif
            ? '<span class="pill pill-ok"><i class="bi bi-check-circle-fill"></i> Actif</span>'
            : '<span class="pill pill-ko"><i class="bi bi-slash-circle-fill"></i> Désactivé</span>'}</td>
          <td>${roleLabel}</td>
          <td class="text-end text-nowrap">${actions}</td>
        </tr>`;
}

function afficherUtilisateurs(liste) {
    document.getElementById("tbody-users").innerHTML =
        liste.length ? liste.map(ligneUtilisateur).join("")
                     : `<tr><td colspan="5" class="text-center text-secondary py-4">Aucun utilisateur</td></tr>`;
    const cpt = document.getElementById("nav-count-users");
    if (cpt) cpt.textContent = cacheUsers.length;
}

async function chargerUtilisateurs() {
    const r = await fetch(`${API_URL}/api/admin/utilisateurs`, { headers: headersAuth() });
    if (!r.ok) return;
    cacheUsers = await r.json();
    appliquerFiltreUsers();
}

function appliquerFiltreUsers() {
    const terme = (document.getElementById("filtre-users").value || "").toLowerCase();
    const filtres = cacheUsers.filter(u =>
        (u.nom || "").toLowerCase().includes(terme) ||
        (u.email || "").toLowerCase().includes(terme)
    );
    afficherUtilisateurs(filtres);
}

async function basculerStatut(id, actif) {
    if (id === monId) { toast("Vous ne pouvez pas désactiver votre propre compte.", "warning"); return; }
    const r = await fetch(`${API_URL}/api/admin/utilisateurs/${id}/statut`, {
        method: "PATCH", headers: headersJSON(), body: JSON.stringify({ est_actif: actif })
    });
    if (r.ok) { toast(actif ? "Compte réactivé." : "Compte désactivé.", "success"); chargerUtilisateurs(); chargerStats(); }
    else { const e = await r.json().catch(() => ({})); toast(e.detail || "Erreur", "danger"); }
}

async function basculerRole(id, promouvoir) {
    const r = await fetch(`${API_URL}/api/admin/utilisateurs/${id}/role`, {
        method: "PATCH", headers: headersJSON(), body: JSON.stringify({ est_actif: promouvoir })
    });
    if (r.ok) { toast(promouvoir ? "Utilisateur promu administrateur." : "Rôle administrateur retiré.", "success"); chargerUtilisateurs(); }
    else { const e = await r.json().catch(() => ({})); toast(e.detail || "Erreur", "danger"); }
}

async function supprimerUtilisateur(id, nom) {
    if (id === monId) { toast("Vous ne pouvez pas supprimer votre propre compte.", "warning"); return; }
    if (!confirm(`Supprimer définitivement l'utilisateur « ${nom} » et toutes ses données ?`)) return;
    const r = await fetch(`${API_URL}/api/admin/utilisateurs/${id}`, { method: "DELETE", headers: headersAuth() });
    if (r.ok) { toast("Utilisateur supprimé.", "success"); chargerUtilisateurs(); chargerStats(); }
    else { const e = await r.json().catch(() => ({})); toast(e.detail || "Erreur", "danger"); }
}

// ── Modèles IA ──
async function chargerModeles() {
    const r = await fetch(`${API_URL}/api/admin/modeles`, { headers: headersAuth() });
    if (!r.ok) return;
    const modeles = await r.json();
    const cpt = document.getElementById("nav-count-models");
    if (cpt) cpt.textContent = modeles.length;
    document.getElementById("tbody-modeles").innerHTML = modeles.length ? modeles.map(m => `
        <tr>
          <td>${m.id}</td>
          <td class="fw-medium">${esc(m.nom)}</td>
          <td class="small text-secondary">${esc(m.description || "—")}</td>
          <td class="small"><code>${esc(m.modele_gemini)}</code></td>
          <td>
            <div class="form-check form-switch">
              <input class="form-check-input" type="checkbox" ${m.est_actif ? "checked" : ""} onchange="basculerModele(${m.id}, this.checked)">
            </div>
          </td>
          <td class="text-end">
            <button class="btn btn-sm btn-outline-danger" onclick="supprimerModele(${m.id}, '${esc(m.nom)}')" title="Supprimer">
              <i class="bi bi-trash"></i>
            </button>
          </td>
        </tr>`).join("") : `<tr><td colspan="6" class="text-center text-secondary py-3">Aucun modèle</td></tr>`;
}

async function basculerModele(id, actif) {
    const r = await fetch(`${API_URL}/api/admin/modeles/${id}`, {
        method: "PATCH", headers: headersJSON(), body: JSON.stringify({ est_actif: actif })
    });
    if (r.ok) toast(actif ? "Modèle activé." : "Modèle désactivé.", "success");
}

async function supprimerModele(id, nom) {
    if (!confirm(`Supprimer le modèle « ${nom} » ?`)) return;
    const r = await fetch(`${API_URL}/api/admin/modeles/${id}`, { method: "DELETE", headers: headersAuth() });
    if (r.ok) { toast("Modèle supprimé.", "success"); chargerModeles(); }
    else { const e = await r.json().catch(() => ({})); toast(e.detail || "Erreur", "danger"); }
}

function toutCharger() { chargerStats(); chargerUtilisateurs(); chargerModeles(); }

// ── Initialisation ──
// ── Navigation entre panneaux ──
const TITRES_PANNEAUX = {
    overview: ["Vue d'ensemble", "Statistiques générales de la plateforme"],
    users: ["Utilisateurs", "Gérer les comptes, statuts et rôles"],
    models: ["Modèles IA", "Configurer les modèles disponibles pour le chatbot"],
    account: ["Mon compte", "Sécurité et mot de passe"],
};

function activerPanneau(nom) {
    document.querySelectorAll(".admin-nav-item").forEach(b =>
        b.classList.toggle("active", b.dataset.panel === nom));
    document.querySelectorAll(".admin-panel").forEach(p =>
        p.classList.toggle("active", p.dataset.panel === nom));
    const [titre, sous] = TITRES_PANNEAUX[nom] || ["", ""];
    document.getElementById("page-titre").textContent = titre;
    document.getElementById("page-soustitre").textContent = sous;
}

document.addEventListener("DOMContentLoaded", async () => {
    if (!(await verifierAcces())) return;
    toutCharger();

    document.querySelectorAll(".admin-nav-item").forEach(btn =>
        btn.addEventListener("click", () => activerPanneau(btn.dataset.panel)));

    document.getElementById("btn-refresh").addEventListener("click", () => { toutCharger(); toast("Données actualisées.", "info"); });
    document.getElementById("filtre-users").addEventListener("input", appliquerFiltreUsers);
    document.getElementById("btn-logout").addEventListener("click", () => {
        localStorage.removeItem("token"); localStorage.removeItem("user");
        window.location.href = "connexion.html";
    });

    // Changement de mot de passe (Mon compte)
    const formMdp = document.getElementById("form-mdp");
    if (formMdp) {
        formMdp.addEventListener("submit", async (e) => {
            e.preventDefault();
            const ancien = document.getElementById("mdp-ancien").value;
            const nouveau = document.getElementById("mdp-nouveau").value;
            const confirme = document.getElementById("mdp-confirme").value;
            if (nouveau !== confirme) { toast("Les deux mots de passe ne correspondent pas.", "warning"); return; }
            const r = await fetch(`${API_URL}/api/auth/mot-de-passe`, {
                method: "PATCH", headers: headersJSON(),
                body: JSON.stringify({ ancien_mot_de_passe: ancien, nouveau_mot_de_passe: nouveau })
            });
            if (r.ok) { toast("Mot de passe modifié avec succès.", "success"); formMdp.reset(); }
            else { const err = await r.json().catch(() => ({})); toast(err.detail || "Erreur", "danger"); }
        });
    }

    const form = document.getElementById("form-modele");
    document.getElementById("btn-ajouter-modele").addEventListener("click", () => form.classList.toggle("d-none"));
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const body = {
            nom: document.getElementById("m-nom").value.trim(),
            description: document.getElementById("m-desc").value.trim(),
            modele_gemini: document.getElementById("m-gemini").value.trim(),
        };
        const r = await fetch(`${API_URL}/api/admin/modeles`, { method: "POST", headers: headersJSON(), body: JSON.stringify(body) });
        if (r.ok) { form.reset(); form.classList.add("d-none"); toast("Modèle créé.", "success"); chargerModeles(); }
        else { const err = await r.json().catch(() => ({})); toast(err.detail || "Erreur lors de l'ajout", "danger"); }
    });
});
