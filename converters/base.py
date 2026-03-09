"""
Clase base abstracta para todos los converters.
Responsabilidad: Definir el contrato que cada converter debe cumplir.

Para agregar un nuevo formato, crear un nuevo archivo en converters/
que herede de BaseConverter e implemente los métodos abstractos.
El registry lo descubrirá automáticamente.
"""

from abc import ABC, abstractmethod


class BaseConverter(ABC):
    """Contrato base para cualquier converter de video/audio a mp3."""

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """
        Retorna lista de extensiones soportadas (sin punto).
        Ejemplo: ["mov"] o ["mp4"]
        """
        ...

    @abstractmethod
    def convert_to_mp3(
        self,
        input_path: str,
        output_path: str,
        bitrate: str = "192k",
        sample_rate: int = 44100,
    ) -> str:
        """
        Ejecuta la conversión del archivo de entrada a MP3.

        Args:
            input_path:   Ruta absoluta al archivo de origen.
            output_path:  Ruta absoluta al archivo MP3 de destino.
            bitrate:      Bitrate de audio (ej. "192k", "320k").
            sample_rate:  Frecuencia de muestreo en Hz.

        Returns:
            Ruta absoluta al archivo MP3 generado.

        Raises:
            ConversionError: Si la conversión falla.
        """
        ...

    def validate_input(self, input_path: str) -> bool:
        """Valida que el archivo de entrada exista y tenga extensión soportada."""
        import os

        if not os.path.isfile(input_path):
            return False
        ext = os.path.splitext(input_path)[1].lstrip(".").lower()
        return ext in self.supported_extensions()

    @staticmethod
    def has_audio_stream(input_path: str) -> bool:
        """
        Verifica si el archivo contiene al menos una pista de audio
        usando ffprobe.
        """
        import subprocess

        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-select_streams", "a",
                    "-show_entries", "stream=codec_type",
                    "-of", "csv=p=0",
                    input_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return "audio" in result.stdout
        except Exception:
            return True  # En caso de duda, intentar igual
