"""
Servicio de transcripción — Audio a Texto con Whisper.
Responsabilidad: Cargar el modelo Whisper y transcribir archivos de audio.
Para audios largos, divide en chunks con overlap y mergea inteligentemente.

Modelos disponibles (OpenAI Whisper):
- tiny  (39M)  — Ultra rápido, menor calidad
- base  (74M)  — Buen balance para CPU
- small (244M) — Mejor calidad, más lento
- medium(769M) — Alta calidad, requiere buena RAM
- turbo (809M) — SOTA (large-v3-turbo), GPU recomendada

Soporta 99 idiomas con auto-detección · Licencia MIT
"""

import os
import tempfile
from difflib import SequenceMatcher

import torch
import whisper
from pydub import AudioSegment

import config

# Detectar dispositivo óptimo (GPU si hay CUDA, si no CPU)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🖥️  Whisper usará: {DEVICE.upper()}"
      + (f" ({torch.cuda.get_device_name(0)})" if DEVICE == "cuda" else ""))

# Cache del modelo cargado
_loaded_model_name: str | None = None
_loaded_model = None


class TranscriptionError(Exception):
    """Se lanza cuando la transcripción falla."""
    pass


# ============================================================
#  Carga de modelo (lazy, con swap dinámico)
# ============================================================

def _get_model(model_name: str | None = None):
    """
    Carga (lazy) el modelo Whisper y lo cachea.
    Si se pide un modelo distinto al cacheado, lo recarga.
    """
    global _loaded_model, _loaded_model_name

    target = model_name or config.WHISPER_MODEL
    if target not in config.WHISPER_MODELS:
        target = config.WHISPER_MODEL

    if _loaded_model is None or _loaded_model_name != target:
        if _loaded_model is not None:
            print(f"🔄  Cambiando modelo Whisper: '{_loaded_model_name}' → '{target}'...")
            del _loaded_model
            _loaded_model = None

        print(f"⏳  Cargando modelo Whisper '{target}' en {DEVICE.upper()}...")
        _loaded_model = whisper.load_model(target, device=DEVICE)
        _loaded_model_name = target
        print(f"✅  Modelo Whisper '{target}' listo.")

    return _loaded_model


def get_available_models() -> dict:
    """Retorna los modelos disponibles con su metadata."""
    return config.WHISPER_MODELS


# ============================================================
#  Audio splitting (pydub)
# ============================================================

def _get_audio_duration_sec(audio_path: str) -> float:
    """Obtiene la duración del audio en segundos."""
    audio = AudioSegment.from_file(audio_path)
    return len(audio) / 1000.0


def _split_audio(audio_path: str, chunk_dur: int, overlap: int) -> list[dict]:
    """
    Divide un audio en chunks con overlap.

    Returns:
        Lista de dicts: {"path": str, "start_sec": float, "end_sec": float}
        Los archivos temporales de chunks se crean en /tmp.
    """
    audio = AudioSegment.from_file(audio_path)
    total_ms = len(audio)
    chunk_ms = chunk_dur * 1000
    overlap_ms = overlap * 1000
    step_ms = chunk_ms - overlap_ms

    chunks = []
    start = 0

    while start < total_ms:
        end = min(start + chunk_ms, total_ms)
        segment = audio[start:end]

        # Exportar chunk como wav temporal (mejor compatibilidad con Whisper)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        segment.export(tmp.name, format="wav")
        tmp.close()

        chunks.append({
            "path": tmp.name,
            "start_sec": start / 1000.0,
            "end_sec": end / 1000.0,
        })

        # Si ya llegamos al final, salimos
        if end >= total_ms:
            break

        start += step_ms

    return chunks


# ============================================================
#  Merge inteligente de transcripciones
# ============================================================

