"""
Servicio de conversión.
Responsabilidad: Orquestar el flujo completo de conversión
delegando al converter correcto según el tipo de archivo.
"""

from converters.registry import get_converter, get_supported_extensions
from services.file_service import get_extension
import config


class UnsupportedFormatError(Exception):
    """Se lanza cuando el formato del archivo no tiene converter registrado."""
    pass


class ConversionError(Exception):
    """Se lanza cuando la conversión falla por cualquier motivo."""
    pass


def convert(input_path: str, output_path: str, original_name: str) -> str:
    """
    Ejecuta la conversión de un archivo de video a MP3.

    Args:
        input_path:    Ruta al archivo subido.
        output_path:   Ruta donde se generará el MP3.
        original_name: Nombre original del archivo (para extraer extensión).

    Returns:
        Ruta absoluta al MP3 generado.

    Raises:
        UnsupportedFormatError: Si no hay converter para ese formato.
        ConversionError:        Si el proceso de conversión falla.
    """
    ext = get_extension(original_name)
    converter = get_converter(ext)

    if converter is None:
        supported = ", ".join(get_supported_extensions())
        raise UnsupportedFormatError(
            f"Formato '.{ext}' no soportado. Formatos disponibles: {supported}"
        )

    try:
        result_path = converter.convert_to_mp3(
            input_path=input_path,
            output_path=output_path,
            bitrate=config.DEFAULT_AUDIO_BITRATE,
            sample_rate=config.DEFAULT_AUDIO_SAMPLE_RATE,
        )
        return result_path
    except Exception as e:
        raise ConversionError(f"Error durante la conversión: {e}") from e
