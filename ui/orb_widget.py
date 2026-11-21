"""
ui/orb_widget.py — Esfera holográfica reactiva a la voz.

La esfera responde dinámicamente:
- ESCUCHANDO: se expande/comprime con el volumen de la voz
- RESPONDIENDO: pulsa con cada fragmento de respuesta de Gemini
- PENSANDO: gira rápido con color dorado
- EN_ESPERA: respiración suave y sutil

Extraída de interface.py para modularidad y escalabilidad.
"""

import math
import random
import time

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QBrush, QRadialGradient, QPen
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF


class Point3D:
    """Punto en espacio 3D para la superficie de la esfera."""
    __slots__ = ('x', 'y', 'z')
    
    def __init__(self, x: float, y: float, z: float):
        self.x, self.y, self.z = x, y, z


class HolographicOrb(QWidget):
    """
    Widget de esfera holográfica 3D con partículas y glow dinámico.
    
    La esfera vive en su propio widget independiente de la lógica de
    negocio. Se controla externamente vía set_state() y set_audio_volume().
    """
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 300)
        
        # Rotación
        self.angle_y = 0.0
        self.angle_x = 0.0
        
        # Partículas en la superficie
        self.points = []
        self.num_points = 1500
        
        # Estado y dimensiones
        self.current_state = "EN_ESPERA"
        self.base_radius = 160.0
        self.current_radius = 160.0
        self.target_radius = 160.0
        
        # Color actual (interpolado)
        self.color_rgb = [0.0, 243.0, 255.0]
        
        # Volumen actual (normalizado 0-1)
        self._current_volume = 0.0
        self._target_volume = 0.0
        
        # Respiración en espera
        self._breath_phase = 0.0
        
        # Pulso de respuesta
        self._response_pulse = 0.0
        self._response_pulse_decay = 0.95
        
        # Glow central
        self._glow_intensity = 0.0
        self._target_glow = 0.2
        
        # Micro-vibración
        self._vibration_offset_x = 0.0
        self._vibration_offset_y = 0.0
        
        self.generate_points()
        
        # Timer de animación: ~60 FPS
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)

    def set_state(self, state: str):
        """Cambia el estado visual de la esfera."""
        self.current_state = state

    def set_audio_volume(self, volumen: float):
        """
        Recibe volumen normalizado (0.0 - 1.0).
        Se usa durante ESCUCHANDO para modular el radio.
        """
        self._target_volume = volumen

    def trigger_response_pulse(self):
        """
        Dispara un pulso de expansión durante RESPONDIENDO.
        Llamar con cada chunk de texto que llega de Gemini.
        """
        self._response_pulse = 1.0

    def generate_points(self):
        """Genera puntos uniformemente distribuidos en una esfera unitaria."""
        self.points.clear()
        for _ in range(self.num_points):
            # Distribución uniforme usando Fibonacci
            phi = math.acos(1 - 2 * random.random())
            theta = 2 * math.pi * random.random()
            self.points.append(Point3D(
                math.sin(phi) * math.cos(theta),
                math.sin(phi) * math.sin(theta),
                math.cos(phi)
            ))

    def animate(self):
        """Frame de animación. Interpola radio, color, y rotación según estado."""
        target_color = [0.0, 243.0, 255.0]  # Cyan por defecto
        
        if self.current_state == "EN_ESPERA":
            # Respiración suave: oscilación sinusoidal lenta ±5px
            self._breath_phase += 0.02
            self.target_radius = self.base_radius + math.sin(self._breath_phase) * 5
            self.angle_y += 0.008
            self.angle_x += 0.004
            self._target_glow = 0.15 + math.sin(self._breath_phase) * 0.05
            target_color = [0.0, 243.0, 255.0]
            
        elif self.current_state == "CARGANDO_IA":
            # Carga: rotación media, púrpura
            self.angle_y += 0.005
            self.angle_x += 0.002
            self.target_radius = self.base_radius
            self._target_glow = 0.3
            target_color = [200.0, 50.0, 255.0]
            
        elif self.current_state == "ESCUCHANDO":
            # Radio controlado por volumen de voz
            # Expansión proporcional al volumen (0-45px extra)
            expansion = self._current_volume * 45.0
            self.target_radius = self.base_radius + expansion
            
            # Rotación lenta para no distraer
            self.angle_y += 0.003
            self.angle_x += 0.001
            
            # Glow proporcional al volumen
            self._target_glow = 0.2 + self._current_volume * 0.5
            
            # Micro-vibraciones proporcionales al volumen
            vibration_strength = self._current_volume * 2.0
            self._vibration_offset_x = random.gauss(0, vibration_strength)
            self._vibration_offset_y = random.gauss(0, vibration_strength)
            
            target_color = [0.0, 243.0, 255.0]
            
        elif self.current_state == "PENSANDO":
            # Rotación rápida, dorado, radio base
            self.angle_y += 0.04
            self.angle_x += 0.02
            self.target_radius = self.base_radius - 5  # Ligeramente contraída
            self._target_glow = 0.4
            target_color = [255.0, 200.0, 0.0]
            
        elif self.current_state == "RESPONDIENDO":
            # Pulso con cada chunk de respuesta
            pulse_expansion = self._response_pulse * 20.0
            self.target_radius = self.base_radius + pulse_expansion + math.sin(time.time() * 3) * 4
            self._response_pulse *= self._response_pulse_decay
            
            self.angle_y += 0.012
            self.angle_x += 0.008
            self._target_glow = 0.35 + self._response_pulse * 0.3
            target_color = [50.0, 255.0, 150.0]
        
        # ─── Interpolaciones suaves ─────────────────────────────
        
        # Radio: interpolación rápida para reactividad
        self.current_radius += (self.target_radius - self.current_radius) * 0.35
        
        # Volumen: interpolación rápida
        self._current_volume += (self._target_volume - self._current_volume) * 0.4
        
        # Color: interpolación suave
        for i in range(3):
            self.color_rgb[i] += (target_color[i] - self.color_rgb[i]) * 0.08
        
        # Glow: interpolación media
        self._glow_intensity += (self._target_glow - self._glow_intensity) * 0.1
        
        # Decay de vibraciones cuando no estamos escuchando
        if self.current_state != "ESCUCHANDO":
            self._vibration_offset_x *= 0.8
            self._vibration_offset_y *= 0.8
        
        self.update()

    def project(self, point: Point3D, width: float, height: float):
        """Proyecta un punto 3D al plano 2D con perspectiva."""
        # Rotación Y
        ry = point.x * math.cos(self.angle_y) - point.z * math.sin(self.angle_y)
        rz = point.x * math.sin(self.angle_y) + point.z * math.cos(self.angle_y)
        rx = point.y
        
        # Rotación X
        rx_final = rx * math.cos(self.angle_x) - rz * math.sin(self.angle_x)
        rz_final = rx * math.sin(self.angle_x) + rz * math.cos(self.angle_x)
        
        # Escalar al radio actual
        px_3d = ry * self.current_radius
        py_3d = rx_final * self.current_radius
        pz_3d = rz_final * self.current_radius
        
        # Perspectiva
        factor = 600 / (pz_3d + 600)
        
        # Aplicar micro-vibraciones al centro
        cx = (width / 2) + self._vibration_offset_x
        cy = (height / 2) + self._vibration_offset_y
        
        return (
            px_3d * factor + cx,
            py_3d * factor + cy,
            (pz_3d + self.base_radius) / (2 * self.base_radius)
        )

    def paintEvent(self, event):
        """Renderiza la esfera con partículas, glow central, y anillos."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        cr = int(self.color_rgb[0])
        cg = int(self.color_rgb[1])
        cb = int(self.color_rgb[2])
        
        # ─── Glow central difuso ─────────────────────────────
        glow_radius = self.current_radius * 1.8
        glow_alpha = int(self._glow_intensity * 120)
        cx = w / 2 + self._vibration_offset_x
        cy = h / 2 + self._vibration_offset_y
        
        central_glow = QRadialGradient(QPointF(cx, cy), glow_radius)
        central_glow.setColorAt(0, QColor(cr, cg, cb, glow_alpha))
        central_glow.setColorAt(0.4, QColor(cr, cg, cb, int(glow_alpha * 0.3)))
        central_glow.setColorAt(1, QColor(cr, cg, cb, 0))
        
        painter.setBrush(QBrush(central_glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(
            cx - glow_radius, cy - glow_radius,
            glow_radius * 2, glow_radius * 2
        ))
        
        # ─── Anillo orbital (visible durante estados activos) ──
        if self.current_state in ("ESCUCHANDO", "RESPONDIENDO", "PENSANDO"):
            ring_alpha = int(40 + self._current_volume * 60)
            ring_pen = QPen(QColor(cr, cg, cb, ring_alpha), 1.0)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            ring_r = self.current_radius * 1.15
            painter.drawEllipse(QRectF(
                cx - ring_r, cy - ring_r * 0.3,
                ring_r * 2, ring_r * 0.6
            ))
        
        # ─── Partículas de superficie ─────────────────────────
        projected = []
        for pt in self.points:
            px, py, z = self.project(pt, w, h)
            projected.append((px, py, z))
        
        # Ordenar por profundidad (lejanas primero)
        projected.sort(key=lambda x: x[2])
        
        for px, py, z in projected:
            size = 1.5 + (z * 3.5)
            alpha = int(20 + (z * 235))
            
            color = QColor(cr, cg, cb, alpha)
            rect = QRectF(px - size / 2, py - size / 2, size, size)
            
            # Glow individual para partículas cercanas
            if z > 0.75:
                glow_size = size * 2.5
                glow = QRadialGradient(QPointF(px, py), glow_size)
                glow.setColorAt(0, QColor(cr, cg, cb, int(alpha * 0.35)))
                glow.setColorAt(1, QColor(cr, cg, cb, 0))
                painter.setBrush(QBrush(glow))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QRectF(
                    px - glow_size, py - glow_size,
                    glow_size * 2, glow_size * 2
                ))
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect)
        
        painter.end()
