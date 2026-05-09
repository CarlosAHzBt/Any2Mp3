"""
Tests para la funcionalidad de unir archivos de audio.
Cubren: validación de inputs, orden del merge, performance,
manejo de errores y flujo completo.
"""

import os
import struct
import tempfile
import subprocess
import time
import unittest

from services.audio_service import merge_mp3_files, AudioMergeError


def create_tone_audio(path, duration_seconds=1, frequency=440, fmt="mp3"):
    """Genera un archivo de audio real con un tono sinusoidal usando ffmpeg."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency={frequency}:duration={duration_seconds}",
            "-q:a", "9",
            path
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )


def get_audio_duration(path):
    """Obtiene la duración de un archivo de audio usando ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path
        ],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())


class TestMergeValidation(unittest.TestCase):
    """Validación de inputs: mínimo de archivos, archivos inexistentes."""

    def setUp(self):
        self._temps = []

    def tearDown(self):
        for p in self._temps:
            if os.path.exists(p):
                os.remove(p)

    def _mp3(self, duration=1, freq=440):
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        create_tone_audio(path, duration, freq)
        self._temps.append(path)
        return path

    def _out(self):
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        self._temps.append(path)
        return path

    def test_rejects_empty_list(self):
        with self.assertRaises(ValueError, msg="Se requieren al menos dos archivos para unir."):
            merge_mp3_files([], self._out())

    def test_rejects_single_file(self):
        with self.assertRaises(ValueError, msg="Se requieren al menos dos archivos para unir."):
            merge_mp3_files([self._mp3()], self._out())

    def test_rejects_nonexistent_file(self):
        real = self._mp3()
        with self.assertRaisesRegex(AudioMergeError, "no existe"):
            merge_mp3_files([real, "/no/existe/nada.mp3"], self._out())


class TestMergeOrder(unittest.TestCase):
    """Verifica que el merge respeta estrictamente el orden de la lista."""

    def setUp(self):
        self._temps = []

    def tearDown(self):
        for p in self._temps:
            if os.path.exists(p):
                os.remove(p)

    def _tone(self, freq, duration=1):
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        create_tone_audio(path, duration, freq)
        self._temps.append(path)
        return path

    def _out(self):
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        self._temps.append(path)
        return path

    def test_merge_order_abc_differs_from_cba(self):
        """
        Genera tres tonos con frecuencias distintas (200, 600, 1000 Hz).
        Hace merge en orden A-B-C y luego C-B-A.
        Si el orden se respeta, los archivos binarios deben ser diferentes.
        """
        a = self._tone(200, 1)
        b = self._tone(600, 1)
        c = self._tone(1000, 1)

        out_abc = self._out()
        out_cba = self._out()

        merge_mp3_files([a, b, c], out_abc)
        merge_mp3_files([c, b, a], out_cba)

        with open(out_abc, "rb") as f1, open(out_cba, "rb") as f2:
            data_abc = f1.read()
            data_cba = f2.read()

        self.assertNotEqual(data_abc, data_cba,
                            "El merge en distinto orden debería producir archivos distintos")


class TestMergeOutput(unittest.TestCase):
    """Verifica propiedades observables del archivo resultante."""

    def setUp(self):
        self._temps = []

    def tearDown(self):
        for p in self._temps:
            if os.path.exists(p):
                os.remove(p)

    def _mp3(self, duration=1, freq=440):
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        create_tone_audio(path, duration, freq)
        self._temps.append(path)
        return path

    def _out(self):
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        self._temps.append(path)
        return path

    def test_output_exists_and_not_empty(self):
        a, b = self._mp3(2), self._mp3(3)
        out = self._out()
        result = merge_mp3_files([a, b], out)
        self.assertEqual(result, out)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 0)

    def test_duration_is_sum_of_inputs(self):
        a = self._mp3(3)
        b = self._mp3(5)
        out = self._out()
        merge_mp3_files([a, b], out)

        dur = get_audio_duration(out)
        self.assertAlmostEqual(dur, 8.0, delta=0.5,
                               msg="La duración del merge debe ser la suma de los inputs")

    def test_duration_updates_when_adding_more_files(self):
        a = self._mp3(2)
        b = self._mp3(3)
        c = self._mp3(4)

        out_ab = self._out()
        out_abc = self._out()

        merge_mp3_files([a, b], out_ab)
        merge_mp3_files([a, b, c], out_abc)

        dur_ab = get_audio_duration(out_ab)
        dur_abc = get_audio_duration(out_abc)

        self.assertAlmostEqual(dur_ab, 5.0, delta=0.5)
        self.assertAlmostEqual(dur_abc, 9.0, delta=0.5)
        self.assertGreater(dur_abc, dur_ab)

    def test_reordering_does_not_change_total_duration(self):
        a = self._mp3(2, 300)
        b = self._mp3(3, 600)
        c = self._mp3(4, 900)

        out1 = self._out()
        out2 = self._out()

        merge_mp3_files([a, b, c], out1)
        merge_mp3_files([c, a, b], out2)

        dur1 = get_audio_duration(out1)
        dur2 = get_audio_duration(out2)
        self.assertAlmostEqual(dur1, dur2, delta=0.3,
                               msg="Reordenar no debería cambiar la duración total")

    def test_output_is_valid_mp3(self):
        a, b = self._mp3(1), self._mp3(1)
        out = self._out()
        merge_mp3_files([a, b], out)

        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", out],
            capture_output=True, text=True, check=True
        )
        self.assertEqual(probe.stdout.strip(), "mp3")

    def test_download_name_has_mp3_extension(self):
        """El output path que devuelve merge_mp3_files termina en .mp3."""
        a, b = self._mp3(1), self._mp3(1)
        out = self._out()
        result = merge_mp3_files([a, b], out)
        self.assertTrue(result.endswith(".mp3"))


