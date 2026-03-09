"""
Servicio de archivos.
Responsabilidad: Gestionar la recepción, almacenamiento temporal
y limpieza de archivos subidos y generados.
"""

import os
import uuid
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

import config


def save_uploaded_file(file: FileStorage) -> tuple[str, str]:
    """
    Guarda un archivo subido en la carpeta de uploads con nombre único.

    Returns:
        Tupla (ruta_absoluta, nombre_original)
    """
    original_name = secure_filename(file.filename or "unknown")
    ext = os.path.splitext(original_name)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(config.UPLOAD_FOLDER, unique_name)
    file.save(dest_path)
    return dest_path, original_name


def build_output_path(original_name: str) -> str:
    """
    Genera la ruta de salida para el MP3 resultante.
    """
    base_name = os.path.splitext(original_name)[0]
    unique_name = f"{base_name}_{uuid.uuid4().hex[:8]}.mp3"
    return os.path.join(config.OUTPUT_FOLDER, unique_name)


def get_extension(filename: str) -> str:
    """Extrae la extensión sin punto, en minúsculas."""
    return os.path.splitext(filename)[1].lstrip(".").lower()


def cleanup_file(path: str) -> None:
    """Elimina un archivo temporal si existe."""
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