def _find_overlap_boundary(text_a: str, text_b: str, min_words: int = 3) -> tuple[str, str]:
    """
    Encuentra dónde se superponen text_a y text_b y devuelve
    las partes limpias para concatenar sin duplicados.

    Usa dos estrategias:
    1. Coincidencia exacta de secuencias de palabras (tail A == head B).
    2. SequenceMatcher para coincidencia difusa si la exacta falla.

    Returns:
        (text_a_clean, text_b_clean) — ya sin overlap.
    """
    words_a = text_a.split()
    words_b = text_b.split()

    if not words_a or not words_b:
        return text_a, text_b

    # --- Estrategia 1: coincidencia exacta tail(A) == head(B) ---
    max_check = min(40, len(words_a), len(words_b))
    for n in range(max_check, min_words - 1, -1):
        if words_a[-n:] == words_b[:n]:
            # Las últimas n palabras de A son iguales a las primeras n de B
            # → B empieza después del overlap
            return text_a, " ".join(words_b[n:])

    # --- Estrategia 2: SequenceMatcher difuso ---
    window = max(30, min(len(words_a), len(words_b), 80))
    tail_a = words_a[-window:]
    head_b = words_b[:window]

    matcher = SequenceMatcher(None, tail_a, head_b)
    best_len = 0
    best_cut_b = 0

    for block in matcher.get_matching_blocks():
        i, j, size = block
        if size < min_words:
            continue

        a_ends_at = i + size
        # Nos interesa que el match esté en el "borde":
        # cerca del final de tail_a y cerca del inicio de head_b
        if a_ends_at >= len(tail_a) - 3 and j <= 5 and size > best_len:
            best_len = size
            best_cut_b = j + size

    if best_len >= min_words:
        return text_a, " ".join(words_b[best_cut_b:])

    # Sin overlap detectado — concatenar directo
    return text_a, text_b


def _merge_segments(
    all_chunks_segments: list[list[dict]],
    chunk_infos: list[dict],
    overlap_sec: float,
) -> list[dict]:
    """
    Mergea segmentos de múltiples chunks, ajustando timestamps
    y eliminando segmentos duplicados en las zonas de overlap.
    """
    if len(all_chunks_segments) == 1:
        return all_chunks_segments[0]

    merged = []

    for idx, (segs, info) in enumerate(zip(all_chunks_segments, chunk_infos)):
        offset = info["start_sec"]

        # Ajustar timestamps al audio completo
        adjusted = []
        for seg in segs:
            adjusted.append({
                "start": round(seg["start"] + offset, 2),
                "end": round(seg["end"] + offset, 2),
                "text": seg["text"],
            })

        if idx == 0:
            # Primer chunk: tomar todo menos la zona de overlap final
            cutoff = info["end_sec"] - overlap_sec
            merged.extend([s for s in adjusted if s["start"] < cutoff + 1])
        elif idx == len(all_chunks_segments) - 1:
            # Último chunk: tomar solo después de la zona de overlap inicial
            cutoff = info["start_sec"] + overlap_sec
            merged.extend([s for s in adjusted if s["start"] >= cutoff - 1])
        else:
            # Chunks del medio: evitar ambas zonas de overlap
            start_cutoff = info["start_sec"] + overlap_sec
            end_cutoff = info["end_sec"] - overlap_sec
            merged.extend([
                s for s in adjusted
                if start_cutoff - 1 <= s["start"] < end_cutoff + 1
            ])

    # Filtrar vacíos y ordenar
    merged = [s for s in merged if s["text"].strip()]
    merged.sort(key=lambda s: s["start"])

    return merged


# ============================================================
#  Transcripción principal (con chunking automático)
# ============================================================

