"""
ui/widgets.py — Componentes auxiliares reutilizables de la UI.

Extraídos de interface.py para modularidad:
- DynamicStatusButton: Botón de estado animado
- ZonaDrop: Zona de arrastrar archivos
- PanelConfiguracion: Diálogo de configuración .env
"""

import os

from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QFileDialog, QDialog,
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont
from PyQt6.QtCore import Qt, QTimer, QRectF

from core import config


# ─── BOTÓN DE ESTADO DINÁMICO ──────────────────────────────────────

class DynamicStatusButton(QPushButton):
    """Botón que muestra el estado actual de Jarvis con animación de pulso."""
    
    STATES = {
        "EN_ESPERA": {
            "text": "EN ESPERA",
            "color": QColor(0, 243, 255),
            "speed": 0
        },
        "ESCUCHANDO": {
            "text": "ESCUCHANDO...",
            "color": QColor(0, 243, 255),
            "speed": 12
        },
        "PENSANDO": {
            "text": "PENSANDO...",
            "color": QColor(255, 200, 0),
            "speed": 10
        },
        "RESPONDIENDO": {
            "text": "RESPONDIENDO...",
            "color": QColor(50, 255, 150),
            "speed": 5
        },
        "CARGANDO_IA": {
            "text": "INICIALIZANDO...",
            "color": QColor(200, 50, 255),
            "speed": 4
        },
    }
    
    def __init__(self):
        super().__init__()
        self.setFixedSize(220, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.current_state = "EN_ESPERA"
        self.pulse_alpha = 150
        self.pulse_dir = 1
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)
    
    def animate(self):
        speed = self.STATES[self.current_state]["speed"]
        if speed > 0:
            self.pulse_alpha += (self.pulse_dir * speed)
            if self.pulse_alpha > 220:
                self.pulse_alpha, self.pulse_dir = 220, -1
            elif self.pulse_alpha < 40:
                self.pulse_alpha, self.pulse_dir = 40, 1
        else:
            self.pulse_alpha = 150
        self.update()
    
    def set_status(self, state: str):
        if state in self.STATES:
            self.current_state = state
            self.pulse_alpha = 40
            self.pulse_dir = 1
            self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        sd = self.STATES[self.current_state]
        bc = sd["color"]
        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        
        dc = QColor(bc)
        dc.setAlpha(int(self.pulse_alpha))
        
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(QPen(dc, 1.5))
        painter.drawRoundedRect(rect, 18, 18)
        
        painter.setPen(QPen(bc))
        painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"[ {sd['text']} ]")
        
        painter.end()


# ─── ZONA DE ARCHIVOS ──────────────────────────────────────────────

class ZonaDrop(QLabel):
    """Zona drag-and-drop para adjuntar archivos."""
    
    STYLE_NORMAL = (
        "QLabel { border: 1px dashed rgba(0, 243, 255, 0.4); border-radius: 10px; "
        "color: rgba(0, 243, 255, 0.6); font-family: 'Consolas'; font-size: 12px; "
        "padding: 15px; background: rgba(0, 0, 0, 0.2); } "
        "QLabel:hover { border: 1px dashed rgba(0, 243, 255, 0.8); "
        "color: rgba(0, 243, 255, 1); background: rgba(0, 243, 255, 0.05); }"
    )
    STYLE_DRAG = (
        "border: 1px dashed #00f3ff; color: #00f3ff; "
        "background: rgba(0, 243, 255, 0.1); border-radius: 10px; "
        "padding: 15px; font-family: 'Consolas';"
    )
    
    def __init__(self):
        super().__init__("📎 Arrastra un archivo o haz clic para buscar")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(self.STYLE_NORMAL)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet(self.STYLE_DRAG)
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.STYLE_NORMAL)
    
    def dropEvent(self, event):
        self.dragLeaveEvent(event)
        for url in event.mimeData().urls():
            filename = url.toLocalFile().split('/')[-1]
            self.setText(f"📁 Listo: {filename}")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo")
            if archivo:
                self.setText(f"📁 Listo: {archivo.split('/')[-1]}")


