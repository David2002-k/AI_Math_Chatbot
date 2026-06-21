let mediaRecorder;
let audioChunks = [];
let isRecording = false;

document.addEventListener("DOMContentLoaded", () => {
    const btnMicro = document.getElementById("btn-micro");
    const inputMessage = document.getElementById("input-message");

    if (!btnMicro) return;

    // Option recommandée : Utiliser la reconnaissance vocale native du navigateur (Web Speech API)
    // Cela évite de surcharger ton serveur FastAPI avec des fichiers audio lourds.
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.lang = 'fr-FR';
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            isRecording = true;
            btnMicro.className = "btn btn-link text-danger fw-bold p-2 shadow-none";
            btnMicro.innerHTML = '<i class="bi bi-mic-fill fs-5 animate-pulse"></i>';
        };

        recognition.onerror = (event) => {
            console.error("Erreur de reconnaissance vocale :", event.error);
            isRecording = false;
            btnMicro.className = "btn btn-link text-secondary p-2 shadow-none";
            btnMicro.innerHTML = '<i class="bi bi-mic fs-5"></i>';
        };

        recognition.onend = () => {
            isRecording = false;
            btnMicro.className = "btn btn-link text-secondary p-2 shadow-none";
            btnMicro.innerHTML = '<i class="bi bi-mic fs-5"></i>';
        };

        recognition.onresult = (event) => {
            const texteTranscrit = event.results[0][0].transcript;
            if (inputMessage) {
                inputMessage.value += texteTranscrit;
                inputMessage.focus();
                // Ajuste la hauteur du textarea si nécessaire
                inputMessage.dispatchEvent(new Event('input'));
            }
        };

        btnMicro.addEventListener("click", () => {
            if (!isRecording) {
                recognition.start();
            } else {
                recognition.stop();
            }
        });

    } else {
        // En cas de secours (Fallback) : Ta méthode par envoi de fichier audio au backend
        btnMicro.addEventListener("click", async () => {
            if (!isRecording) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];

                    mediaRecorder.ondataavailable = (event) => {
                        audioChunks.push(event.data);
                    };

                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        btnMicro.innerHTML = '<i class="bi bi-hourglass-split fs-5"></i>';
                        
                        const formData = new FormData();
                        formData.append("file", audioBlob, "audio.wav");

                        try {
                            // CORRECTION : Ajout du token de sécurité JWT au cas où le backend l'exige
                            const response = await fetch(`${API_URL}/api/transcribe`, {
                                method: "POST",
                                headers: {
                                    "Authorization": `Bearer ${localStorage.getItem("token")}`
                                },
                                body: formData
                            });
                            const data = await response.json();
                            if (data.text) {
                                inputMessage.value = data.text;
                                inputMessage.focus();
                            }
                        } catch (err) {
                            console.error("Erreur transcription backend :", err);
                        }
                        
                        btnMicro.innerHTML = '<i class="bi bi-mic fs-5"></i>';
                    };

                    mediaRecorder.start();
                    isRecording = true;
                    btnMicro.className = "btn btn-link text-danger fw-bold p-2 shadow-none";
                } catch (err) {
                    alert("Veuillez autoriser l'accès au micro.");
                }
            } else {
                mediaRecorder.stop();
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                isRecording = false;
                btnMicro.className = "btn btn-link text-secondary p-2 shadow-none";
            }
        });
    }
});