def transcribe(
    audio_path: str,
    language: str | None = None,
    model_name: str | None = None,
) -> dict:
    """
    Transcribe un archivo de audio a texto.
    Si el audio es largo (> CHUNK_MIN_DURATION_SEC), lo divide en chunks
    con overlap y mergea los resultados inteligentemente.

    Args:
        audio_path: Ruta al archivo de audio.
        language:   Código de idioma (ej: "es", "en"). None = auto-detectar.
        model_name: Nombre del modelo Whisper a usar.

    Returns:
        Dict con: text, language, segments, model, chunks_used, duration.

    Raises:
        TranscriptionError: Si la transcripción falla.
    """
    chunk_files: list[str] = []

    try:
        model = _get_model(model_name)

        # Opciones base — fp16 acelera ~2x en GPU
        options = {"fp16": DEVICE == "cuda"}
        lang = language or config.WHISPER_LANGUAGE
        if lang:
            options["language"] = lang

        # Determinar duración del audio
        duration = _get_audio_duration_sec(audio_path)
        use_chunking = duration > config.CHUNK_MIN_DURATION_SEC

        # --- Audio corto → transcripción directa ---
        if not use_chunking:
            print(f"🎤  Audio corto ({duration:.0f}s), transcripción directa...")
            result = model.transcribe(audio_path, **options)

            segments = [
                {
                    "start": round(s["start"], 2),
                    "end": round(s["end"], 2),
                    "text": s["text"].strip(),
                }
                for s in result.get("segments", [])
            ]

            return {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "segments": segments,
                "model": model_name or config.WHISPER_MODEL,
                "chunks_used": 1,
                "duration": round(duration, 1),
            }

        # --- Audio largo → chunked transcription ---
        chunks = _split_audio(
            audio_path,
            chunk_dur=config.CHUNK_DURATION_SEC,
            overlap=config.CHUNK_OVERLAP_SEC,
        )
        chunk_files = [c["path"] for c in chunks]
        total_chunks = len(chunks)

        print(
            f"🔪  Audio largo ({duration:.0f}s), dividido en {total_chunks} chunks "
            f"({config.CHUNK_DURATION_SEC}s + {config.CHUNK_OVERLAP_SEC}s overlap)"
        )

        # Detectar idioma en el primer chunk si no fue especificado
        detected_lang = lang
        if not detected_lang:
            audio_detect = whisper.load_audio(chunks[0]["path"])
            audio_detect = whisper.pad_or_trim(audio_detect)
            mel = whisper.log_mel_spectrogram(
                audio_detect, n_mels=model.dims.n_mels
            ).to(model.device)
            _, probs = model.detect_language(mel)
            detected_lang = max(probs, key=probs.get)
            options["language"] = detected_lang
            print(f"🌐  Idioma detectado: {detected_lang}")

        # Transcribir cada chunk secuencialmente
        all_texts: list[str] = []
        all_segments: list[list[dict]] = []

        for i, chunk_info in enumerate(chunks):
            chunk_path = chunk_info["path"]
            print(
                f"   📝 Chunk {i + 1}/{total_chunks} "
                f"[{chunk_info['start_sec']:.0f}s → {chunk_info['end_sec']:.0f}s]..."
            )

            result = model.transcribe(chunk_path, **options)
            text = result["text"].strip()
            all_texts.append(text)

            segs = [
                {
                    "start": round(s["start"], 2),
                    "end": round(s["end"], 2),
                    "text": s["text"].strip(),
                }
                for s in result.get("segments", [])
            ]
            all_segments.append(segs)

            print(f"   ✅ Chunk {i + 1} listo ({len(text.split())} palabras)")

        # --- Merge inteligente de textos ---
        print(f"🧩  Mergeando {total_chunks} transcripciones...")
        merged_text = all_texts[0]
        for i in range(1, len(all_texts)):
            _, clean_b = _find_overlap_boundary(merged_text, all_texts[i])
            if clean_b.strip():
                merged_text = merged_text.rstrip() + " " + clean_b.lstrip()

        # --- Merge inteligente de segmentos ---
        merged_segments = _merge_segments(
            all_segments, chunks, config.CHUNK_OVERLAP_SEC
        )

        print(
            f"✅  Transcripción completa: {len(merged_text.split())} palabras, "
            f"{len(merged_segments)} segmentos"
        )

        return {
            "text": merged_text.strip(),
            "language": detected_lang or "unknown",
            "segments": merged_segments,
            "model": model_name or config.WHISPER_MODEL,
            "chunks_used": total_chunks,
            "duration": round(duration, 1),
        }

    except TranscriptionError:
        raise
    except Exception as e:
        raise TranscriptionError(f"Error durante la transcripción: {e}") from e
    finally:
        # Limpiar archivos temporales de chunks
        for path in chunk_files:
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:
                pass


def get_supported_audio_extensions() -> list[str]:
    """Retorna las extensiones de audio soportadas para transcripción."""
    return sorted(config.TRANSCRIPTION_AUDIO_EXTENSIONS)
