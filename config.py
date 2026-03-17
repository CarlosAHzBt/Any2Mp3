"""
Configuración central de la aplicación Any2Mp3.
Responsabilidad: Almacenar constantes y parámetros de configuración.
"""

import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Carpetas de trabajo
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")

# Tamaño máximo de archivo (10 GB)
MAX_CONTENT_LENGTH = 10 * 1024 * 1024 * 1024

# Configuración de audio de salida por defecto
DEFAULT_AUDIO_BITRATE = "192k"
DEFAULT_AUDIO_SAMPLE_RATE = 44100

# Tiempo máximo de conversión en segundos
CONVERSION_TIMEOUT = 600

# ---- Transcripción (Whisper) ----
# Modelo Whisper por defecto: "base" es rápido en CPU.
# Opciones: tiny, base, small, medium, large, turbo
WHISPER_MODEL = "base"

# Modelos disponibles con info para el frontend
WHISPER_MODELS = {
    "tiny":   {"label": "⚡ Ultra rápido",  "desc": "39M params · ~1 GB RAM",  "size": "tiny"},
    "base":   {"label": "🚀 Rápido",       "desc": "74M params · ~1 GB RAM",  "size": "base"},
    "small":  {"label": "⚖️ Balanceado",   "desc": "244M params · ~2 GB RAM", "size": "small"},
    "medium": {"label": "🎯 Preciso",      "desc": "769M params · ~5 GB RAM", "size": "medium"},
    "turbo":  {"label": "🧠 SOTA",         "desc": "809M params · ~6 GB RAM", "size": "turbo"},
}

# Idioma por defecto (None = auto-detectar)
WHISPER_LANGUAGE = None

# ---- Chunked Transcription ----
# Duración máxima de cada chunk en segundos (5 min)
CHUNK_DURATION_SEC = 300
# Overlap entre chunks en segundos (15 seg para merge inteligente)
CHUNK_OVERLAP_SEC = 15
# Umbral mínimo de duración para activar chunking (2 min)
CHUNK_MIN_DURATION_SEC = 120

# Formatos de audio soportados para transcripción
TRANSCRIPTION_AUDIO_EXTENSIONS = {"mp3", "wav", "flac", "ogg", "m4a", "wma", "aac", "opus", "webm", "mp4", "mov"}

# ---- ElevenLabs (Scribe v2) ----
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# ---- Google Gemini (STT) ----
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_STT_MODEL = os.environ.get("GEMINI_STT_MODEL", "gemini-3-flash-preview")

# Crear carpetas si no existen
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
