"""
audio/stt.py — Motor de Speech-to-Text para JARVIS.

Escucha continuamente el micrófono, detecta habla vs silencio,
y transcribe con Whisper cuando detecta 3 segundos de silencio.
Envía volumen normalizado (0.0-1.0) en cada frame para la esfera.
"""

import time
import numpy as np
import pyaudio
# pyrefly: ignore [missing-import]
from faster_whisper import WhisperModel
from core import config


class JarvisEars:
    def __init__(self):
        modelo = config.WHISPER_MODEL
        device = config.WHISPER_DEVICE
        compute = config.WHISPER_COMPUTE
        print(f"[STT] Cargando corteza auditiva (Whisper '{modelo}') en {device}...")
        self.model = WhisperModel(modelo, device=device, compute_type=compute)
        self.prompt_bilingue = "Hola Jarvis, let's write some code. Inicializa el sistema."
        self.activo = True

    def escuchar_continuamente(self, callback_estado, callback_comando, callback_volumen):
        """
        Bucle principal de escucha.
        
        Args:
            callback_estado: fn(str) — emite estado (EN_ESPERA, ESCUCHANDO, PENSANDO)
            callback_comando: fn(str) — emite texto transcrito
            callback_volumen: fn(float) — emite volumen normalizado 0.0-1.0
        """
        CHUNK = config.AUDIO_CHUNK
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = config.AUDIO_RATE
        UMBRAL_SILENCIO = config.VOLUME_THRESHOLD
        DURACION_SILENCIO = config.SILENCE_DURATION  # 3 segundos

        p = pyaudio.PyAudio()
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )

        callback_estado("EN_ESPERA")
        
        frames_audio = []
        hablando = False
        inicio_silencio = time.time()

        print("[STT] Micrófono abierto. Analizando espectro en tiempo real...")

        try:
            while self.activo:
                try:
                    # Leer bloque de audio crudo
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    
                    # Convertir a float32 para evitar overflow en int16² → fix RuntimeWarning
                    audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                    
                    # Calcular RMS (Root Mean Square) → Volumen real
                    rms = np.sqrt(np.mean(audio_np ** 2))
                    
                    # Normalizar volumen: 0.0 - 1.0 (tope en ~5000 RMS crudo)
                    volumen_normalizado = min(rms / 5000.0, 1.0)

                    if rms > UMBRAL_SILENCIO:
                        if not hablando:
                            hablando = True
                            callback_estado("ESCUCHANDO")
                        
                        inicio_silencio = time.time()
                        frames_audio.append(audio_np)
                        
                        # Enviar volumen normalizado a la UI (cada frame)
                        callback_volumen(volumen_normalizado)
                    else:
                        if hablando:
                            # Enviar volumen bajo durante silencio parcial
                            callback_volumen(volumen_normalizado)
                            frames_audio.append(audio_np)
                            
                            # Si pasamos 3 segundos en silencio → procesar
                            if time.time() - inicio_silencio > DURACION_SILENCIO:
                                hablando = False
                                callback_estado("PENSANDO")
                                callback_volumen(0.0)
                                
                                # Convertir audio al formato de Whisper (float32 normalizado)
                                audio_completo = np.concatenate(frames_audio) / 32768.0
                                frames_audio = []  # Vaciar buffer
                                
                                segments, _ = self.model.transcribe(
                                    audio_completo,
                                    beam_size=5,
                                    initial_prompt=self.prompt_bilingue,
                                    condition_on_previous_text=False
                                )
                                
                                texto = "".join([s.text for s in segments]).strip()
                                if texto:
                                    print(f"[STT] Transcripción: {texto}")
                                    callback_comando(texto)
                                else:
                                    callback_estado("EN_ESPERA")
                        else:
                            # En espera: enviar volumen ambiente sutil
                            callback_volumen(volumen_normalizado * 0.3)
                            
                except Exception as e:
                    print(f"[STT Error]: {e}")
        finally:
            # Limpieza garantizada
            stream.stop_stream()
            stream.close()
            p.terminate()
            print("[STT] Micrófono cerrado limpiamente.")

    def detener(self):
        """Señala al bucle que debe terminar."""
        self.activo = False