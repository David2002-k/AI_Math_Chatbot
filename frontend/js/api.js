// Adresse locale de ton serveur backend Python (FastAPI par défaut sur le port 8000)
const API_URL = "http://127.0.0.1:8000";

/**
 * Gère une session expirée/invalide (réponse HTTP 401).
 * On purge le token périmé AVANT de rediriger : sinon la garde de index.html
 * (qui ne teste que la présence d'un token) laisse l'utilisateur revenir et
 * reboucle indéfiniment sur des erreurs 401.
 */
function redirigerVersConnexion() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "pages/connexion.html";
}

/**
 * Envoie un message texte à l'API du chatbot
 * @param {number} chatId - L'identifiant de la conversation courante
 * @param {string} contenu - Le texte saisi par l'utilisateur
 * @param {number|null} modeleId - L'ID du modèle IA sélectionné (optionnel)
 * @returns {Promise<object>}
 */
async function sendChatMessage(chatId, contenu, modeleId = null) {
    try {
        const response = await fetch(`${API_URL}/api/messages`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            },
            body: JSON.stringify({ 
                chat_id: chatId, 
                contenu: contenu, 
                modele_id: modeleId 
            })
        });

        if (response.status === 401) {
            console.warn("Utilisateur déconnecté ou token expiré.");
            redirigerVersConnexion();
            return null;
        }

        if (!response.ok) {
            const erreurData = await response.json().catch(() => ({}));
            throw new Error(erreurData.detail || `Erreur serveur (${response.status})`);
        }

        return await response.json(); // Renvoie le MessageReponse complet enregistré en BDD
    } catch (error) {
        console.error("Erreur API Chat :", error);
        return {
            role: "assistant",
            contenu: `❌ ${error.message || "Impossible de joindre le serveur."}`
        };
    }
}

/**
 * Supprime un fichier joint encore "en attente" (avant l'envoi du message).
 * Utilisé par le bouton ✕ des badges d'aperçu.
 * @param {number} fichierId - L'ID du fichier renvoyé par l'upload
 * @returns {Promise<boolean>} true si la suppression a réussi
 */
async function deleteFileBackend(fichierId) {
    try {
        const response = await fetch(`${API_URL}/api/fichiers/${fichierId}`, {
            method: "DELETE",
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            }
        });
        return response.ok;
    } catch (error) {
        console.error("Erreur suppression fichier :", error);
        return false;
    }
}

/**
 * Envoie un fichier binaire (PDF, Image) lié à une conversation au backend
 * @param {File} file - Le fichier à uploader
 * @param {number} chatId - L'ID de la conversation associée
 * @returns {Promise<object|null>}
 */
async function uploadFileBackend(file, chatId) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("chat_id", chatId);

    try {
        const response = await fetch(`${API_URL}/api/fichiers`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            },
            body: formData
        });

        if (response.status === 401) {
            return { __unauthorized: true };
        }

        if (!response.ok) {
            const erreurData = await response.json().catch(() => ({}));
            throw new Error(erreurData.detail || `Erreur serveur (${response.status})`);
        }
        return await response.json();
    } catch (error) {
        console.error("Erreur API Upload :", error);
        alert(`❌ Échec de l'envoi du fichier "${file.name}" : ${error.message}`);
        return null;
    }
}