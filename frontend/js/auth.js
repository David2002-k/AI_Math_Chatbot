document.addEventListener("DOMContentLoaded", () => {
    // On récupère les formulaires s'ils sont présents sur la page actuelle
    const formConnexion = document.getElementById("form-connexion");
    const formInscription = document.getElementById("form-inscription");

    // --- 1. GESTION DE LA CONNEXION ---
    if (formConnexion) {
        formConnexion.addEventListener("submit", async (e) => {
            e.preventDefault();

            const email = document.getElementById("email").value.trim();
            const password = document.getElementById("password").value;
            const btnSubmit = formConnexion.querySelector("button[type='submit']");

            // État visuel de chargement
            btnSubmit.disabled = true;
            btnSubmit.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span> Connexion...`;

            try {
                // CORRECTION : Le backend attend un JSON {email, mot_de_passe} (ConnexionSchema), pas un formulaire OAuth2
                const response = await fetch(`${API_URL}/api/auth/connexion`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: email, mot_de_passe: password })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.detail || "Identifiants incorrects");
                }

                // Sauvegarder le token JWT et les infos utilisateur localement
                localStorage.setItem("token", data.access_token);
                if (data.utilisateur) {
                    localStorage.setItem("user", JSON.stringify(data.utilisateur));
                }

                // Redirection vers le tableau de bord / chat principal
                window.location.href = "../index.html";

            } catch (error) {
                alert(`❌ Erreur : ${error.message}`);
                btnSubmit.disabled = false;
                btnSubmit.innerText = "Se connecter";
            }
        });
    }

    // --- 2. GESTION DE L'INSCRIPTION ---
    if (formInscription) {
        formInscription.addEventListener("submit", async (e) => {
            e.preventDefault();

            const name = document.getElementById("nom").value.trim();
            const email = document.getElementById("email").value.trim();
            const password = document.getElementById("password").value;
            const passwordConfirm = document.getElementById("password-confirm").value;
            const btnSubmit = formInscription.querySelector("button[type='submit']");

            // Vérification basique des mots de passe
            if (password !== passwordConfirm) {
                alert("❌ Les mots de passe ne correspondent pas.");
                return;
            }

            btnSubmit.disabled = true;
            btnSubmit.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span> Création...`;

            try {
                // CORRECTION 3 : Alignement sur la bonne route du backend (/api/auth/inscription)
                const response = await fetch(`${API_URL}/api/auth/inscription`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ nom: name, email: email, mot_de_passe: password })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.detail || "Échec de l'inscription");
                }

                alert("✨ Compte créé avec succès ! Connectez-vous.");
                window.location.href = "connexion.html";

            } catch (error) {
                alert(`❌ Erreur : ${error.message}`);
                btnSubmit.disabled = false;
                btnSubmit.innerText = "S'inscrire";
            }
        });
    }
});

/**
 * Fonction globale utilitaire pour vérifier si l'utilisateur est connecté.
 * À appeler au tout début de tes pages privées (ex: index.html ou parametres.html).
 */
function checkAuthentication() {
    const token = localStorage.getItem("token");
    // Si pas de token et qu'on n'est pas déjà sur la page de connexion, on redirige
    if (!token && !window.location.href.includes("connexion.html") && !window.location.href.includes("inscription.html")) {
        window.location.href = "pages/connexion.html";
    }
}

/**
 * Déconnecte l'utilisateur et nettoie le stockage du navigateur
 */
function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "connexion.html";
}