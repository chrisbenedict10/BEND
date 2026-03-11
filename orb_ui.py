import sys
import math
import random
import time
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QSize
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QBrush, QPen, QPainterPath, QLinearGradient

from state_manager import state_manager, OrbState
from audio_listener import audio_listener

# UI Configuration
WINDOW_SIZE = 300
ORB_BASE_RADIUS = 50
FPS = 60

class OrbWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(WINDOW_SIZE, WINDOW_SIZE)
        
        # State-based animation properties
        self._rotation_angle = 0.0
        self._pulse_factor = 1.0
        self._target_radius = float(ORB_BASE_RADIUS)
        self._current_radius = float(ORB_BASE_RADIUS)
        
        # Smoothing helpers
        self._last_amp = 0.0
        self._phase = 0.0
        
        # Performance: Pre-calculate wave offsets
        self._wave_offsets = [random.uniform(0, 2 * math.pi) for _ in range(5)]
        
        # Timer for ~60 FPS animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000 // FPS)

    def paintEvent(self, event):
        """Main rendering loop with high-fidelity visuals."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # DEBUG: Uncomment the line below to see the window bounds
        # painter.fillRect(self.rect(), QColor(255, 0, 0, 20)) 
        
        # Get current data from state manager
        state = state_manager.current_state
        amp = state_manager.amplitude
        
        # Smooth the amplitude (exponential smoothing)
        self._last_amp = (self._last_amp * 0.7) + (amp * 0.3)
        
        # Center of drawing
        cx, cy = WINDOW_SIZE // 2, WINDOW_SIZE // 2
        
        # 1. Update Core Pulse logic
        self._update_animation_params(state)
        
        # 2. Draw based on State
        if state == OrbState.PROCESSING:
            self._draw_processing_nebula(painter, cx, cy, self._current_radius)
        elif state == OrbState.SPEAKING:
            self._draw_waveform_orb(painter, cx, cy, self._current_radius)
        elif state == OrbState.LISTENING:
            self._draw_listening_orb(painter, cx, cy, self._current_radius)
        else:
            # IDLE
            self._draw_idle_orb(painter, cx, cy, self._current_radius)

    def _update_animation_params(self, state):
        """Calculate dynamic radius and phase transitions."""
        t = time.time()
        
        if state == OrbState.IDLE:
            # Slow breathing pulse
            idle_pulse = (math.sin(t * 1.5) + 1.0) / 2.0 
            self._target_radius = ORB_BASE_RADIUS + (idle_pulse * 12.0)
        elif state == OrbState.LISTENING:
            # React directly to mic
            self._target_radius = ORB_BASE_RADIUS + (self._last_amp * 100.0)
        elif state == OrbState.PROCESSING:
            # Small, tight core for processing
            self._target_radius = ORB_BASE_RADIUS * 0.9 + (math.sin(t * 10.0) * 5.0)
        elif state == OrbState.SPEAKING:
            # Sync with speaking volume
            self._target_radius = ORB_BASE_RADIUS + (self._last_amp * 80.0)

        # Smooth radius transition (Lerp)
        self._current_radius = (self._current_radius * 0.8) + (self._target_radius * 0.2)
        self._phase += 0.08

    def _draw_glow_circle(self, painter, cx, cy, radius, color_start, color_end=QColor(0,0,0,0)):
        """Helper to draw a soft glowing radial gradient."""
        gradient = QRadialGradient(float(cx), float(cy), float(radius))
        gradient.setColorAt(0.0, color_start)
        gradient.setColorAt(1.0, color_end)
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

    def _draw_idle_orb(self, painter, cx, cy, radius):
        """Elegant, layered breathing orb with multiple color blobs."""
        t = time.time()
        
        # Large faint blue outer glow (increased alpha)
        self._draw_glow_circle(painter, cx, cy, radius * 2.2, QColor(0, 120, 255, 60))
        
        # Purple moving blob
        px = cx + math.cos(t * 0.8) * 15
        py = cy + math.sin(t * 0.7) * 15
        self._draw_glow_circle(painter, px, py, radius * 1.6, QColor(147, 51, 234, 100))
        
        # Cyan core blob
        cx2 = cx + math.sin(t * 1.2) * 10
        cy2 = cy + math.cos(t * 1.1) * 10
        self._draw_glow_circle(painter, cx2, cy2, radius * 1.3, QColor(6, 182, 212, 140))
        
        # Bright white center core (High visibility)
        self._draw_glow_circle(painter, cx, cy, radius * 0.6, QColor(255, 255, 255, 255))

    def _draw_listening_orb(self, painter, cx, cy, radius):
        """Aggressive, reactive orb for listening state."""
        t = time.time()
        # Reactive outer rim (pulsing with mic)
        glow_size = radius * (1.5 + self._last_amp)
        self._draw_glow_circle(painter, cx, cy, glow_size, QColor(255, 0, 128, 40))
        
        # Core layers
        self._draw_glow_circle(painter, cx, cy, radius * 1.2, QColor(150, 0, 255, 80))
        self._draw_glow_circle(painter, cx, cy, radius * 0.8, QColor(255, 255, 255, 220))
        
        # Add subtle wave rings
        for i in range(3):
            ring_r = (radius + (i * 20) + (t * 50) % 60)
            alpha = max(0, 150 - int((ring_r / (radius * 3)) * 150))
            if alpha > 0:
                pen = QPen(QColor(255, 255, 255, alpha))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(int(cx - ring_r), int(cy - ring_r), int(ring_r * 2), int(ring_r * 2))

    def _draw_processing_nebula(self, painter, cx, cy, radius):
        """Rotating multi-colored color shift (Processing state)."""
        self._rotation_angle = (self._rotation_angle + 6) % 360
        t = time.time()
        
        colors = [
            QColor(255, 59, 48, 150),  # Red
            QColor(0, 122, 255, 150),  # Blue
            QColor(175, 82, 222, 150), # Purple
            QColor(90, 200, 250, 150)  # Cyan
        ]
        
        # Draw rotating blobs
        for i, color in enumerate(colors):
            angle = math.radians(self._rotation_angle + (i * 90))
            dist = radius * 0.5
            bx = cx + math.cos(angle) * dist
            by = cy + math.sin(angle) * dist
            self._draw_glow_circle(painter, bx, by, radius * 1.2, color)
            
        # Central white star
        self._draw_glow_circle(painter, cx, cy, radius * 0.4, QColor(255, 255, 255, 220))

    def _draw_waveform_orb(self, painter, cx, cy, radius):
        """High-fidelity Siri-style multi-layered wave logic."""
        t = time.time()
        
        # Base glow
        self._draw_idle_orb(painter, cx, cy, radius * 0.8)
        
        # Wave configurations: (color, freq, speed, height, width)
        waves = [
            (QColor(255, 255, 255, 220), 0.04, 2.5, 45, 3),
            (QColor(0, 255, 255, 140), 0.03, 1.8, 35, 2),
            (QColor(255, 50, 150, 140), 0.05, 3.2, 40, 2),
            (QColor(150, 50, 255, 100), 0.02, 1.2, 25, 2)
        ]
        
        for i, (color, freq, speed, height, width) in enumerate(waves):
            pen = QPen(color)
            pen.setWidth(width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            
            path = QPainterPath()
            amp_scale = (self._last_amp * height) + (5.0 if state_manager.current_state == OrbState.SPEAKING else 0)
            
            # Draw wave centered horizontally
            w_len = 160
            start_x = cx - (w_len // 2)
            path.moveTo(float(start_x), float(cy))
            
            for x in range(0, w_len + 1, 4):
                # Sine wave with bell-curve envelope for tapering
                env = math.exp(-pow((x - w_len/2) / (w_len/3), 2)) # Gaussian envelope
                y = math.sin(x * freq + self._phase * speed + self._wave_offsets[i]) * amp_scale * env
                path.lineTo(float(start_x + x), float(cy + y))
            
            painter.drawPath(path)

class OrbWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowOpacity(1.0)
        
        self.orb_widget = OrbWidget()
        self.setCentralWidget(self.orb_widget)
        self.setFixedSize(WINDOW_SIZE, WINDOW_SIZE)
        
        # Position at the center bottom of screen, safely above the taskbar
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            pos_x = screen_geo.x() + (screen_geo.width() - WINDOW_SIZE) // 2
            pos_y = screen_geo.y() + screen_geo.height() - WINDOW_SIZE - 10
            self.move(int(pos_x), int(pos_y))
            print(f"🌟 Orb UI positioned at ({pos_x}, {pos_y}) on {screen.name()}.")
        
        self.show()
        self.raise_()

def launch_demo():
    """Standalone launcher for the demo."""
    app = QApplication(sys.argv)
    
    # Start audio capture
    audio_listener.start()
    
    window = OrbWindow()
    window.show()
    
    print("✨ Orb UI Launched. Say something to see it react!")
    print("Press Ctrl+C in terminal or exit window to quit.")
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        audio_listener.stop()

if __name__ == "__main__":
    launch_demo()
