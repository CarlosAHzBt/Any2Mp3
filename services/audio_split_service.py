"""
Servicio para dividir audios en fragmentos usando VAD (Voice Activity Detection)
para cortar en los silencios.
"""

import os
import torch
from pydub import AudioSegment

class AudioSplitError(Exception):
    pass

# Cache del modelo VAD (torch.hub.load es costoso por request)
_vad_cache = None

def load_vad_model():
    global _vad_cache
    if _vad_cache is None:
        try:
            _vad_cache = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                        model='silero_vad',
                                        force_reload=False,
                                        trust_repo=True)
        except Exception as e:
            raise AudioSplitError(f"No se pudo cargar el modelo VAD: {e}")
    return _vad_cache

def split_audio(file_path: str, output_dir: str, target_duration_mins: int = 20, window_mins: int = 1) -> list[str]:
    """
    Divide un archivo de audio en fragmentos de aproximadamente 'target_duration_mins'.
    Busca un silencio en una ventana alrededor del corte ideal usando VAD.
    Retorna una lista de rutas de los archivos generados.
    """
    if not os.path.isfile(file_path):
        raise AudioSplitError(f"Archivo no encontrado: {file_path}")
        
    target_duration_ms = target_duration_mins * 60 * 1000
    window_ms = window_mins * 60 * 1000

    try:
        audio = AudioSegment.from_file(file_path)
    except Exception as e:
        raise AudioSplitError(f"Error al cargar audio: {str(e)}")

    total_duration_ms = len(audio)
    if total_duration_ms <= target_duration_ms:
        return [file_path] # No hay que dividir

    model, utils = load_vad_model()
    get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks = utils
    
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # Exportaremos en MP3
    ext = ".mp3"
    
    output_paths = []
    current_start_ms = 0
    segment_idx = 1
    
    while current_start_ms < total_duration_ms:
        ideal_cut_ms = current_start_ms + target_duration_ms
        
        # Si el fragmento restante es menor que el corte + un margen razonable, terminar
        if ideal_cut_ms + (target_duration_ms // 3) > total_duration_ms:
            segment_audio = audio[current_start_ms:]
            out_path = os.path.join(output_dir, f"{base_name}_part{segment_idx}{ext}")
            segment_audio.export(out_path, format="mp3")
            output_paths.append(out_path)
            break
            
        # Determinar la ventana donde buscar el silencio
        window_start = max(current_start_ms + 1000, ideal_cut_ms - window_ms // 2)
        window_end = min(total_duration_ms, ideal_cut_ms + window_ms // 2)
        
        temp_window_path = os.path.join(output_dir, f"temp_window_{segment_idx}.wav")
        window_audio = audio[window_start:window_end]
        # Silero VAD requiere 16kHz en mono
        window_audio.export(temp_window_path, format="wav", parameters=["-ar", "16000", "-ac", "1"])
        
        try:
            wav = read_audio(temp_window_path, sampling_rate=16000)
            speech_timestamps = get_speech_timestamps(wav, model, sampling_rate=16000)
        finally:
            if os.path.exists(temp_window_path):
                os.remove(temp_window_path)
                
        cut_ms = ideal_cut_ms # Default a ideal si no hallamos silencio
        
        silences_in_window = []
        if not speech_timestamps:
            cut_ms = ideal_cut_ms
        else:
            def samples_to_ms(s): return int((s / 16000) * 1000)
            
            first_speech_start = samples_to_ms(speech_timestamps[0]['start'])
            if first_speech_start > 0:
                silences_in_window.append((0, first_speech_start))
                
            for i in range(len(speech_timestamps) - 1):
                s_end = samples_to_ms(speech_timestamps[i]['end'])
                s_next_start = samples_to_ms(speech_timestamps[i+1]['start'])
                silences_in_window.append((s_end, s_next_start))
                
            last_speech_end = samples_to_ms(speech_timestamps[-1]['end'])
            window_duration_ms = window_end - window_start
            if last_speech_end < window_duration_ms:
                silences_in_window.append((last_speech_end, window_duration_ms))
                
            if silences_in_window:
                # Encontrar el silencio mas cercano al corte ideal
                best_cut_in_window = ideal_cut_ms - window_start
                min_dist = float('inf')
                chosen_cut_in_window = best_cut_in_window
                
                for s_start, s_end in silences_in_window:
                    mid_silence = (s_start + s_end) // 2
                    dist = abs(mid_silence - best_cut_in_window)
                    if dist < min_dist:
                        min_dist = dist
                        chosen_cut_in_window = mid_silence
                
                cut_ms = window_start + chosen_cut_in_window
                
        segment_audio = audio[current_start_ms:cut_ms]
        out_path = os.path.join(output_dir, f"{base_name}_part{segment_idx}{ext}")
        segment_audio.export(out_path, format="mp3")
        output_paths.append(out_path)
        
        current_start_ms = cut_ms
        segment_idx += 1
        
    return output_paths
