"""
Servicio de transcripción — Audio a Texto con ElevenLabs Scribe v2.
Responsabilidad: Enviar archivos de audio a la API de ElevenLabs
y retornar la transcripción en formato compatible con el resto de la app.

Modelo: Scribe v2 (SOTA)
- 99 idiomas · Auto-detección · Timestamps word-level
- Diarización de speakers · Archivos hasta 3 GB
- Requiere API key de ElevenLabs
"""

import os
import time

from elevenlabs.client import ElevenLabs

import config


class ScribeTranscriptionError(Exception):
    """Se lanza cuando la transcripción con Scribe falla."""
    pass


def _get_client() -> ElevenLabs:
    """Obtiene el cliente de ElevenLabs con la API key configurada."""
    api_key = config.ELEVENLABS_API_KEY
    if not api_key or api_key == "tu_api_key_aqui":
        raise ScribeTranscriptionError(
            "API key de ElevenLabs no configurada. "
            "Agregá tu key en el archivo .env (ELEVENLABS_API_KEY=...)"
        )
    return ElevenLabs(api_key=api_key)


def is_available() -> bool:
    """Retorna True si la API key de ElevenLabs está configurada."""
    key = config.ELEVENLABS_API_KEY
    return bool(key and key != "tu_api_key_aqui")


def transcribe(
    audio_path: str,
    language: str | None = None,
    diarize: bool = False,
) -> dict:
    """
    Transcribe un archivo de audio usando ElevenLabs Scribe v2.

    Args:
        audio_path: Ruta al archivo de audio.
        language:   Código de idioma ISO-639-1 (ej: "es", "en"). None = auto-detectar.
        diarize:    Si True, identifica quién habla en cada segmento.

    Returns:
        Dict compatible con el formato de la app:
        {text, language, segments, model, chunks_used, duration}

    Raises:
        ScribeTranscriptionError: Si la transcripción falla.
    """
    try:
        client = _get_client()

        file_size = os.path.getsize(audio_path)
        file_size_mb = file_size / (1024 * 1024)
        print(f"🔷  ElevenLabs Scribe v2 — Transcribiendo ({file_size_mb:.1f} MB)...")

        start_time = time.time()

        # Preparar parámetros
        kwargs = {
            "model_id": "scribe_v2",
            "timestamps_granularity": "word",
            "tag_audio_events": True,
            "diarize": diarize,
            "temperature": 0.0,
        }

        if language:
            kwargs["language_code"] = language

        # Enviar archivo a la API
        with open(audio_path, "rb") as audio_file:
            result = client.speech_to_text.convert(
                file=audio_file,
                **kwargs,
            )

        elapsed = time.time() - start_time
        print(f"✅  Scribe v2 completado en {elapsed:.1f}s")

        # Usar timestamps tal cual los entrega la API (sin merge local)
        segments = _api_words_to_segments(result.words if result.words else [])

        # Calcular duración del audio a partir de los timestamps
        duration = 0.0
        if result.words:
            last_word = result.words[-1]
            if hasattr(last_word, "end") and last_word.end is not None:
                duration = last_word.end

        # Idioma detectado
        detected_lang = "unknown"
        if hasattr(result, "language_code") and result.language_code:
            detected_lang = result.language_code

        return {
            "text": result.text.strip() if result.text else "",
            "language": detected_lang,
            "segments": segments,
            "model": "scribe_v2",
            "engine": "elevenlabs",
            "chunks_used": 1,
            "duration": round(duration, 1),
        }

    except ScribeTranscriptionError:
        raise
    except Exception as e:
        raise ScribeTranscriptionError(
            f"Error en la transcripción con ElevenLabs Scribe v2: {e}"
        ) from e


def _api_words_to_segments(words: list) -> list[dict]:
    """
    Convierte las words de ElevenLabs en segmentos 1:1,
    sin reordenar ni reagrupar texto localmente.
    """
    if not words:
        return []

    segments = []
    for word in words:
        text = (word.text if hasattr(word, "text") else str(word)).strip()
        if not text:
            continue

        start = word.start if hasattr(word, "start") and word.start is not None else 0.0
        end = word.end if hasattr(word, "end") and word.end is not None else start

        segments.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "text": text,
        })

    return segments
