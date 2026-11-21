"""
brain/router.py — Orquestador central de JARVIS.

Recibe texto transcrito, decide si es un comando local o si debe
consultarse a Gemini, y emite la respuesta por signals de Qt.
Corre en un QThread separado para no bloquear la UI.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from brain.gemini_client import GeminiClient


# Comandos locales que no necesitan LLM
COMANDOS_LOCALES = {
    "mini": "MODO_MINI",
    "segundo plano": "MODO_MINI",
    "minimiza": "MODO_MINI",
    "completa": "MODO_FULLSCREEN",
    "maximiza": "MODO_FULLSCREEN",
    "pantalla completa": "MODO_FULLSCREEN",
    "normal": "MODO_NORMAL",
    "restaura": "MODO_NORMAL",
    "cierra": "CERRAR",
    "apaga": "CERRAR",
    "apágate": "CERRAR",
}


def detectar_comando_local(texto: str) -> str | None:
    """
    Revisa si el texto contiene un comando local conocido.
    
    Returns:
        str con el tipo de comando, o None si no es comando local.
    """
    texto_lower = texto.lower().strip()
    for trigger, comando in COMANDOS_LOCALES.items():
        if trigger in texto_lower:
            return comando
    return None


class BrainWorker(QThread):
    """
    Worker thread que procesa comandos de voz.
    
    Señales:
        senal_pensando: Emitida cuando empieza a procesar
        senal_chunk: Emitida con cada fragmento de respuesta (streaming)
        senal_respuesta_completa: Emitida con la respuesta final completa
        senal_comando_local: Emitida cuando detecta un comando local
        senal_error: Emitida si hay un error
    """
    senal_pensando = pyqtSignal()
    senal_chunk = pyqtSignal(str)
    senal_respuesta_completa = pyqtSignal(str)
    senal_comando_local = pyqtSignal(str)
    senal_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.gemini = GeminiClient()
        self._texto_pendiente = None
        self._debe_procesar = False
    
    def procesar(self, texto: str):
        """
        Encola un texto para procesar. Si el worker ya está corriendo,
        espera a que termine. Si no, lo arranca.
        """
        self._texto_pendiente = texto
        self._debe_procesar = True
        if not self.isRunning():
            self.start()
    
    def run(self):
        """Procesa el texto pendiente."""
        while self._debe_procesar:
            self._debe_procesar = False
            texto = self._texto_pendiente
            if not texto:
                return
            
            # 1. Verificar si es comando local
            comando = detectar_comando_local(texto)
            if comando:
                self.senal_comando_local.emit(comando)
                return
            
            # 2. No es comando local → consultar Gemini
            self.senal_pensando.emit()
            
            respuesta_completa = []
            try:
                for chunk in self.gemini.generar_respuesta_stream(texto):
                    self.senal_chunk.emit(chunk)
                    respuesta_completa.append(chunk)
                
                texto_final = "".join(respuesta_completa).strip()
                if texto_final:
                    self.senal_respuesta_completa.emit(texto_final)
                else:
                    self.senal_error.emit("Gemini no generó respuesta.")
            except Exception as e:
                self.senal_error.emit(str(e))
    
    def reconfigurar_gemini(self):
        """Reconfigura el cliente Gemini (tras cambiar settings)."""
        self.gemini.reconfigurar()
