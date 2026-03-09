"""
Converter para archivos .mov (Apple QuickTime).
Responsabilidad: Convertir archivos .mov a MP3 usando ffmpeg.
"""

import subprocess

from converters.base import BaseConverter


class MovConverter(BaseConverter):
    """Convierte archivos .mov a MP3."""

    def supported_extensions(self) -> list[str]:
        return ["mov"]

    def convert_to_mp3(
        self,
        input_path: str,
        output_path: str,
        bitrate: str = "192k",
        sample_rate: int = 44100,
    ) -> str:
        if not self.validate_input(input_path):
            raise ValueError(f"Archivo inválido o extensión no soportada: {input_path}")

        if not self.has_audio_stream(input_path):
            raise RuntimeError(
                "El archivo .mov no contiene pista de audio. "
                "No se puede extraer MP3 de un video sin sonido."
            )

        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vn",                      # Sin video
            "-acodec", "libmp3lame",    # Codec MP3
            "-ab", bitrate,             # Bitrate
            "-ar", str(sample_rate),    # Sample rate
            "-y",                       # Sobrescribir sin preguntar
            output_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Error al convertir .mov a MP3:\n{result.stderr}"
            )

        return output_path