class TestMergeErrors(unittest.TestCase):
    """Manejo de errores: archivos corruptos, merge fallido."""

    def setUp(self):
        self._temps = []

    def tearDown(self):
        for p in self._temps:
            if os.path.exists(p):
                os.remove(p)

    def _mp3(self, duration=1):
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        create_tone_audio(path, duration)
        self._temps.append(path)
        return path

    def _out(self):
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        self._temps.append(path)
        return path

    def test_corrupt_file_raises_error(self):
        good = self._mp3(1)
        fd, bad = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        self._temps.append(bad)
        with open(bad, "wb") as f:
            f.write(b"not a real mp3 file at all, just garbage data")

        out = self._out()
        with self.assertRaises(AudioMergeError):
            merge_mp3_files([good, bad], out)

    def test_valid_files_still_work_after_error(self):
        """Después de un merge fallido, un merge válido debe funcionar."""
        good_a = self._mp3(1)
        good_b = self._mp3(1)

        fd, bad = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        self._temps.append(bad)
        with open(bad, "wb") as f:
            f.write(b"garbage")

        out_bad = self._out()
        try:
            merge_mp3_files([good_a, bad], out_bad)
        except AudioMergeError:
            pass

        out_good = self._out()
        result = merge_mp3_files([good_a, good_b], out_good)
        self.assertTrue(os.path.exists(result))
        self.assertGreater(os.path.getsize(result), 0)


class TestMergePerformance(unittest.TestCase):
    """El merge debe completarse dentro de un umbral de tiempo razonable."""

    def setUp(self):
        self._temps = []

    def tearDown(self):
        for p in self._temps:
            if os.path.exists(p):
                os.remove(p)

    def _mp3(self, duration=1):
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        create_tone_audio(path, duration)
        self._temps.append(path)
        return path

    def _out(self):
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        self._temps.append(path)
        return path

    def test_three_short_files_merge_under_five_seconds(self):
        a = self._mp3(3)
        b = self._mp3(5)
        c = self._mp3(4)
        out = self._out()

        start = time.time()
        merge_mp3_files([a, b, c], out)
        elapsed = time.time() - start

        self.assertLess(elapsed, 5.0,
                        f"El merge de 3 archivos cortos tardó {elapsed:.1f}s, "
                        "debería ser menor a 5s")


class TestFullMergeFlow(unittest.TestCase):
    """Flujo completo: crear archivos desordenados, reordenar, merge, validar."""

    def setUp(self):
        self._temps = []

    def tearDown(self):
        for p in self._temps:
            if os.path.exists(p):
                os.remove(p)

    def _tone(self, freq, duration=2):
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        create_tone_audio(path, duration, freq)
        self._temps.append(path)
        return path

    def _out(self):
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        self._temps.append(path)
        return path

    def test_upload_reorder_merge_download(self):
        """
        Simula: subir 3 archivos desordenados (parte_03, parte_01, parte_02),
        reordenarlos a (parte_01, parte_02, parte_03), hacer merge y verificar
        que el resultado existe, tiene la duración correcta y es MP3 válido.
        """
        parte_03 = self._tone(1000, 2)
        parte_01 = self._tone(200, 2)
        parte_02 = self._tone(600, 2)

        upload_order = [parte_03, parte_01, parte_02]
        reordered = [parte_01, parte_02, parte_03]

        out = self._out()
        result = merge_mp3_files(reordered, out)

        self.assertTrue(os.path.exists(result))
        self.assertGreater(os.path.getsize(result), 0)

        dur = get_audio_duration(result)
        self.assertAlmostEqual(dur, 6.0, delta=0.5)

        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", result],
            capture_output=True, text=True, check=True
        )
        self.assertEqual(probe.stdout.strip(), "mp3")

    def test_merge_then_change_list_invalidates_old_result(self):
        """
        Simula: merge A+B, luego el usuario cambia la lista a A+C.
        El segundo merge debe producir un resultado diferente al primero.
        """
        a = self._tone(200, 2)
        b = self._tone(600, 2)
        c = self._tone(1000, 2)

        out1 = self._out()
        out2 = self._out()

        merge_mp3_files([a, b], out1)
        merge_mp3_files([a, c], out2)

        with open(out1, "rb") as f1, open(out2, "rb") as f2:
            self.assertNotEqual(f1.read(), f2.read(),
                                "Un merge con lista diferente debe generar resultado diferente")


if __name__ == "__main__":
    unittest.main()
