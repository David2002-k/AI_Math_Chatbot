/**
 * js/chat.js
 * ──────────────────────────────────────────────────────────────────
 * Gère l'affichage des salons, le chargement de l'historique PostgreSQL,
 * l'envoi des messages et le rendu dynamique KaTeX pour les mathématiques.
 * ──────────────────────────────────────────────────────────────────
 */

document.addEventListener("DOMContentLoaded", () => {
    const btnEnvoyer = document.getElementById("btn-envoyer");
    const inputMessage = document.getElementById("input-message");
    const zoneMessages = document.getElementById("zone-messages");
    const welcomeMessage = document.getElementById("welcome-message");
    const btnUpload = document.getElementById("btn-upload");
    const inputFichier = document.getElementById("input-fichier");
    const apercuFichiers = document.getElementById("apercu-fichiers");
    const btnNouveauChat = document.getElementById("btn-nouveau-chat");
    const listeChatsContainer = document.getElementById("liste-chats");
    
    let selectedFiles = [];
    let currentChatId = null; // Stocke l'ID de la conversation active

    // Retire l'écran d'accueil s'il est encore affiché. On le recherche par id
    // à chaque appel (et non via une référence figée), car le bouton « Nouvelle
    // conversation » le recrée : une référence capturée une seule fois devient
    // obsolète et n'enlèverait pas le nouvel écran.
    function quitterAccueil() {
        const acc = document.getElementById("welcome-message");
        if (acc) acc.remove();
    }

    // Ouvre une discussion vide dans la zone principale (utilisé quand on joint
    // un fichier alors qu'aucune conversation n'est ouverte) : on sort de
    // l'accueil et on prépare la zone, sans quitter la discussion.
    function ouvrirDiscussionVide(titre = "Nouvelle discussion") {
        quitterAccueil();
        const titreEl = document.getElementById("current-chat-title");
        if (titreEl) titreEl.innerText = titre;
        zoneMessages.innerHTML = "";
    }

    // ─── Rendu KaTeX sécurisé : ne casse jamais l'affichage du texte si KaTeX est indisponible ───
    function rendreMaths(element) {
        if (typeof renderMathInElement !== "function") {
            console.warn("KaTeX non chargé : les formules resteront en texte brut.");
            return;
        }
        try {
            renderMathInElement(element, {
                delimiters: [
                    {left: "$$", right: "$$", display: true},
                    {left: "\\[", right: "\\]", display: true},
                    {left: "$", right: "$", display: false},
                    {left: "\\(", right: "\\)", display: false}
                ],
                throwOnError: false
            });
        } catch (err) {
            console.warn("Erreur de rendu KaTeX (ignorée) :", err);
        }
    }

    // Au démarrage, on charge l'historique de l'utilisateur connecté
    chargerHistoriqueChats();

    // ─── Recherche dans l'historique (titre + contenu des messages, côté serveur) ───
    const inputRecherche = document.getElementById("recherche-chat");
    if (inputRecherche) {
        let minuteurRecherche = null;
        inputRecherche.addEventListener("input", () => {
            const terme = inputRecherche.value.trim();
            clearTimeout(minuteurRecherche);
            // Petit délai (debounce) pour ne pas appeler l'API à chaque frappe.
            minuteurRecherche = setTimeout(() => {
                if (terme.length === 0) {
                    chargerHistoriqueChats();      // champ vidé → on remet tout l'historique
                } else {
                    rechercherChats(terme);
                }
            }, 250);
        });
    }

    // Ferme tout menu contextuel ouvert dès qu'on clique ailleurs sur la page
    document.addEventListener("click", () => {
        document.querySelectorAll(".menu-chat-contextuel.ouvert").forEach(m => m.classList.remove("ouvert"));
    });

    // ─── 1. CHARGEMENT DE L'HISTORIQUE (CORRECTION DU BLOCAGE) ───
    async function chargerHistoriqueChats() {
        if (!listeChatsContainer) return;

        try {
            const response = await fetch(`${API_URL}/api/chats`, {
                method: "GET",
                headers: {
                    "Authorization": `Bearer ${localStorage.getItem("token")}`
                }
            });

            if (response.status === 401) {
                // Token périmé / session perdue dès l'ouverture de l'app :
                // on purge et on renvoie vers la connexion plutôt que de laisser
                // une interface à moitié fonctionnelle (historique faussement vide).
                redirigerVersConnexion();
                return;
            }

            if (!response.ok) throw new Error("Erreur serveur lors du chargement");

            const chats = await response.json();
            afficherChats(chats);

        } catch (error) {
            console.error("Erreur historique :", error);
            listeChatsContainer.innerHTML = `<div class="text-danger small px-2">Erreur de chargement</div>`;
        }
    }

    // ─── Recherche serveur : titre OU contenu des messages ───
    async function rechercherChats(terme) {
        if (!listeChatsContainer) return;
        try {
            const response = await fetch(`${API_URL}/api/chats/recherche?q=${encodeURIComponent(terme)}`, {
                headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
            });
            if (response.status === 401) { redirigerVersConnexion(); return; }
            if (!response.ok) throw new Error("Erreur recherche");
            const chats = await response.json();
            afficherChats(chats, `Aucun résultat pour « ${terme} »`);
        } catch (error) {
            console.error("Erreur recherche :", error);
        }
    }

    // ─── Rendu d'une liste de conversations dans la barre latérale ───
    function afficherChats(chats, messageVide = "Aucune conversation") {
        if (!listeChatsContainer) return;
        listeChatsContainer.innerHTML = "";

        if (!chats || chats.length === 0) {
            listeChatsContainer.innerHTML = `<div class="text-secondary small px-2">${messageVide}</div>`;
            return;
        }

        // Génération dynamique des salons dans la barre latérale
        chats.forEach(chat => {
                const chatItem = document.createElement("div");
                chatItem.className = "chat-sidebar-item p-2 mb-1 rounded text-light small d-flex align-items-center gap-2";
                chatItem.dataset.chatId = chat.id;
                chatItem.dataset.titre = chat.titre || "Discussion Math";
                chatItem.style.cursor = "pointer";
                if (chat.id === currentChatId) chatItem.classList.add("actif");

                const titreSpan = document.createElement("span");
                titreSpan.className = "text-truncate flex-grow-1";
                titreSpan.textContent = chat.titre || "Discussion Math";

                const icone = document.createElement("i");
                icone.className = "bi bi-chat-left-text text-secondary";

                const btnMenu = document.createElement("button");
                btnMenu.className = "btn btn-sm btn-menu-chat p-0";
                btnMenu.innerHTML = `<i class="bi bi-three-dots"></i>`;
                btnMenu.title = "Renommer ou supprimer cette conversation";
                btnMenu.setAttribute("aria-label", "Renommer ou supprimer cette conversation");

                // Menu contextuel clair : deux actions explicites, pas de prompt() ambigu.
                const menu = document.createElement("ul");
                menu.className = "menu-chat-contextuel";

                const itemRenommer = document.createElement("li");
                itemRenommer.innerHTML = `<button type="button"><i class="bi bi-pencil"></i> Renommer</button>`;

                const itemSupprimer = document.createElement("li");
                itemSupprimer.innerHTML = `<button type="button" class="danger"><i class="bi bi-trash3"></i> Supprimer</button>`;

                menu.appendChild(itemRenommer);
                menu.appendChild(itemSupprimer);

                chatItem.appendChild(icone);
                chatItem.appendChild(titreSpan);
                chatItem.appendChild(btnMenu);
                chatItem.appendChild(menu);

                chatItem.addEventListener("click", () => selectionnerChat(chat.id, chat.titre));

                btnMenu.addEventListener("click", (e) => {
                    e.stopPropagation();
                    const etaitOuvert = menu.classList.contains("ouvert");
                    document.querySelectorAll(".menu-chat-contextuel.ouvert").forEach(m => m.classList.remove("ouvert"));
                    if (!etaitOuvert) menu.classList.add("ouvert");
                });

                itemRenommer.querySelector("button").addEventListener("click", async (e) => {
                    e.stopPropagation();
                    menu.classList.remove("ouvert");
                    const nouveauTitre = prompt("Nouveau nom de la conversation :", chat.titre);
                    if (nouveauTitre === null || nouveauTitre.trim() === "") return;
                    await renommerChat(chat.id, nouveauTitre.trim());
                });

                itemSupprimer.querySelector("button").addEventListener("click", async (e) => {
                    e.stopPropagation();
                    menu.classList.remove("ouvert");
                    if (!confirm(`Supprimer définitivement "${chat.titre}" ?`)) return;
                    await supprimerChat(chat.id);
                });

                listeChatsContainer.appendChild(chatItem);
            });
    }

    // Renomme une conversation (PATCH /api/chats/{id})
    async function renommerChat(chatId, nouveauTitre) {
        try {
            await fetch(`${API_URL}/api/chats/${chatId}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${localStorage.getItem("token")}`
                },
                body: JSON.stringify({ titre: nouveauTitre })
            });
            if (chatId === currentChatId) {
                document.getElementById("current-chat-title").innerText = nouveauTitre;
            }
            chargerHistoriqueChats();
        } catch (err) {
            alert("❌ Impossible de renommer la conversation.");
        }
    }

    // Supprime une conversation (DELETE /api/chats/{id})
    async function supprimerChat(chatId) {
        try {
            const response = await fetch(`${API_URL}/api/chats/${chatId}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
            });

            if (response.status === 401) { redirigerVersConnexion(); return; }

            // On vérifie réellement le succès : sans ça, une erreur serveur
            // (ex. 500) passait inaperçue et la conversation « refusait » de partir.
            if (!response.ok) {
                let detail = `Erreur serveur (${response.status})`;
                try { const e = await response.json(); if (e.detail) detail = e.detail; } catch (_) {}
                alert(`❌ Suppression impossible : ${detail}`);
                return;
            }

            if (chatId === currentChatId && btnNouveauChat) {
                btnNouveauChat.click();
            }
            chargerHistoriqueChats();
        } catch (err) {
            alert("❌ Impossible de joindre le serveur pour supprimer la conversation.");
        }
    }

    // Sélectionner un salon et charger ses messages passés
    async function selectionnerChat(chatId, titre) {
        currentChatId = chatId;
        document.getElementById("current-chat-title").innerText = titre;
        document.querySelectorAll("#liste-chats .chat-sidebar-item").forEach(item => {
            item.classList.toggle("actif", Number(item.dataset.chatId) === chatId);
        });
        if (welcomeMessage) welcomeMessage.remove();
        zoneMessages.innerHTML = `<div class="text-center py-3 text-secondary"><div class="spinner-border spinner-border-sm text-primary"></div> Chargement...</div>`;

        try {
            const response = await fetch(`${API_URL}/api/chats/${chatId}`, {
                headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
            });
            if (!response.ok) {
                const erreurData = await response.json().catch(() => ({}));
                throw new Error(erreurData.detail || `Erreur serveur (${response.status})`);
            }
            
            const messages = await response.json();
            zoneMessages.innerHTML = "";

            messages.forEach(msg => {
                if (msg.role === "user") {
                    appendMessage(msg.contenu, "user");
                } else {
                    appendMessage(formaterTexteIA(msg.contenu), "bot");
                }
            });

            // Forcer le rendu mathématique global sur l'historique chargé
            rendreMaths(zoneMessages);

        } catch (err) {
            console.error("Erreur historique (détail) :", err);
            zoneMessages.innerHTML = `<div class="text-danger small text-center py-3">Erreur : ${err.message || "récupération des messages impossible"}</div>`;
        }
    }

    // ─── 2. ENVOI DE MESSAGE ───
    async function gererEnvoi() {
        const text = inputMessage.value.trim();
        if (!text && selectedFiles.length === 0) return;

        quitterAccueil();

        // Si aucun salon n'est ouvert, on en crée un par défaut en BDD de manière transparente
        if (!currentChatId) {
            try {
                const response = await fetch(`${API_URL}/api/chats`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${localStorage.getItem("token")}`
                    },
                    body: JSON.stringify({ titre: text.substring(0, 25) || "Nouvelle discussion" })
                });
                if (response.status === 401) {
                    redirigerVersConnexion();
                    return;
                }
                const nouveauChat = await response.json();
                currentChatId = nouveauChat.id;
                chargerHistoriqueChats(); // Rafraîchit la sidebar
            } catch (err) {
                console.error("Impossible de créer le salon :", err);
                alert("❌ Impossible de créer la conversation. Vérifie que le serveur backend tourne bien.");
                return;
            }
        }

        // Envoi réel des fichiers joints, maintenant qu'on dispose d'un chat_id.
        // (L'ajout était purement local ; c'est ici qu'on les transmet au serveur,
        //  qui les rattachera automatiquement au message envoyé juste après.)
        if (selectedFiles.length > 0) {
            for (const item of selectedFiles) {
                const res = await uploadFileBackend(item.file, currentChatId);
                if (res && res.__unauthorized) { redirigerVersConnexion(); return; }
            }
        }

        // Afficher le message utilisateur, avec les fichiers joints sous forme de
        // pastilles (nom + icône), façon Claude.
        let userContent = "";
        if (selectedFiles.length > 0) {
            const puces = selectedFiles.map(item => {
                const nom = (item.file && item.file.name) ? item.file.name : "fichier";
                return `<span class="msg-fichier"><i class="bi bi-paperclip"></i> ${nom.replace(/[&<>"]/g, "")}</span>`;
            }).join("");
            userContent += `<div class="msg-fichiers">${puces}</div>`;
        }
        if (text) userContent += `<div>${text.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]))}</div>`;

        appendMessage(userContent, "user");
        inputMessage.value = "";
        selectedFiles = [];
        apercuFichiers.innerHTML = "";
        inputMessage.style.height = "auto";

        // Indicateur de chargement
        const loadingId = appendMessage(`<div class="typing-dots"><span></span><span></span><span></span></div>`, "bot");
        const botBubble = document.getElementById(loadingId);

        // Lancer la requête en streaming : la réponse s'affiche au fur et à mesure
        await streamChatMessage(currentChatId, text, botBubble, (titre) => {
            if (titre) {
                document.getElementById("current-chat-title").innerText = titre;
                chargerHistoriqueChats();
            }
        });

        zoneMessages.scrollTop = zoneMessages.scrollHeight;
    }

    // ─── Réception de la réponse Gemini en streaming (effet de frappe) ───
    async function streamChatMessage(chatId, contenu, botBubble, onFin) {
        let brut = "";
        let premierFragment = true;

        try {
            const response = await fetch(`${API_URL}/api/messages/stream`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${localStorage.getItem("token")}`
                },
                body: JSON.stringify({ chat_id: chatId, contenu: contenu, modele_id: null })
            });

            if (response.status === 401) {
                redirigerVersConnexion();
                return;
            }
            if (!response.ok || !response.body) {
                throw new Error(`Erreur serveur (${response.status})`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let tampon = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                tampon += decoder.decode(value, { stream: true });
                const lignes = tampon.split("\n\n");
                tampon = lignes.pop(); // garde le fragment incomplet pour le prochain tour

                for (const ligne of lignes) {
                    if (!ligne.startsWith("data: ")) continue;
                    const evt = JSON.parse(ligne.slice(6));

                    if (evt.erreur) throw new Error(evt.erreur);

                    if (evt.delta) {
                        const bulle = botBubble.querySelector(".bubble");
                        if (premierFragment) {
                            // On bascule sur un simple <span> de texte brut : pas de ré-analyse
                            // markdown/HTML à chaque fragment, donc pas de "saut" visuel —
                            // le texte s'écoule en continu, comme sur Claude.
                            bulle.innerHTML = `<span class="texte-en-flux"></span>`;
                            premierFragment = false;
                        }
                        brut += evt.delta;
                        bulle.querySelector(".texte-en-flux").textContent = brut;
                        zoneMessages.scrollTop = zoneMessages.scrollHeight;
                    }

                    if (evt.fin) {
                        // Une fois le flux terminé, on applique le formatage markdown
                        // complet (gras, listes, titres...) puis le rendu KaTeX.
                        botBubble.querySelector(".bubble").innerHTML = formaterTexteIA(brut);
                        rendreMaths(botBubble);
                        if (onFin) onFin(evt.titre);
                    }
                }
            }
        } catch (err) {
            console.error("Erreur streaming :", err);
            botBubble.querySelector(".bubble").innerHTML = `❌ ${err.message || "Impossible de joindre le serveur."}`;
        }
    }

    // Déclencheurs d'envoi
    if (btnEnvoyer) btnEnvoyer.addEventListener("click", gererEnvoi);
    if (inputMessage) {
        inputMessage.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                gererEnvoi();
            }
        });
    }

    // ─── 3. AJOUT DE BULLE DANS L'ECRAN ───
    // ─── Mise en forme du texte généré par l'IA (espacement, gras, listes) ───
    function formaterTexteIA(texte) {
        if (!texte) return "";

        // ── Étape 1 : on extrait les blocs LaTeX (\[...\] et \(...\)) AVANT tout traitement,
        // pour que le formatage markdown (retours à la ligne, listes...) ne les abîme jamais.
        const segmentsMath = [];
        let proteges = texte.replace(/\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)/g, (match) => {
            segmentsMath.push(match);
            return `@@MATH${segmentsMath.length - 1}@@`;
        });

        // On échappe seulement < et > (anti-XSS) sur le texte restant, jamais & : LaTeX l'utilise comme séparateur de colonnes
        let html = proteges.replace(/</g, "&lt;").replace(/>/g, "&gt;");

        // ## Titres markdown → <h6>
        html = html.replace(/^#{1,6}\s+(.+)$/gm, "<h6 class='fw-bold mt-3 mb-2'>$1</h6>");
        // **gras** → <strong>
        html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
        // Listes à puces "- item" ou "* item" en début de ligne
        html = html.replace(/^[-*]\s+(.+)$/gm, "<li>$1</li>");
        html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul class="mb-2 ps-3">${m.replace(/\n/g, "")}</ul>`);
        // Lignes horizontales "---" → séparateur visuel
        html = html.replace(/^---+$/gm, "<hr class='border-secondary my-3'>");
        // Doubles retours à la ligne → nouveau paragraphe, simple retour → <br>
        html = html.split(/\n{2,}/).map(p => `<p class="mb-2">${p.replace(/\n/g, "<br>")}</p>`).join("");

        // ── Étape 2 : on replace les blocs LaTeX, intacts, à la place des marqueurs ──
        html = html.replace(/@@MATH(\d+)@@/g, (_, i) => segmentsMath[parseInt(i)]);

        return html;
    }

    function appendMessage(htmlContent, sender) {
        const uniqueId = "msg-" + Date.now() + Math.floor(Math.random() * 1000);
        const msgContainer = document.createElement("div");
        msgContainer.id = uniqueId;
        msgContainer.className = `msg-container msg-${sender}`;
        
        msgContainer.innerHTML = `<div class="bubble">${htmlContent}</div>`;
        zoneMessages.appendChild(msgContainer);
        zoneMessages.scrollTop = zoneMessages.scrollHeight;
        return uniqueId;
    }

    // ─── 4. GESTION DE L'UPLOAD DE FICHIERS ───
    // Le fichier est envoyé et traité (extraction du texte) immédiatement à la
    // sélection, avec un indicateur visuel pendant le traitement (spinner → coché).
    if (btnUpload && inputFichier) {
        btnUpload.addEventListener("click", () => inputFichier.click());
        // Joindre un fichier est une action PUREMENT LOCALE : on ne crée aucune
        // conversation et on n'appelle pas le serveur ici. Les fichiers ne sont
        // réellement envoyés qu'au moment de l'envoi du message (voir gererEnvoi).
        // → impossible de « quitter le chat » ou de recharger la page à l'ajout.
        inputFichier.addEventListener("change", (e) => {
            const fichiers = Array.from(e.target.files);
            inputFichier.value = ""; // permet de re-sélectionner le même fichier

            fichiers.forEach((file) => {
                const estImage = file.type.startsWith("image/");
                const objectUrl = estImage ? URL.createObjectURL(file) : null;
                const vignetteHTML = estImage
                    ? `<img src="${objectUrl}" class="apercu-vignette" alt="">`
                    : `<span class="apercu-vignette d-flex align-items-center justify-content-center"><i class="bi bi-file-earmark-text"></i></span>`;

                const badge = document.createElement("span");
                badge.className = "apercu-fichier badge d-flex align-items-center gap-2 p-1 pe-2";
                badge.innerHTML = `
                    <span class="apercu-media">${vignetteHTML}</span>
                    <span class="apercu-nom">${file.name.replace(/[&<>"]/g, "")}</span>`;

                const entree = { file, objectUrl };
                selectedFiles.push(entree);

                const btnRetirer = document.createElement("button");
                btnRetirer.type = "button";
                btnRetirer.className = "btn-close btn-close-white apercu-retirer";
                btnRetirer.setAttribute("aria-label", "Retirer le fichier");
                btnRetirer.addEventListener("click", () => {
                    selectedFiles = selectedFiles.filter(it => it !== entree);
                    if (objectUrl) URL.revokeObjectURL(objectUrl);
                    badge.remove();
                });
                badge.appendChild(btnRetirer);
                apercuFichiers.appendChild(badge);
            });
        });
    }

    // ─── 5. BOUTON NOUVELLE CONVERSATION ───
    if (btnNouveauChat) {
        btnNouveauChat.addEventListener("click", () => {
            currentChatId = null;
            document.getElementById("current-chat-title").innerText = "Nouvelle discussion";
            zoneMessages.innerHTML = `
                <div class="text-center text-secondary my-auto py-5" id="welcome-message">
                  <i class="bi bi-calculator-fill display-3 text-primary opacity-75"></i>
                  <h4 class="mt-3 fw-bold text-light">Bienvenue sur AI Math Chatbot 👋</h4>
                  <p class="text-muted mx-auto" style="max-width: 500px;">
                    Posez votre question mathématique, importez un exercice ou utilisez votre micro pour démarrer.
                  </p>
                </div>`;
        });
    }

    // ─── 6. SÉLECTEUR DE MODÈLE IA (dropdown manuel, sans JS Bootstrap) ───
    const btnSelecteurModele = document.getElementById("btn-selecteur-modele");
    const menuSelecteurModele = document.getElementById("menu-selecteur-modele");
    if (btnSelecteurModele && menuSelecteurModele) {
        btnSelecteurModele.addEventListener("click", (e) => {
            e.stopPropagation();
            menuSelecteurModele.classList.toggle("ouvert");
        });
        document.addEventListener("click", () => menuSelecteurModele.classList.remove("ouvert"));
    }
    document.querySelectorAll(".dropdown-item[data-modele]").forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const model = e.currentTarget.getAttribute("data-modele");
            document.getElementById("modele-actuel").innerText = model;
            if (menuSelecteurModele) menuSelecteurModele.classList.remove("ouvert");
        });
    });

    // ─── 7. SUGGESTIONS RAPIDES SUR L'ÉCRAN D'ACCUEIL ───
    document.querySelectorAll(".suggestion-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            inputMessage.value = chip.getAttribute("data-suggestion");
            inputMessage.focus();
            gererEnvoi();
        });
    });
});