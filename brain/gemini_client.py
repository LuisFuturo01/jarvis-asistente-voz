"""
brain/gemini_client.py — Cliente aislado para la API de Google Gemini.

Usa la API REST directamente via httpx para tener control total sobre
timeouts y retries, evitando los retries internos agresivos del SDK
que bloquean el thread con rate limits del tier gratuito.
"""

import time
import re
import json
import httpx
from core import config


# System prompt que define la personalidad de Jarvis
SYSTEM_PROMPT = (
    "Eres J.A.R.V.I.S., un asistente personal inteligente inspirado en el de Iron Man. "
    "Respondes de forma concisa, inteligente y con un toque de humor sutil. "
    "Puedes responder en espanol o ingles segun el idioma del usuario. "
    "Manten tus respuestas breves y directas a menos que te pidan una explicacion detallada. "
    "No uses emojis ni formato markdown en tus respuestas ya que seran leidas en voz alta."
)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
MAX_RETRIES = 3
TIMEOUT = 30  # segundos


class GeminiClient:
    """
    Cliente Gemini via API REST directa.
    Control total de timeouts y retries sin el SDK.
    """
    
    def __init__(self):
        self.api_key = None
        self.modelo = None
        self.historial = []  # Lista de {role, parts}
        self._configurar()
    
    def _configurar(self):
        """Configura el cliente con la API key actual."""
        self.api_key = config.get_gemini_api_key()
        self.modelo = config.get_gemini_model()
        self.historial = []
        
        if not self.api_key:
            print("[BRAIN] No hay API key de Gemini configurada.")
            return
        
        print(f"[BRAIN] Gemini conectado: {self.modelo}")
    
    def reconfigurar(self):
        """Reconfigura el cliente (util tras cambiar API key en settings)."""
        config.reload()
        self._configurar()
    
    def _build_payload(self, texto: str) -> dict:
        """Construye el payload JSON para la API."""
        contents = list(self.historial)
        contents.append({
            "role": "user",
            "parts": [{"text": texto}]
        })
        
        return {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024
            }
        }
    
    def _add_to_history(self, user_text: str, model_text: str):
        """Agrega un intercambio al historial conversacional."""
        self.historial.append({
            "role": "user",
            "parts": [{"text": user_text}]
        })
        self.historial.append({
            "role": "model",
            "parts": [{"text": model_text}]
        })
        # Limitar historial (ultimos 20 intercambios = 40 entries)
        if len(self.historial) > 40:
            self.historial = self.historial[-40:]
    
    def generar_respuesta(self, texto: str) -> str:
        """Genera una respuesta completa con retry automatico."""
        if not self.api_key:
            return "No puedo responder: la API de Gemini no esta configurada. Ve a Configuracion."
        
        url = f"{BASE_URL}/models/{self.modelo}:generateContent?key={self.api_key}"
        payload = self._build_payload(texto)
        
        for intento in range(MAX_RETRIES):
            try:
                with httpx.Client(timeout=TIMEOUT) as client:
                    response = client.post(url, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    text = self._extract_text(data)
                    if text:
                        self._add_to_history(texto, text)
                    return text or "Sin respuesta."
                
                elif response.status_code == 429:
                    wait_time = self._extract_retry_delay(response.text)
                    if intento < MAX_RETRIES - 1:
                        print(f"[BRAIN] Rate limit. Esperando {wait_time:.0f}s... ({intento + 1}/{MAX_RETRIES})")
                        time.sleep(wait_time)
                    else:
                        return f"Rate limit: espera {wait_time:.0f}s e intenta de nuevo."
                
                elif response.status_code == 404:
                    return f"Error: Modelo '{self.modelo}' no encontrado. Cambialo en Configuracion."
                
                elif response.status_code == 400 and 'API_KEY_INVALID' in response.text:
                    return "Error: la API key de Gemini no es válida. Actualízala en Configuración (⚙)."
                elif response.status_code == 401 or response.status_code == 403:
                    return "Error: API key invalida. Verifica en Configuracion."
                
                else:
                    return f"Error HTTP {response.status_code}: {response.text[:100]}"
                    
            except httpx.TimeoutException:
                if intento < MAX_RETRIES - 1:
                    print(f"[BRAIN] Timeout. Reintentando... ({intento + 1}/{MAX_RETRIES})")
                else:
                    return "Error: Timeout al conectar con Gemini."
            except Exception as e:
                print(f"[BRAIN] Error: {e}")
                return f"Error de conexion: {str(e)[:100]}"
        
        return "No se pudo obtener respuesta despues de varios intentos."
    
    def generar_respuesta_stream(self, texto: str):
        """Genera una respuesta con streaming y retry automatico."""
        if not self.api_key:
            yield "No puedo responder: la API de Gemini no esta configurada."
            return
        
        url = f"{BASE_URL}/models/{self.modelo}:streamGenerateContent?alt=sse&key={self.api_key}"
        payload = self._build_payload(texto)
        
        for intento in range(MAX_RETRIES):
            try:
                full_response = []
                
                with httpx.Client(timeout=TIMEOUT) as client:
                    with client.stream("POST", url, json=payload) as response:
                        if response.status_code == 429:
                            response.read()
                            wait_time = self._extract_retry_delay(response.text)
                            if intento < MAX_RETRIES - 1:
                                print(f"[BRAIN] Rate limit. Esperando {wait_time:.0f}s... ({intento + 1}/{MAX_RETRIES})")
                                time.sleep(wait_time)
                                continue
                            else:
                                yield f"Rate limit: espera {wait_time:.0f}s e intenta de nuevo."
                                return
                        
                        if response.status_code == 404:
                            response.read()
                            yield f"Error: Modelo '{self.modelo}' no encontrado."
                            return
                        
                        if response.status_code != 200:
                            response.read()
                            yield f"Error HTTP {response.status_code}"
                            return
                        
                        for line in response.iter_lines():
                            if line.startswith("data: "):
                                json_str = line[6:]
                                try:
                                    data = json.loads(json_str)
                                    text = self._extract_text(data)
                                    if text:
                                        full_response.append(text)
                                        yield text
                                except json.JSONDecodeError:
                                    pass
                
                # Guardar en historial al completar
                result = "".join(full_response).strip()
                if result:
                    self._add_to_history(texto, result)
                return  # Exito
                
            except httpx.TimeoutException:
                if intento < MAX_RETRIES - 1:
                    print(f"[BRAIN] Timeout stream. Reintentando... ({intento + 1}/{MAX_RETRIES})")
                else:
                    yield "Error: Timeout al conectar con Gemini."
            except Exception as e:
                print(f"[BRAIN] Error stream: {e}")
                yield f"Error: {str(e)[:100]}"
                return
    
    def _extract_text(self, data: dict) -> str:
        """Extrae el texto de la respuesta JSON de la API."""
        try:
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
        except (KeyError, IndexError):
            pass
        return ""
    
    def _extract_retry_delay(self, error_text: str) -> float:
        """Extrae el tiempo de espera sugerido por la API."""
        try:
            match = re.search(r'retry in (\d+\.?\d*)', error_text.lower())
            if match:
                return float(match.group(1)) + 2  # +2s de margen
        except:
            pass
        return 15.0  # Default 15s
    
    def limpiar_historial(self):
        """Reinicia el historial de conversacion."""
        self.historial = []
