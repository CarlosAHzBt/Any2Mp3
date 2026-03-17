"""
Servicio de transcripción — Audio a Texto con Google Gemini.
Responsabilidad: Subir audio a Google GenAI y retornar texto
en formato compatible con el resto de la app.
"""

import os
import time

from google import genai

import config


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
        uploaded_file = client.files.upload(file=audio_path)

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
