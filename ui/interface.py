"""
ui/interface.py — Ventana principal de JARVIS.

Solo se encarga de:
1. Ensamblar los widgets (esfera, status, input, drop zone)
2. Conectar señales entre AudioWorker, BrainWorker y la UI
3. Controles de ventana (arrastrar, minimizar, fullscreen)

NO contiene lógica de negocio — eso vive en brain/router.py.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLineEdit, QPushButton, QSizeGrip
)
from PyQt6.QtCore import Qt, QPoint, QThread, pyqtSignal

from audio.stt import JarvisEars
from brain.router import BrainWorker
from ui.orb_widget import HolographicOrb
from ui.widgets import DynamicStatusButton, ZonaDrop, PanelConfiguracion


# ─── AUDIO WORKER (hilo dedicado para STT) ────────────────────────

class AudioWorker(QThread):
    """Worker thread que ejecuta el bucle de escucha del micrófono."""
    senal_estado = pyqtSignal(str)
    senal_comando = pyqtSignal(str)
    senal_volumen = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.oidos = None

    def run(self):
        self.senal_estado.emit("CARGANDO_IA")
        self.oidos = JarvisEars()

        print("[UI] Conectando nervios auditivos al hilo principal...")
        self.oidos.escuchar_continuamente(
            callback_estado=lambda estado: self.senal_estado.emit(estado),
            callback_comando=lambda cmd: self.senal_comando.emit(cmd),
            callback_volumen=lambda vol: self.senal_volumen.emit(vol),
        )

    def stop(self):
        if self.oidos:
            self.oidos.detener()
        if self.isRunning():
            self.quit()
            self.wait(3000)
            if self.isRunning():
                self.terminate()
                self.wait()


# ─── VENTANA PRINCIPAL ────────────────────────────────────────────

class JarvisUI(QMainWindow):
    """
    Ventana principal de JARVIS.
    
    Ensambla la esfera holográfica, los controles de estado,
    y coordina AudioWorker ↔ BrainWorker ↔ Orb.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.drag_position = QPoint()
        self.is_mini = False
        self._respondiendo = False
        self._respuesta_buffer = []
        
        self._init_ui()
        self._init_brain()
        self._init_audio()
    
    # ─── Inicialización ──────────────────────────────────────
    
    def _init_ui(self):
        """Construye toda la interfaz gráfica."""
        self.resize(800, 750)
        
        self.main_widget = QWidget()
        self.main_widget.setObjectName("Main")
        self.main_widget.setStyleSheet(
            "QWidget#Main { "
            "background-color: qradialgradient("
            "cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, "
            "stop:0 #050811, stop:1 #010205); "
            "border: 1px solid rgba(0, 243, 255, 0.2); "
            "border-radius: 20px; }"
        )
        self.setCentralWidget(self.main_widget)
        
        self.layout = QVBoxLayout(self.main_widget)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # ── Barra superior ────────────────────────────────
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(10, 0, 10, 0)
        
        estilo_btn_ctrl = (
            "QPushButton { color: rgba(0, 243, 255, 0.4); border: none; "
            "background: transparent; font-size: 16px; } "
            "QPushButton:hover { color: #00f3ff; }"
        )
        
        self.btn_ajustes = QPushButton("⚙")
        self.btn_ajustes.setStyleSheet(estilo_btn_ctrl)
        self.btn_ajustes.clicked.connect(self._abrir_configuracion)
        top_layout.addWidget(self.btn_ajustes)
        top_layout.addStretch()
        
        win_ctrl_layout = QHBoxLayout()
        win_ctrl_layout.setSpacing(20)
        
        self.btn_toggle_mini = QPushButton("◉")
        self.btn_toggle_mini.setStyleSheet(estilo_btn_ctrl)
        self.btn_toggle_mini.clicked.connect(self._toggle_modo_mini)
        win_ctrl_layout.addWidget(self.btn_toggle_mini)
        
        self.btn_toggle_full = QPushButton("⛶")
        self.btn_toggle_full.setStyleSheet(estilo_btn_ctrl)
        self.btn_toggle_full.clicked.connect(self._toggle_pantalla_completa)
        win_ctrl_layout.addWidget(self.btn_toggle_full)
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setStyleSheet(
            "QPushButton { color: rgba(0, 243, 255, 0.2); border: none; "
            "background: transparent; font-size: 16px; } "
            "QPushButton:hover { color: red; }"
        )
        self.btn_close.clicked.connect(self.close)
        win_ctrl_layout.addWidget(self.btn_close)
        
        top_layout.addLayout(win_ctrl_layout)
        self.layout.addLayout(top_layout)
        
        # ── Esfera holográfica ────────────────────────────
        self.orb = HolographicOrb()
        self.layout.addWidget(self.orb, stretch=1)
        
        # ── Botón de estado ───────────────────────────────
        status_layout = QHBoxLayout()
        self.status_btn = DynamicStatusButton()
        status_layout.addStretch()
        status_layout.addWidget(self.status_btn)
        status_layout.addStretch()
        self.layout.addLayout(status_layout)
        
        # ── Zona de archivos ──────────────────────────────
        self.drop_zone = ZonaDrop()
        drop_layout = QHBoxLayout()
        drop_layout.setContentsMargins(50, 10, 50, 10)
        drop_layout.addWidget(self.drop_zone)
        self.layout.addLayout(drop_layout)
        
        # ── Campo de texto ────────────────────────────────
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Escuchando...")
        self.input_field.setStyleSheet(
            "QLineEdit { background: rgba(0, 0, 0, 0.3); "
            "border: 1px solid rgba(0, 243, 255, 0.15); "
            "border-radius: 15px; padding: 10px; color: #00f3ff; "
            "font-family: 'Consolas', monospace; font-size: 14px; "
            "text-align: center; } "
            "QLineEdit:focus { background: rgba(0, 0, 0, 0.6); "
            "border: 1px solid rgba(0, 243, 255, 0.5); }"
        )
        self.input_field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_field.setReadOnly(True)
        
        input_container = QHBoxLayout()
        input_container.setContentsMargins(50, 0, 50, 0)
        input_container.addWidget(self.input_field)
        self.layout.addLayout(input_container)
        
        # ── Grip de redimensionado ────────────────────────
        bottom_corner = QHBoxLayout()
        bottom_corner.addStretch()
        grip = QSizeGrip(self)
        grip.setFixedSize(15, 15)
        grip.setStyleSheet("background: transparent;")
        bottom_corner.addWidget(grip)
        self.layout.addLayout(bottom_corner)
    
    def _init_brain(self):
        """Inicializa el BrainWorker para procesar comandos con Gemini."""
        self.brain = BrainWorker()
        self.brain.senal_pensando.connect(self._on_brain_pensando)
        self.brain.senal_chunk.connect(self._on_brain_chunk)
        self.brain.senal_respuesta_completa.connect(self._on_brain_respuesta_completa)
        self.brain.senal_comando_local.connect(self._on_comando_local)
        self.brain.senal_error.connect(self._on_brain_error)
    
    def _init_audio(self):
        """Inicializa el AudioWorker para escucha por micrófono."""
        self.hilo_audio = AudioWorker()
        self.hilo_audio.senal_estado.connect(self._on_estado_audio)
        self.hilo_audio.senal_comando.connect(self._on_comando_voz)
        self.hilo_audio.senal_volumen.connect(self._on_volumen)
        self.hilo_audio.start()
    
    # ─── Handlers de Audio ──────────────────────────────────
    
    def _on_estado_audio(self, nuevo_estado: str):
        """El STT cambió de estado (EN_ESPERA, ESCUCHANDO, PENSANDO)."""
        # No interrumpir si estamos en medio de una respuesta de Gemini
        if self._respondiendo and nuevo_estado in ("EN_ESPERA", "ESCUCHANDO"):
            return
        self.status_btn.set_status(nuevo_estado)
        self.orb.set_state(nuevo_estado)
    
    def _on_comando_voz(self, texto: str):
        """El STT transcribió un comando de voz."""
        self.input_field.setText(f"🎤 {texto}")
        # Enviar al brain para procesamiento
        self.brain.procesar(texto)
    
    def _on_volumen(self, volumen: float):
        """Volumen normalizado del micrófono (0.0 - 1.0)."""
        self.orb.set_audio_volume(volumen)
    
    # ─── Handlers del Brain ─────────────────────────────────
    
    def _on_brain_pensando(self):
        """Gemini está procesando."""
        self._respondiendo = True
        self._respuesta_buffer = []
        self.status_btn.set_status("PENSANDO")
        self.orb.set_state("PENSANDO")
    
    def _on_brain_chunk(self, chunk: str):
        """Llegó un fragmento de respuesta de Gemini (streaming)."""
        # Cambiar a estado respondiendo al primer chunk
        if self.orb.current_state != "RESPONDIENDO":
            self.status_btn.set_status("RESPONDIENDO")
            self.orb.set_state("RESPONDIENDO")
        
        self._respuesta_buffer.append(chunk)
        
        # Mostrar respuesta progresivamente en el input field
        texto_actual = "".join(self._respuesta_buffer)
        # Truncar para que quepa en el campo visual
        if len(texto_actual) > 120:
            self.input_field.setText(f"💬 ...{texto_actual[-117:]}")
        else:
            self.input_field.setText(f"💬 {texto_actual}")
        
        # Pulsar la esfera con cada chunk
        self.orb.trigger_response_pulse()
    
    def _on_brain_respuesta_completa(self, respuesta: str):
        """Gemini terminó de responder."""
        self._respondiendo = False
        
        # Mostrar respuesta final
        if len(respuesta) > 120:
            self.input_field.setText(f"💬 {respuesta[:117]}...")
        else:
            self.input_field.setText(f"💬 {respuesta}")
        
        print(f"[JARVIS]: {respuesta}")
        
        # Volver a estado de espera
        self.status_btn.set_status("EN_ESPERA")
        self.orb.set_state("EN_ESPERA")
    
    def _on_brain_error(self, error: str):
        """Error del brain."""
        self._respondiendo = False
        self.input_field.setText(f"⚠ {error}")
        self.status_btn.set_status("EN_ESPERA")
        self.orb.set_state("EN_ESPERA")
    
    def _on_comando_local(self, comando: str):
        """El brain detectó un comando local (no necesita LLM)."""
        if comando == "MODO_MINI":
            self._modo_mini()
        elif comando == "MODO_FULLSCREEN":
            self._toggle_pantalla_completa()
        elif comando == "MODO_NORMAL":
            self._modo_normal()
        elif comando == "CERRAR":
            self.close()
    
    # ─── Configuración ──────────────────────────────────────
    
    def _abrir_configuracion(self):
        """Abre el panel de configuración y reconfigura Gemini si se guardó."""
        dialog = PanelConfiguracion(self)
        if dialog.exec():
            # Si se guardó la config, reconfigurar Gemini
            self.brain.reconfigurar_gemini()
            self.input_field.setText("✅ Configuración guardada")
    
    # ─── Modos de ventana ───────────────────────────────────
    
    def _toggle_modo_mini(self):
        if self.isFullScreen():
            self.showNormal()
            self._actualizar_iconos_normales()
        if self.is_mini:
            self._modo_normal()
        else:
            self._modo_mini()
    
    def _toggle_pantalla_completa(self):
        if self.is_mini:
            self._modo_normal()
        if self.isFullScreen():
            self._modo_normal()
        else:
            self._modo_normal()
            self.showFullScreen()
            self.btn_toggle_full.setText("❐")
            self.btn_toggle_full.setToolTip("Restaurar Ventana")
            self.is_mini = False
    
    def _modo_mini(self):
        self.showNormal()
        self.orb.hide()
        self.drop_zone.hide()
        self.input_field.hide()
        self.btn_toggle_full.hide()
        self.setFixedSize(280, 110)
        self.btn_toggle_mini.setText("❐")
        self.is_mini = True
    
    def _modo_normal(self):
        self.showNormal()
        self.setMinimumSize(400, 500)
        self.setMaximumSize(16777215, 16777215)
        self.resize(800, 750)
        self.orb.show()
        self.drop_zone.show()
        self.input_field.show()
        self.btn_toggle_full.show()
        self._actualizar_iconos_normales()
        self.is_mini = False
    
    def _actualizar_iconos_normales(self):
        self.btn_toggle_mini.setText("◉")
        self.btn_toggle_full.setText("⛶")
    
    # ─── Drag de ventana ────────────────────────────────────
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.isFullScreen():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    # ─── Cierre limpio ──────────────────────────────────────
    
    def closeEvent(self, event):
        print("[UI] Apagando receptores auditivos...")
        if hasattr(self, 'hilo_audio'):
            self.hilo_audio.stop()
        event.accept()


# ─── Standalone execution ──────────────────────────────────────────

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = JarvisUI()
    ex.show()
    sys.exit(app.exec())