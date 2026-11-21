"""
core/config.py — Configuración centralizada para JARVIS.

Lee exclusivamente de .env para mantener un solo source of truth.
Provee constantes de audio y helpers de acceso.
"""

import os
from dotenv import load_dotenv, find_dotenv, set_key

# Buscar o crear .env
_ENV_FILE = find_dotenv()
if not _ENV_FILE:
    with open(".env", "w") as f:
        pass
    _ENV_FILE = find_dotenv() or ".env"
load_dotenv(_ENV_FILE, override=True)


# ─── Constantes de Audio ───────────────────────────────────────────
SILENCE_DURATION = 3.0          # Segundos de silencio antes de procesar
VOLUME_THRESHOLD = 300          # Umbral RMS para detectar habla (ajustar según mic)
AUDIO_RATE = 16000              # Sample rate para Whisper
AUDIO_CHUNK = 1024              # Tamaño de buffer de audio
WHISPER_MODEL = "base"          # Modelo Whisper: tiny, base, small, medium
WHISPER_DEVICE = "cpu"          # Device: cpu o cuda
WHISPER_COMPUTE = "int8"        # Compute type para faster-whisper


# ─── Helpers de Configuración ──────────────────────────────────────
def get(key: str, default: str = "") -> str:
    """Lee una variable del .env."""
    return os.getenv(key, default)


def set(key: str, value: str):
    """Escribe una variable al .env y actualiza el entorno."""
    set_key(_ENV_FILE, key, value)
    os.environ[key] = value


def get_env_file_path() -> str:
    """Retorna la ruta al archivo .env."""
    return _ENV_FILE


# ─── Accesos directos para LLM ────────────────────────────────────
def get_active_provider() -> str:
    return get("PROVEEDOR_ACTIVO", "gemini")

def get_gemini_api_key() -> str:
    return get("GEMINI_API_KEY", "")

def get_gemini_model() -> str:
    return get("GEMINI_MODELO", "gemini-2.5-flash")

def get_deepseek_api_key() -> str:
    return get("DEEPSEEK_API_KEY", "")

def get_deepseek_model() -> str:
    return get("DEEPSEEK_MODELO", "deepseek-chat")


def reload():
    """Recarga el .env (útil después de guardar configuración)."""
    load_dotenv(_ENV_FILE, override=True)