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

    // ─── Recherche dans l'historique (filtrage côté client) ───
    const inputRecherche = document.getElementById("recherche-chat");
    if (inputRecherche) {
        inputRecherche.addEventListener("input", () => {
            const terme = inputRecherche.value.trim().toLowerCase();
            document.querySelectorAll("#liste-chats .chat-sidebar-item").forEach(item => {
                const titre = item.textContent.trim().toLowerCase();
                item.style.display = titre.includes(terme) ? "" : "none";
            });
        });
    }

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
                listeChatsContainer.innerHTML = `<div class="text-warning small px-2">Veuillez vous connecter.</div>`;
                return;
            }

            if (!response.ok) throw new Error("Erreur serveur lors du chargement");

            const chats = await response.json();
            listeChatsContainer.innerHTML = ""; // On efface le message "Chargement de l'historique..."

            if (chats.length === 0) {
                listeChatsContainer.innerHTML = `<div class="text-secondary small px-2">Aucune conversation</div>`;
                return;
            }

            // Génération dynamique des salons dans la barre latérale
            chats.forEach(chat => {
                const chatItem = document.createElement("div");
                chatItem.className = "chat-sidebar-item p-2 mb-1 rounded text-light small d-flex align-items-center gap-2";
                chatItem.style.cursor = "pointer";
                chatItem.innerHTML = `<i class="bi bi-chat-left-text text-secondary"></i> <span class="text-truncate">${chat.titre || "Discussion Math"}</span>`;
                
                chatItem.addEventListener("click", () => selectionnerChat(chat.id, chat.titre));
                listeChatsContainer.appendChild(chatItem);
            });

        } catch (error) {
            console.error("Erreur historique :", error);
            listeChatsContainer.innerHTML = `<div class="text-danger small px-2">Erreur de chargement</div>`;
        }
    }

    // Sélectionner un salon et charger ses messages passés
    async function selectionnerChat(chatId, titre) {
        currentChatId = chatId;
        document.getElementById("current-chat-title").innerText = titre;
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

        if (welcomeMessage) welcomeMessage.remove();

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
                    window.location.href = "pages/connexion.html";
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

        // Afficher le message utilisateur
        let userContent = text;
        if (selectedFiles.length > 0) {
            userContent += `<br><small class="text-info">📎 ${selectedFiles.length} fichier(s) joint(s)</small>`;
            for (let f of selectedFiles) {
                await uploadFileBackend(f, currentChatId); // Passage du currentChatId requis
            }
        }
        
        appendMessage(userContent, "user");
        inputMessage.value = "";
        selectedFiles = [];
        apercuFichiers.innerHTML = "";
        inputMessage.style.height = "auto";

        // Indicateur de chargement
        const loadingId = appendMessage(`<div class="typing-dots"><span></span><span></span><span></span></div>`, "bot");

        // Lancer la requête API vers Python
        const data = await sendChatMessage(currentChatId, text, null);
        if (!data) return; // 401 : redirection déjà en cours vers la connexion

        // Remplacer l'indicateur par la réponse finale de Gemini
        const botBubble = document.getElementById(loadingId);
        if (botBubble) {
            const contenu = data.contenu || "Désolé, je n'ai pas pu générer de réponse.";
            botBubble.querySelector(".bubble").innerHTML = formaterTexteIA(contenu);
            
            // Déclenchement de KaTeX pour les formules
            rendreMaths(botBubble);
        }
        
        zoneMessages.scrollTop = zoneMessages.scrollHeight;
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
    if (btnUpload && inputFichier) {
        btnUpload.addEventListener("click", () => inputFichier.click());
        inputFichier.addEventListener("change", (e) => {
            selectedFiles = Array.from(e.target.files);
            apercuFichiers.innerHTML = "";
            selectedFiles.forEach((file) => {
                const badge = document.createElement("span");
                badge.className = "badge bg-secondary d-flex align-items-center gap-1 p-2";
                badge.innerHTML = `<i class="bi bi-file-earmark-check"></i> ${file.name}`;
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

    // ─── 6. SÉLECTEUR DE MODÈLE IA ───
    document.querySelectorAll(".dropdown-item").forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const model = e.target.getAttribute("data-modele");
            document.getElementById("modele-actuel").innerText = model;
        });
    });
});