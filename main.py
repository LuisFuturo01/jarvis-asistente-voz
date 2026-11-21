"""
main.py — Entry point de J.A.R.V.I.S.

Punto de entrada limpio: crea la aplicación Qt y lanza la interfaz.
Todo corre en un solo proceso; audio y brain usan QThreads.
"""

import sys
from PyQt6.QtWidgets import QApplication
from ui.interface import JarvisUI


def main():
    print("[SISTEMA] Iniciando secuencias de arranque de J.A.R.V.I.S...")
    
    app = QApplication(sys.argv)
    window = JarvisUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()