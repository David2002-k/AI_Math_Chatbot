/**
 * js/theme.js
 * ──────────────────────────────────────────────────────────────────
 * Gère le basculement dynamique du thème (Sombre / Clair) et
 * mémorise le choix de l'utilisateur.
 * ──────────────────────────────────────────────────────────────────
 */

document.addEventListener("DOMContentLoaded", () => {
    const btnTheme = document.getElementById("btn-toggle-theme");
    const htmlTag = document.documentElement;

    // 1. Charger le thème sauvegardé ou appliquer "sombre" par défaut
    const savedTheme = localStorage.getItem("theme") || "sombre";
    htmlTag.setAttribute("data-theme", savedTheme);
    updateThemeIcon(savedTheme);

    // 2. Écouteur d'événement sur le bouton de bascule
    if (btnTheme) {
        btnTheme.addEventListener("click", () => {
            const currentTheme = htmlTag.getAttribute("data-theme");
            const newTheme = currentTheme === "sombre" ? "clair" : "sombre";
            
            htmlTag.setAttribute("data-theme", newTheme);
            localStorage.setItem("theme", newTheme);
            updateThemeIcon(newTheme);
        });
    }

    // 3. Mise à jour de l'icône et correction du contraste d'accessibilité
    function updateThemeIcon(theme) {
        if (!btnTheme) return;
        
        const icon = btnTheme.querySelector("i");
        if (!icon) return; // Sécurité si la balise <i> n'est pas encore prête

        if (theme === "sombre") {
            icon.className = "bi bi-sun"; // Icône soleil pour passer au clair
            document.body.style.color = "#f8f9fa"; // Sécurité contraste sombre
        } else {
            icon.className = "bi bi-moon-stars"; // Icône lune pour passer au sombre
            document.body.style.color = "#212529"; // Sécurité contraste clair
        }
    }
});