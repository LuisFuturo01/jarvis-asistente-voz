# J.A.R.V.I.S. — Asistente de voz de escritorio

Asistente personal por voz: escucha por micrófono (Whisper local), entiende la intención con IA (Gemini o DeepSeek), responde y ejecuta herramientas del sistema. Interfaz PyQt6 con orbe holográfico animado, modo mini y panel de configuración.

## Tecnologías
- Python 3.13 + PyQt6
- faster-whisper (STT) + TTS
- Gemini / DeepSeek API

## Cómo ejecutarlo
```bash
python -m venv venv
venv\Scripts\activate
pip install PyQt6 faster-whisper httpx python-dotenv
copy .env.example .env   # GEMINI_API_KEY=..., GEMINI_MODELO=gemini-2.5-flash
python main.py
```

---
Desarrollado por **Luis Alejandro Zeballos Quiroz** · [Portafolio](https://github.com/LuisFuturo01) · luis.zeballos.quiroz@gmail.com
