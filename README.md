# 🎵 Any2Mp3

Convierte prácticamente **cualquier archivo de video/audio a MP3** y **transcribe audio a texto** usando [OpenAI Whisper](https://github.com/openai/whisper), desde una app de escritorio.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey?logo=flask)
![Whisper](https://img.shields.io/badge/Whisper-SOTA-green?logo=openai)
![License](https://img.shields.io/badge/License-MIT-yellow)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

---

## ✨ Features

| Feature | Descripción |
|---------|-------------|
| 🔄 **Conversión a MP3** | Soporta MP4, MOV y más formatos de video/audio |
| 🎙️ **Transcripción de audio** | Speech-to-text con OpenAI Whisper (99 idiomas) |
| ☁️ **APIs de transcripción** | ElevenLabs Scribe v2 y Google Gemini (vía API key) |
| 🧠 **Múltiples modelos** | Tiny, Base, Small, Medium y Turbo (SOTA) |
| ✂️ **Chunked transcription** | Divide audio largo en partes, transcribe y une inteligentemente |
| 🌐 **Auto-detección de idioma** | O selecciona manualmente entre 12+ idiomas |
| 📋 **Timestamps** | Segmentos con marcas de tiempo exportables |
| 🖥️ **UI moderna** | Dark theme, drag & drop, tabs |

## 🚀 Guía paso a paso para ejecución

Sigue estos pasos para poner en marcha el proyecto en tu máquina local:

### 1. Prerrequisitos
Asegúrate de tener instalado **Python 3.10+** y **FFmpeg**.

```bash
# Instalar FFmpeg en macOS
brew install ffmpeg

# Instalar FFmpeg en Ubuntu / Debian
sudo apt update && sudo apt install ffmpeg
```

### 2. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/Any2Mp3.git
cd Any2Mp3
```

### 3. Configurar el entorno virtual
Es recomendable usar un entorno virtual para gestionar las dependencias:

```bash
# Crear el entorno
python -m venv .venv

# Activar el entorno
# En macOS/Linux:
source .venv/bin/activate
# En Windows:
.venv\Scripts\activate
```

### 4. Instalar dependencias
Con el entorno virtual activo, instala los paquetes necesarios:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configurar variables de entorno
Crea un archivo `.env` en la raíz del proyecto y añade tus claves de API (puedes basarte en el archivo `.env.example` si existe o crearlo desde cero):

```env
ELEVENLABS_API_KEY=tu_clave_aqui
GEMINI_API_KEY=tu_clave_aqui
GEMINI_STT_MODEL=gemini-3-flash-preview
```

### 6. Ejecutar la aplicación

En macOS, abre `Any2Mp3.app` desde Finder. También puedes arrancar la misma ventana desde terminal:

```bash
python desktop.py
```

La app abre su propia ventana; no necesitas iniciar un servidor ni abrir el navegador. Al cerrar la ventana termina también el proceso interno.

¡Listo! Ya puedes empezar a convertir y transcribir. 🎉


## 📁 Estructura del proyecto

```
Any2Mp3/
├── app.py                  # Entry point (Flask)
├── config.py               # Configuración central
├── requirements.txt
├── converters/             # Módulos de conversión (registry pattern)
│   ├── base.py
│   ├── mp4_converter.py
│   └── mov_converter.py
├── services/
│   ├── conversion_service.py
│   ├── file_service.py
│   └── transcription_service.py
├── routes/
│   └── api.py              # Endpoints REST
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    └── js/app.js
```

## 🎙️ Modelos de Whisper

| Modelo | Params | RAM aprox. | Velocidad | Precisión |
|--------|--------|-----------|-----------|-----------|
| `tiny` | 39M | ~1 GB | ⚡⚡⚡ | ★★☆☆☆ |
| `base` | 74M | ~1 GB | ⚡⚡ | ★★★☆☆ |
| `small` | 244M | ~2 GB | ⚡ | ★★★★☆ |
| `medium` | 769M | ~5 GB | 🐢 | ★★★★☆ |
| `turbo` | 809M | ~6 GB | 🐢🐢 | ★★★★★ |

> **Tip:** En CPU, `base` ofrece el mejor balance velocidad/calidad. Si tienes GPU con CUDA, prueba `turbo` para resultados SOTA.

## 🔑 Variables de entorno (APIs cloud)

Configurá las claves en tu archivo `.env`:

- `ELEVENLABS_API_KEY=...`
- `GEMINI_API_KEY=...`
- `GEMINI_STT_MODEL=gemini-3-flash-preview` (opcional)

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Aquí hay algunas ideas:

- 🆕 Agregar más formatos de conversión (AVI, MKV, FLAC…)
- 🌍 Soporte de más idiomas en la UI
- 🖥️ Soporte GPU / CUDA automático
- 📦 Dockerizar la aplicación
- 🔊 Agregar opciones de calidad de audio (bitrate, sample rate)
- 🧪 Tests unitarios y de integración

### ¿Cómo contribuir?

1. Haz **fork** del proyecto
2. Crea tu rama (`git checkout -b feature/mi-feature`)
3. Haz commit de tus cambios (`git commit -m 'feat: nueva funcionalidad'`)
4. Push a tu rama (`git push origin feature/mi-feature`)
5. Abre un **Pull Request**

## 📄 Licencia

Este proyecto está bajo la licencia [MIT](LICENSE). Úsalo, modifícalo, compártelo.

---

<p align="center">
  Hecho con ☕ y 🎶 · <b>Any2Mp3</b>
</p>
