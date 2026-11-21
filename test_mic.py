import speech_recognition as sr

print("Buscando micrófonos conectados...")
try:
    mic_list = sr.Microphone.list_microphone_names()
    for index, name in enumerate(mic_list):
        print(f"[{index}] {name}")
    print("\n[ÉXITO] PyAudio y SpeechRecognition están funcionando correctamente.")
except Exception as e:
    print(f"[ERROR FATAL]: {e}")