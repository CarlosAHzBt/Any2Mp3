/**
 * Any2Mp3 — Frontend Logic
 * Responsabilidad: Manejar interacción del usuario, drag & drop,
 * subida de archivos, descarga del resultado y transcripción de audio.
 */

document.addEventListener("DOMContentLoaded", () => {

    // ============================================================
    //  Widget de dispositivo (GPU / CPU)
    // ============================================================
    (async function loadDeviceInfo() {
        const badge = document.getElementById("device-badge");
        const text  = document.getElementById("device-text");
        try {
            const res  = await fetch("/api/device");
            const data = await res.json();

            badge.classList.remove("device-badge--loading");

            if (data.device === "gpu") {
                badge.classList.add("device-badge--gpu");
                text.textContent = `GPU: ${data.name} · ${data.vram_total_gb} GB VRAM · CUDA ${data.cuda_version}`;
            } else {
                badge.classList.add("device-badge--cpu");
                text.textContent = "CPU — Sin GPU detectada (transcripción más lenta)";
            }
        } catch {
            badge.classList.remove("device-badge--loading");
            badge.classList.add("device-badge--cpu");
            text.textContent = "No se pudo detectar el dispositivo";
        }
    })();

    // ============================================================
    //  Navegación por Tabs
    // ============================================================
    const tabs = document.querySelectorAll(".tab");
    const tabContents = document.querySelectorAll(".tab-content");

    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            const target = tab.dataset.tab;
            tabs.forEach(t => t.classList.remove("tab--active"));
            tabContents.forEach(tc => tc.classList.remove("tab-content--active"));
            tab.classList.add("tab--active");
            document.getElementById(`tab-${target}`).classList.add("tab-content--active");
        });
    });

    // ============================================================
    //  TAB 1: Convertidor de Video a MP3
    // ============================================================

    // --- Elementos del DOM ---
    const dropZone       = document.getElementById("drop-zone");
    const fileInput      = document.getElementById("file-input");
    const fileInfo       = document.getElementById("file-info");
    const fileName       = document.getElementById("file-name");
    const fileSize       = document.getElementById("file-size");
    const btnRemove      = document.getElementById("btn-remove");
    const btnConvert     = document.getElementById("btn-convert");
    const progressCont   = document.getElementById("progress-container");
    const progressBar    = document.getElementById("progress-bar");
    const progressText   = document.getElementById("progress-text");
    const resultDiv      = document.getElementById("result");
    const errorDiv       = document.getElementById("error");
    const errorText      = document.getElementById("error-text");
    const formatsSpan    = document.getElementById("supported-formats");

    let selectedFile = null;

    // --- Cargar formatos soportados ---
    async function loadFormats() {
        try {
            const res = await fetch("/api/formats");
            const data = await res.json();
            const exts = data.formats.map(f => `.${f}`).join(", ");
            formatsSpan.textContent = `Formatos soportados: ${exts}`;

            // Actualizar accept del input
            fileInput.accept = data.formats.map(f => `.${f}`).join(",");
        } catch {
            formatsSpan.textContent = "Formatos: .mp4, .mov";
        }
    }
    loadFormats();

    // --- Utilidades ---
    function formatSize(bytes) {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
        return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    }

    function resetUI() {
        fileInfo.classList.add("hidden");
        btnConvert.classList.add("hidden");
        progressCont.classList.add("hidden");
        resultDiv.classList.add("hidden");
        errorDiv.classList.add("hidden");
        dropZone.classList.remove("hidden");
        progressBar.style.width = "0%";
    }

    function showFile(file) {
        selectedFile = file;
        fileName.textContent = file.name;
        fileSize.textContent = formatSize(file.size);
        dropZone.classList.add("hidden");
        fileInfo.classList.remove("hidden");
        btnConvert.classList.remove("hidden");
        resultDiv.classList.add("hidden");
        errorDiv.classList.add("hidden");
    }

    function showError(msg) {
        errorText.textContent = msg;
        errorDiv.classList.remove("hidden");
        progressCont.classList.add("hidden");
        btnConvert.classList.remove("hidden");
        btnConvert.disabled = false;
    }

    // --- Drag & Drop ---
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("drop-zone--active");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("drop-zone--active");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("drop-zone--active");
        if (e.dataTransfer.files.length > 0) {
            showFile(e.dataTransfer.files[0]);
        }
    });

    // --- File input ---
    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            showFile(fileInput.files[0]);
        }
    });

    // --- Quitar archivo ---
    btnRemove.addEventListener("click", () => {
        selectedFile = null;
        fileInput.value = "";
        resetUI();
    });

    // --- Convertir ---
    btnConvert.addEventListener("click", async () => {
        if (!selectedFile) return;

        btnConvert.disabled = true;
        resultDiv.classList.add("hidden");
        errorDiv.classList.add("hidden");
        progressCont.classList.remove("hidden");
        progressBar.style.width = "0%";
        progressText.textContent = "Subiendo archivo...";

        const formData = new FormData();
        formData.append("file", selectedFile);

        try {
            const xhr = new XMLHttpRequest();

            // Progreso de subida
            xhr.upload.addEventListener("progress", (e) => {
                if (e.lengthComputable) {
                    const pct = Math.round((e.loaded / e.total) * 70); // 0-70% subida
                    progressBar.style.width = `${pct}%`;
                    if (pct >= 70) {
                        progressText.textContent = "Convirtiendo audio...";
                    }
                }
            });

            // Respuesta
            xhr.addEventListener("load", () => {
                progressBar.style.width = "100%";

                if (xhr.status === 200) {
                    // Descargar el MP3
                    const blob = xhr.response;
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    const mp3Name = selectedFile.name.replace(/\.[^.]+$/, ".mp3");
                    a.href = url;
                    a.download = mp3Name;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    URL.revokeObjectURL(url);

                    progressCont.classList.add("hidden");
                    resultDiv.classList.remove("hidden");
                    btnConvert.disabled = false;
                } else {
                    // Parsear error — puede ser JSON o HTML
                    const blob = xhr.response;
                    if (blob && blob.size > 0) {
                        const reader = new FileReader();
                        reader.onload = () => {
                            try {
                                const data = JSON.parse(reader.result);
                                showError(data.error || `Error del servidor (${xhr.status}).`);
                            } catch {
                                showError(`Error del servidor (${xhr.status}).`);
                            }
                        };
                        reader.onerror = () => {
                            showError(`Error del servidor (${xhr.status}).`);
                        };
                        reader.readAsText(blob);
                    } else {
                        showError(`Error del servidor (${xhr.status}).`);
                    }
                }
            });

            xhr.addEventListener("error", () => {
                showError("Error de red. Verificá tu conexión.");
            });

            xhr.addEventListener("timeout", () => {
                showError("La conversión tardó demasiado. Intentá con un archivo más chico.");
            });

            xhr.timeout = 600000; // 10 minutos

            xhr.open("POST", "/api/convert");
            xhr.responseType = "blob";
            xhr.send(formData);

        } catch (err) {
            showError(`Error: ${err.message}`);
        }
    });

    // ============================================================
    //  TAB 2: Transcripción de Audio a Texto (Whisper)
    // ============================================================

    const tDropZone      = document.getElementById("t-drop-zone");
    const tFileInput     = document.getElementById("t-file-input");
    const tFileInfo      = document.getElementById("t-file-info");
    const tFileName      = document.getElementById("t-file-name");
    const tFileSize      = document.getElementById("t-file-size");
    const tBtnRemove     = document.getElementById("t-btn-remove");
    const tOptions       = document.getElementById("t-options");
    const tModel         = document.getElementById("t-model");
    const tModelHint     = document.getElementById("t-model-hint");
    const tLanguage      = document.getElementById("t-language");
    const tBtnTranscribe = document.getElementById("t-btn-transcribe");
    const tProgressCont  = document.getElementById("t-progress-container");
    const tProgressBar   = document.getElementById("t-progress-bar");
    const tProgressText  = document.getElementById("t-progress-text");
    const tResultDiv     = document.getElementById("t-result");
    const tResultText    = document.getElementById("t-result-text");
    const tDetectedLang  = document.getElementById("t-detected-lang");
    const tBtnCopy       = document.getElementById("t-btn-copy");
    const tBtnDownload   = document.getElementById("t-btn-download");
    const tBtnTimestamps = document.getElementById("t-btn-timestamps");
    const tSegmentsDiv   = document.getElementById("t-segments");
    const tErrorDiv      = document.getElementById("t-error");
    const tErrorText     = document.getElementById("t-error-text");
    const tFormatsSpan   = document.getElementById("t-supported-formats");
    const tWhisperOpts   = document.getElementById("t-whisper-options");
    const tElevenOpts    = document.getElementById("t-elevenlabs-options");
    const tDiarize       = document.getElementById("t-diarize");
    const engineButtons  = document.querySelectorAll(".engine-btn");

    let tSelectedFile = null;
    let tTranscriptionData = null;
    let tCurrentEngine = "whisper";

    // --- Engine selector ---
    engineButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            if (btn.classList.contains("engine-btn--disabled")) return;

            const engine = btn.dataset.engine;
            tCurrentEngine = engine;
            engineButtons.forEach(b => b.classList.remove("engine-btn--active"));
            btn.classList.add("engine-btn--active");

            if (engine === "elevenlabs") {
                tWhisperOpts.classList.add("hidden");
                tElevenOpts.classList.remove("hidden");
                tModelHint.textContent = "💡 Scribe v2: transcripción cloud ultra rápida. Requiere API key de ElevenLabs.";
            } else if (engine === "google") {
                tWhisperOpts.classList.add("hidden");
                tElevenOpts.classList.add("hidden");
                tModelHint.textContent = "💡 Gemini: transcripción cloud multimodal. Requiere API key de Google.";
            } else {
                tWhisperOpts.classList.remove("hidden");
                tElevenOpts.classList.add("hidden");
                tModelHint.textContent = modelHints[tModel.value] || "";
            }
        });
    });

    // Cargar estado de engines disponibles
    (async function loadEngines() {
        try {
            const res = await fetch("/api/transcription/engines");
            const data = await res.json();
            data.engines.forEach(engine => {
                const btn = document.querySelector(`.engine-btn[data-engine="${engine.id}"]`);
                if (!btn) return;
                if (!engine.available) {
                    btn.classList.add("engine-btn--disabled");
                    if (engine.id === "elevenlabs") {
                        btn.title = "API key no configurada. Agregá ELEVENLABS_API_KEY en .env";
                    }
                    if (engine.id === "google") {
                        btn.title = "API key no configurada. Agregá GEMINI_API_KEY en .env";
                    }
                }
            });
        } catch { /* ignore */ }
    })();

    // Hints por modelo
    const modelHints = {
        tiny:   "💡 Muy rápido (~10x), calidad básica. Ideal para pruebas.",
        base:   "💡 Rápido (~7x) con buena calidad. Recomendado para CPU.",
        small:  "💡 Mejor calidad (~4x), tarda un poco más. ~2 GB RAM.",
        medium: "💡 Alta calidad (~2x), puede tardar bastante en CPU. ~5 GB RAM.",
        turbo:  "💡 Máxima calidad (SOTA). Recomendado con GPU. ~6 GB RAM.",
    };

    tModel.addEventListener("change", () => {
        tModelHint.textContent = modelHints[tModel.value] || "";
    });

    // Mapa de códigos de idioma a nombres
    const langNames = {
        es: "Español", en: "Inglés", fr: "Francés", de: "Alemán",
        pt: "Portugués", it: "Italiano", ja: "Japonés", ko: "Coreano",
        zh: "Chino", ru: "Ruso", ar: "Árabe", hi: "Hindi",
        nl: "Neerlandés", pl: "Polaco", sv: "Sueco", tr: "Turco",
        uk: "Ucraniano", vi: "Vietnamita", th: "Tailandés", cs: "Checo",
    };

    // --- Cargar formatos de transcripción ---
    async function loadTranscriptionFormats() {
        try {
            const res = await fetch("/api/transcription/formats");
            const data = await res.json();
            const exts = data.formats.map(f => `.${f}`).join(", ");
            tFormatsSpan.textContent = `Formatos soportados: ${exts}`;
            tFileInput.accept = data.formats.map(f => `.${f}`).join(",");
        } catch {
            tFormatsSpan.textContent = "Formatos: .mp3, .wav, .flac, .ogg, .m4a";
        }
    }
    loadTranscriptionFormats();

    // --- Utilidades de transcripción ---
    function tResetUI() {
        tFileInfo.classList.add("hidden");
        tOptions.classList.add("hidden");
        tBtnTranscribe.classList.add("hidden");
        tProgressCont.classList.add("hidden");
        tResultDiv.classList.add("hidden");
        tErrorDiv.classList.add("hidden");
        tSegmentsDiv.classList.add("hidden");
        tDropZone.classList.remove("hidden");
        tProgressBar.style.width = "0%";
    }

    function tShowFile(file) {
        tSelectedFile = file;
        tFileName.textContent = file.name;
        tFileSize.textContent = formatSize(file.size);
        tDropZone.classList.add("hidden");
        tFileInfo.classList.remove("hidden");
        tOptions.classList.remove("hidden");
        tBtnTranscribe.classList.remove("hidden");
        tResultDiv.classList.add("hidden");
        tErrorDiv.classList.add("hidden");
    }

    function tShowError(msg) {
        tErrorText.textContent = msg;
        tErrorDiv.classList.remove("hidden");
        tProgressCont.classList.add("hidden");
        tBtnTranscribe.classList.remove("hidden");
        tBtnTranscribe.disabled = false;
    }

    function formatTimestamp(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        const ms = Math.round((seconds % 1) * 100);
        if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${String(ms).padStart(2, "0")}`;
        return `${m}:${String(s).padStart(2, "0")}.${String(ms).padStart(2, "0")}`;
    }

    // --- Drag & Drop (transcripción) ---
    tDropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        tDropZone.classList.add("drop-zone--active");
    });

    tDropZone.addEventListener("dragleave", () => {
        tDropZone.classList.remove("drop-zone--active");
    });

    tDropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        tDropZone.classList.remove("drop-zone--active");
        if (e.dataTransfer.files.length > 0) {
            tShowFile(e.dataTransfer.files[0]);
        }
    });

    tFileInput.addEventListener("change", () => {
        if (tFileInput.files.length > 0) {
            tShowFile(tFileInput.files[0]);
        }
    });

    tBtnRemove.addEventListener("click", () => {
        tSelectedFile = null;
        tTranscriptionData = null;
        tFileInput.value = "";
        tResetUI();
    });

    // --- Transcribir ---
    tBtnTranscribe.addEventListener("click", async () => {
        if (!tSelectedFile) return;

        tBtnTranscribe.disabled = true;
        tResultDiv.classList.add("hidden");
        tErrorDiv.classList.add("hidden");
        tProgressCont.classList.remove("hidden");
        tProgressBar.style.width = "0%";
        tProgressText.textContent = "Subiendo archivo...";

        const formData = new FormData();
        formData.append("file", tSelectedFile);
        formData.append("engine", tCurrentEngine);
        if (tCurrentEngine === "whisper") {
            formData.append("model", tModel.value);
        }
        if (tCurrentEngine === "elevenlabs" && tDiarize.checked) {
            formData.append("diarize", "true");
        }
        if (tLanguage.value) {
            formData.append("language", tLanguage.value);
        }

        try {
            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener("progress", (e) => {
                if (e.lengthComputable) {
                    const pct = Math.round((e.loaded / e.total) * 40);
                    tProgressBar.style.width = `${pct}%`;
                    if (pct >= 40) {
                        const engineLabel = tCurrentEngine === "elevenlabs"
                            ? "🔷 Scribe v2"
                            : tCurrentEngine === "google"
                                ? "🟢 Gemini"
                                : tModel.options[tModel.selectedIndex].text;
                        tProgressText.textContent = `🧠 Transcribiendo con ${engineLabel}...`;
                        // Animar la barra lentamente mientras espera
                        let fakePct = 40;
                        const msgs = tCurrentEngine === "elevenlabs"
                            ? [
                                `🔷 Enviando audio a ElevenLabs...`,
                                `🔷 Scribe v2 procesando...`,
                                `🔷 Generando transcripción...`,
                                `⏳ Casi listo...`,
                                `✅ Finalizando respuesta...`,
                            ]
                            : tCurrentEngine === "google"
                                ? [
                                    `🟢 Subiendo audio a Google...`,
                                    `🟢 Gemini procesando audio...`,
                                    `🟢 Generando transcripción...`,
                                    `⏳ Casi listo...`,
                                    `✅ Finalizando respuesta...`,
                                ]
                                : [
                                    `🧠 Transcribiendo con ${engineLabel}...`,
                                    `🔪 Dividiendo audio en partes...`,
                                    `📝 Procesando chunks de audio...`,
                                    `🧩 Mergeando transcripciones...`,
                                    `⏳ Casi listo, finalizando...`,
                                ];
                        let msgIdx = 0;
                        const interval = setInterval(() => {
                            fakePct += 0.3;
                            if (fakePct >= 95) clearInterval(interval);
                            tProgressBar.style.width = `${fakePct}%`;
                            if (fakePct > 50 && msgIdx < msgs.length - 1) msgIdx = Math.min(1, msgs.length - 1);
                            if (fakePct > 65) msgIdx = Math.min(2, msgs.length - 1);
                            if (fakePct > 80) msgIdx = Math.min(3, msgs.length - 1);
                            if (fakePct > 90) msgIdx = Math.min(4, msgs.length - 1);
                            tProgressText.textContent = msgs[msgIdx];
                        }, 2000);
                        xhr._fakeInterval = interval;
                    }
                }
            });

            xhr.addEventListener("load", () => {
                if (xhr._fakeInterval) clearInterval(xhr._fakeInterval);
                tProgressBar.style.width = "100%";

                if (xhr.status === 200) {
                    try {
                        const data = JSON.parse(xhr.responseText);
                        tTranscriptionData = data;

                        // Mostrar texto
                        tResultText.textContent = data.text;

                        // Idioma detectado + info de chunks
                        const langCode = data.language;
                        const langLabel = langNames[langCode] || langCode;
                        let infoText = `Idioma: ${langLabel}`;
                        if (data.duration) {
                            const mins = Math.floor(data.duration / 60);
                            const secs = Math.round(data.duration % 60);
                            infoText += ` · ${mins}m${secs}s`;
                        }
                        if (data.chunks_used > 1) {
                            infoText += ` · ${data.chunks_used} chunks`;
                        }
                        tDetectedLang.textContent = infoText;

                        // Generar segmentos con timestamps
                        tSegmentsDiv.innerHTML = "";
                        if (data.segments && data.segments.length > 0) {
                            data.segments.forEach(seg => {
                                const div = document.createElement("div");
                                div.className = "segment";
                                div.innerHTML = `<span class="segment__time">[${formatTimestamp(seg.start)} → ${formatTimestamp(seg.end)}]</span> <span class="segment__text">${seg.text}</span>`;
                                tSegmentsDiv.appendChild(div);
                            });
                        }

                        tProgressCont.classList.add("hidden");
                        tResultDiv.classList.remove("hidden");
                        tBtnTranscribe.disabled = false;
                    } catch {
                        tShowError("Error al procesar la respuesta del servidor.");
                    }
                } else {
                    try {
                        const data = JSON.parse(xhr.responseText);
                        tShowError(data.error || `Error del servidor (${xhr.status}).`);
                    } catch {
                        tShowError(`Error del servidor (${xhr.status}).`);
                    }
                }
            });

            xhr.addEventListener("error", () => {
                if (xhr._fakeInterval) clearInterval(xhr._fakeInterval);
                tShowError("Error de red. Verificá tu conexión.");
            });

            xhr.addEventListener("timeout", () => {
                if (xhr._fakeInterval) clearInterval(xhr._fakeInterval);
                tShowError("La transcripción tardó demasiado. Intentá con un archivo más corto.");
            });

            xhr.timeout = 1800000; // 30 minutos

            xhr.open("POST", "/api/transcribe");
            xhr.send(formData);

        } catch (err) {
            tShowError(`Error: ${err.message}`);
        }
    });

    // --- Copiar texto ---
    tBtnCopy.addEventListener("click", async () => {
        if (!tTranscriptionData) return;
        try {
            await navigator.clipboard.writeText(tTranscriptionData.text);
            tBtnCopy.textContent = "✅ Copiado!";
            setTimeout(() => { tBtnCopy.textContent = "📋 Copiar"; }, 2000);
        } catch {
            // Fallback
            const ta = document.createElement("textarea");
            ta.value = tTranscriptionData.text;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand("copy");
            ta.remove();
            tBtnCopy.textContent = "✅ Copiado!";
            setTimeout(() => { tBtnCopy.textContent = "📋 Copiar"; }, 2000);
        }
    });

    // --- Descargar como .txt ---
    tBtnDownload.addEventListener("click", () => {
        if (!tTranscriptionData) return;

        let content = tTranscriptionData.text + "\n";

        // Agregar timestamps si hay segmentos
        if (tTranscriptionData.segments && tTranscriptionData.segments.length > 0) {
            content += "\n\n--- Transcripción con Timestamps ---\n\n";
            tTranscriptionData.segments.forEach(seg => {
                content += `[${formatTimestamp(seg.start)} → ${formatTimestamp(seg.end)}] ${seg.text}\n`;
            });
        }

        const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        const baseName = tSelectedFile ? tSelectedFile.name.replace(/\.[^.]+$/, "") : "transcripcion";
        a.href = url;
        a.download = `${baseName}_transcripcion.txt`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    });

    // --- Toggle timestamps ---
    tBtnTimestamps.addEventListener("click", () => {
        tSegmentsDiv.classList.toggle("hidden");
        tBtnTimestamps.textContent = tSegmentsDiv.classList.contains("hidden")
            ? "⏱️ Timestamps"
            : "⏱️ Ocultar Timestamps";
    });
});
