"""
core/events.py — Sistema de eventos desacoplado para JARVIS.

Permite que audio, brain y UI se comuniquen sin importarse mutuamente.
Cada módulo publica/suscribe eventos sin conocer a los demás.
"""

from enum import Enum, auto
from typing import Callable, Any


class EventType(Enum):
    """Todos los eventos posibles en el sistema."""
    # Audio
    VOLUME_UPDATE = auto()       # float: volumen normalizado 0.0 - 1.0
    STATE_CHANGE = auto()        # str: EN_ESPERA, ESCUCHANDO, PENSANDO, RESPONDIENDO
    
    # Transcripción
    COMMAND_RECEIVED = auto()    # str: texto transcrito del usuario
    
    # Brain
    RESPONSE_STARTED = auto()    # None: Gemini empezó a generar
    RESPONSE_CHUNK = auto()      # str: fragmento de respuesta (streaming)
    RESPONSE_COMPLETE = auto()   # str: respuesta completa final
    RESPONSE_ERROR = auto()      # str: mensaje de error
    
    # Comandos locales
    LOCAL_COMMAND = auto()       # str: comando local detectado (mini, cierra, etc.)


class EventBus:
    """
    Bus de eventos singleton para comunicación entre módulos.
    
    Uso:
        bus = EventBus()
        bus.subscribe(EventType.VOLUME_UPDATE, mi_callback)
        bus.publish(EventType.VOLUME_UPDATE, 0.75)
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._listeners = {}
        return cls._instance
    
    def subscribe(self, event_type: EventType, callback: Callable):
        """Registra un callback para un tipo de evento."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Elimina un callback de un tipo de evento."""
        if event_type in self._listeners:
            self._listeners[event_type] = [
                cb for cb in self._listeners[event_type] if cb != callback
            ]
    
    def publish(self, event_type: EventType, data: Any = None):
        """Dispara todos los callbacks registrados para un tipo de evento."""
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"[EventBus] Error en listener de {event_type.name}: {e}")
    
    def clear(self):
        """Limpia todos los listeners. Útil para tests o reset."""
        self._listeners.clear()