# ─── PANEL DE CONFIGURACIÓN ───────────────────────────────────────

class PanelConfiguracion(QDialog):
    """Diálogo frameless para editar la configuración del .env."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(450, 350)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        fondo = QWidget()
        fondo.setStyleSheet(
            "QWidget { background-color: rgba(10, 15, 30, 0.95); "
            "border: 1px solid #00f3ff; border-radius: 15px; } "
            "QLabel { color: #00f3ff; font-family: 'Consolas'; font-size: 13px; "
            "border: none; background: transparent; } "
            "QLineEdit, QComboBox { background: rgba(0,0,0,0.5); color: white; "
            "border: 1px solid rgba(0,243,255,0.3); border-radius: 5px; "
            "padding: 5px; font-family: 'Consolas'; }"
        )
        layout.addWidget(fondo)
        
        form_layout = QFormLayout(fondo)
        form_layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_titulo = QLabel(">> CONFIGURACIÓN DEL CEREBRO (.ENV) <<")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addRow(lbl_titulo)
        
        # Proveedor
        self.combo_proveedor = QComboBox()
        self.combo_proveedor.addItems(["gemini", "deepseek", "local_futuro"])
        self.combo_proveedor.setCurrentText(config.get_active_provider())
        form_layout.addRow("PROVEEDOR ACTIVO:", self.combo_proveedor)
        
        # Gemini
        self.combo_gemini = QComboBox()
        self.combo_gemini.addItems(["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"])
        self.combo_gemini.setCurrentText(config.get_gemini_model())
        self.input_gemini_key = QLineEdit(config.get_gemini_api_key())
        self.input_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("MOD. GEMINI:", self.combo_gemini)
        form_layout.addRow("KEY GEMINI:", self.input_gemini_key)
        
        # DeepSeek
        self.combo_deepseek = QComboBox()
        self.combo_deepseek.addItems(["deepseek-chat", "deepseek-coder"])
        self.combo_deepseek.setCurrentText(config.get_deepseek_model())
        self.input_deepseek_key = QLineEdit(config.get_deepseek_api_key())
        self.input_deepseek_key.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("MOD. DEEPSEEK:", self.combo_deepseek)
        form_layout.addRow("KEY DEEPSEEK:", self.input_deepseek_key)
        
        # Botones
        btn_layout = QHBoxLayout()
        
        btn_guardar = QPushButton("GUARDAR EN .ENV")
        btn_guardar.setStyleSheet(
            "QPushButton { background: rgba(0,243,255,0.2); color: #00f3ff; "
            "border: 1px solid #00f3ff; border-radius: 5px; padding: 8px; "
            "font-family: 'Consolas'; } "
            "QPushButton:hover { background: rgba(0,243,255,0.4); }"
        )
        btn_guardar.clicked.connect(self._guardar)
        
        btn_cerrar = QPushButton("CANCELAR")
        btn_cerrar.setStyleSheet(
            "QPushButton { background: rgba(255,0,0,0.2); color: red; "
            "border: 1px solid red; border-radius: 5px; padding: 8px; "
            "font-family: 'Consolas'; }"
        )
        btn_cerrar.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_cerrar)
        btn_layout.addWidget(btn_guardar)
        form_layout.addRow(btn_layout)
    
    def _guardar(self):
        """Guarda la configuración en .env y recarga."""
        config.set("PROVEEDOR_ACTIVO", self.combo_proveedor.currentText())
        config.set("GEMINI_MODELO", self.combo_gemini.currentText())
        config.set("GEMINI_API_KEY", self.input_gemini_key.text())
        config.set("DEEPSEEK_MODELO", self.combo_deepseek.currentText())
        config.set("DEEPSEEK_API_KEY", self.input_deepseek_key.text())
        config.reload()
        self.accept()
