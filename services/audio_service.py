"""
Servicio para operaciones de audio que no son estrictamente conversión,
como unir múltiples archivos MP3.
"""

import os
import subprocess

import config


class AudioMergeError(Exception):
    """Excepción lanzada cuando ocurre un error al unir archivos de audio."""
    pass


def merge_mp3_files(input_paths: list[str], output_path: str) -> str:
    """
    Une múltiples archivos de audio en un MP3.
    Usa filter_complex concat de ffmpeg (recodifica, tolera codecs/sample rates distintos).

    Args:
        input_paths: Lista de rutas absolutas de los MP3 a unir.
        output_path: Ruta absoluta donde se guardará el resultado.

    Returns:
        Ruta absoluta del archivo resultante.

    Raises:
        ValueError: Si hay menos de 2 archivos.
        AudioMergeError: Si hay un error con ffmpeg o los archivos.
    """
    if not input_paths or len(input_paths) < 2:
        raise ValueError("Se requieren al menos dos archivos para unir.")

    for path in input_paths:
        if not os.path.isfile(path):
            raise AudioMergeError(f"El archivo {path} no existe o no es accesible.")

    # Usaremos filter_complex para asegurar que formatos con diferentes
    # codecs o sample rates se unan correctamente y generen un MP3 válido.
    
    cmd = ["ffmpeg", "-y"]
    filter_parts = []
    
    for i, path in enumerate(input_paths):
        cmd.extend(["-i", path])
        filter_parts.append(f"[{i}:a]")
        
    filter_parts.append(f"concat=n={len(input_paths)}:v=0:a=1[out]")
    filter_complex = "".join(filter_parts)
    
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "libmp3lame",
        "-q:a", "5",  # preset rápido, ~130kbps VBR
        output_path
    ])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.CONVERSION_TIMEOUT,
        )

        if result.returncode != 0:
            raise AudioMergeError(f"Error interno al unir audios: {result.stderr}")

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise AudioMergeError("ffmpeg terminó pero el archivo de salida está vacío o no existe.")

        return output_path

    except Exception as e:
        if not isinstance(e, AudioMergeError):
            raise AudioMergeError(f"Excepción al ejecutar ffmpeg: {str(e)}")
        raise e
