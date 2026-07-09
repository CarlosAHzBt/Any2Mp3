"""
Servicio de transcripción — Audio a Texto con Google Gemini.
Responsabilidad: Subir audio a Google GenAI y retornar texto
en formato compatible con el resto de la app.
"""

import mimetypes
import os
import time
import traceback

from google import genai

import config


# Máximo de reintentos para uploads fallidos
_MAX_UPLOAD_RETRIES = 3
# Segundos entre reintentos (backoff lineal)
_RETRY_DELAY_SEC = 2
# Tiempo máximo de espera para que un archivo pase a ACTIVE (seg)
_FILE_ACTIVE_TIMEOUT = 120
# Intervalo de polling para estado del archivo (seg)
_FILE_POLL_INTERVAL = 2


class GoogleTranscriptionError(Exception):
    """Se lanza cuando la transcripción con Google falla."""
    pass


def _get_client() -> genai.Client:
    """Obtiene el cliente de Google GenAI con la API key configurada."""
    api_key = config.GEMINI_API_KEY
    if not api_key:
        raise GoogleTranscriptionError(
            "API key de Google no configurada. "
            "Agregá tu key en el archivo .env (GEMINI_API_KEY=...)"
        )
    return genai.Client(api_key=api_key)


def is_available() -> bool:
    """Retorna True si la API key de Google está configurada."""
    return bool(config.GEMINI_API_KEY)


def _guess_mime_type(audio_path: str) -> str:
    """Determina el MIME type del archivo de audio."""
    mime, _ = mimetypes.guess_type(audio_path)
    if mime:
        return mime
    # Fallback por extensión
    ext = os.path.splitext(audio_path)[1].lower()
    mime_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".opus": "audio/opus",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".wma": "audio/x-ms-wma",
        ".webm": "audio/webm",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
    }
    return mime_map.get(ext, "application/octet-stream")


def _upload_with_retry(client: genai.Client, audio_path: str) -> object:
    """
    Sube un archivo a Google GenAI con reintentos.
    Abre el archivo como stream binario para evitar errores de I/O
    del sistema operativo durante uploads largos.
    """
    mime_type = _guess_mime_type(audio_path)
    last_error = None

    for attempt in range(1, _MAX_UPLOAD_RETRIES + 1):
        try:
            print(f"📤  Upload intento {attempt}/{_MAX_UPLOAD_RETRIES}...")
            with open(audio_path, "rb") as f:
                uploaded = client.files.upload(
                    file=f,
                    config={"mime_type": mime_type},
                )
            print(f"📤  Upload exitoso (intento {attempt})")
            return uploaded
        except Exception as e:
            last_error = e
            print(f"⚠️  Upload intento {attempt} falló: {e}")
            if attempt < _MAX_UPLOAD_RETRIES:
                time.sleep(_RETRY_DELAY_SEC * attempt)

    raise GoogleTranscriptionError(
        f"No se pudo subir el archivo después de {_MAX_UPLOAD_RETRIES} intentos. "
        f"Último error: {last_error}"
    )


def _wait_for_active(client: genai.Client, uploaded_file) -> object:
    """
    Espera a que el archivo subido pase al estado ACTIVE.
    Algunos archivos grandes requieren procesamiento antes de usarse.
    """
    start = time.time()
    while time.time() - start < _FILE_ACTIVE_TIMEOUT:
        try:
            file_info = client.files.get(name=uploaded_file.name)
            state = getattr(file_info, "state", None)
            # Si no tiene state o ya está activo, salimos
            if state is None or str(state).upper() in ("ACTIVE", "STATE_UNSPECIFIED"):
                return file_info
            if str(state).upper() == "FAILED":
                raise GoogleTranscriptionError(
                    "Google reportó que el archivo falló al procesarse."
                )
            print(f"⏳  Archivo en estado '{state}', esperando...")
            time.sleep(_FILE_POLL_INTERVAL)
        except GoogleTranscriptionError:
            raise
        except Exception:
            # Si falla el polling, asumimos que el archivo está listo
            return uploaded_file

    raise GoogleTranscriptionError(
        f"Timeout: el archivo no pasó a estado ACTIVE en {_FILE_ACTIVE_TIMEOUT}s."
    )


def transcribe(audio_path: str, language: str | None = None) -> dict:
    """
    Transcribe un archivo de audio usando Google Gemini.

    Args:
        audio_path: Ruta al archivo de audio.
        language:   Código de idioma ISO-639-1 (ej: "es", "en"). None = auto-detectar.

    Returns:
        Dict compatible con el formato de la app:
        {text, language, segments, model, chunks_used, duration}

    Raises:
        GoogleTranscriptionError: Si la transcripción falla.
    """
    uploaded_file = None
    try:
        client = _get_client()

        file_size = os.path.getsize(audio_path)
        file_size_mb = file_size / (1024 * 1024)
        print(f"🟢  Google Gemini — Transcribiendo ({file_size_mb:.1f} MB)...")

        start_time = time.time()

        # Upload con reintentos y stream binario explícito
        uploaded_file = _upload_with_retry(client, audio_path)

        # Esperar a que el archivo esté listo para usar
        uploaded_file = _wait_for_active(client, uploaded_file)

        prompt = (
            "Transcribe este audio de forma literal. "
            "Devuelve solo la transcripción final, sin explicaciones extra."
            "Identifica quien es quién si hay varias personas hablando. "
            "hazlo lo mejor posible eres un experto Speech to text, no dejes nada sin transcribir, incluso si no entiendes algo ponlo como [inaudible] o similar. "
        )
        if language:
            prompt += f" El idioma esperado es: {language}."

        response = client.models.generate_content(
            model=config.GEMINI_STT_MODEL,
            contents=[prompt, uploaded_file],
        )

        elapsed = time.time() - start_time
        print(f"✅  Google Gemini completado en {elapsed:.1f}s")

        text = (response.text or "").strip()
        if not text:
            raise GoogleTranscriptionError(
                "Google devolvió una respuesta vacía. Probá con otro audio o modelo."
            )

        return {
            "text": text,
            "language": language or "auto",
            "segments": [],
            "model": config.GEMINI_STT_MODEL,
            "engine": "google",
            "chunks_used": 1,
            "duration": 0.0,
        }

    except GoogleTranscriptionError:
        raise
    except Exception as e:
        traceback.print_exc()
        raise GoogleTranscriptionError(
            f"Error en la transcripción con Google Gemini: {e}"
        ) from e
    finally:
        # Best-effort: limpiar archivo subido en Google File API
        if uploaded_file is not None:
            try:
                client = _get_client()
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass
