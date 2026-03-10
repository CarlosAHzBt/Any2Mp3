"""
Rutas de la API.
Responsabilidad: Definir endpoints HTTP, validar requests
y delegar la lógica a los servicios.
"""

import os

from flask import Blueprint, request, jsonify, send_file

import torch

from converters.registry import get_supported_extensions
from services import file_service, conversion_service, transcription_service, elevenlabs_service

api = Blueprint("api", __name__)


@api.route("/api/device", methods=["GET"])
def device_info():
    """Retorna información sobre el dispositivo de cómputo (GPU/CPU)."""
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_total = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 1)
        vram_used = round(torch.cuda.memory_allocated(0) / (1024 ** 3), 2)
        return jsonify({
            "device": "gpu",
            "name": gpu_name,
            "vram_total_gb": vram_total,
            "vram_used_gb": vram_used,
            "cuda_version": torch.version.cuda or "N/A",
        })
    return jsonify({
        "device": "cpu",
        "name": "CPU",
    })


@api.route("/api/formats", methods=["GET"])
def list_formats():
    """Retorna los formatos de entrada soportados."""
    return jsonify({"formats": get_supported_extensions()})


@api.route("/api/convert", methods=["POST"])
def convert_file():
    """
    Recibe un archivo de video y devuelve el MP3 resultante.

    Espera un form-data con campo 'file'.
    """
    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Nombre de archivo vacío."}), 400

    # Validar extensión antes de guardar
    ext = file_service.get_extension(file.filename)
    supported = get_supported_extensions()
    if ext not in supported:
        return jsonify({
            "error": f"Formato '.{ext}' no soportado.",
            "supported": supported,
        }), 415

    input_path = None
    output_path = None

    try:
        # 1. Guardar archivo subido
        input_path, original_name = file_service.save_uploaded_file(file)

        # 2. Preparar ruta de salida
        output_path = file_service.build_output_path(original_name)

        # 3. Convertir
        result_path = conversion_service.convert(
            input_path, output_path, original_name
        )

        # 4. Enviar MP3 al cliente
        mp3_name = os.path.splitext(original_name)[0] + ".mp3"
        return send_file(
            result_path,
            as_attachment=True,
            download_name=mp3_name,
            mimetype="audio/mpeg",
        )

    except conversion_service.UnsupportedFormatError as e:
        return jsonify({"error": str(e)}), 415

    except conversion_service.ConversionError as e:
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        return jsonify({"error": f"Error inesperado: {e}"}), 500

    finally:
        # Limpieza de archivos temporales
        if input_path:
            file_service.cleanup_file(input_path)
        if output_path:
            file_service.cleanup_file(output_path)


# ============================================================
#  Transcripción — Audio a Texto (Whisper)
# ============================================================

@api.route("/api/transcription/formats", methods=["GET"])
def transcription_formats():
    """Retorna las extensiones de audio soportadas para transcripción."""
    return jsonify({"formats": transcription_service.get_supported_audio_extensions()})


@api.route("/api/transcription/models", methods=["GET"])
def transcription_models():
    """Retorna los modelos Whisper disponibles."""
    return jsonify({"models": transcription_service.get_available_models()})


@api.route("/api/transcription/engines", methods=["GET"])
def transcription_engines():
    """Retorna los motores de transcripción disponibles."""
    engines = [
        {
            "id": "whisper",
            "name": "OpenAI Whisper",
            "description": "Modelo local — corre en tu GPU/CPU, sin costo por uso",
            "available": True,
            "icon": "🧠",
        },
        {
            "id": "elevenlabs",
            "name": "ElevenLabs Scribe v2",
            "description": "API cloud — SOTA, ultra rápido, requiere API key",
            "available": elevenlabs_service.is_available(),
            "icon": "🔷",
        },
    ]
    return jsonify({"engines": engines})


@api.route("/api/transcribe", methods=["POST"])
def transcribe_file():
    """
    Recibe un archivo de audio y devuelve la transcripción en texto.

    Espera un form-data con campo 'file' y opcionalmente 'language'.
    """
    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Nombre de archivo vacío."}), 400

    # Validar extensión
    ext = file_service.get_extension(file.filename)
    supported = transcription_service.get_supported_audio_extensions()
    if ext not in supported:
        return jsonify({
            "error": f"Formato '.{ext}' no soportado para transcripción.",
            "supported": supported,
        }), 415

    # Idioma opcional ("es", "en", etc.) — None = auto-detectar
    language = request.form.get("language") or None
    # Modelo opcional ("tiny", "base", "small", etc.)
    model_name = request.form.get("model") or None
    # Motor de transcripción: "whisper" o "elevenlabs"
    engine = request.form.get("engine", "whisper")
    # Diarization (solo ElevenLabs)
    diarize = request.form.get("diarize", "false").lower() == "true"

    input_path = None
    try:
        # 1. Guardar archivo subido
        input_path, original_name = file_service.save_uploaded_file(file)

        # 2. Transcribir con el motor seleccionado
        if engine == "elevenlabs":
            result = elevenlabs_service.transcribe(
                input_path, language=language, diarize=diarize
            )
        else:
            result = transcription_service.transcribe(
                input_path, language=language, model_name=model_name
            )

        return jsonify(result)

    except (transcription_service.TranscriptionError,
            elevenlabs_service.ScribeTranscriptionError) as e:
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        return jsonify({"error": f"Error inesperado: {e}"}), 500

    finally:
        if input_path:
            file_service.cleanup_file(input_path)
