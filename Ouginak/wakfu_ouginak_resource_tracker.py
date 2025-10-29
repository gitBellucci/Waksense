#!/usr/bin/env python3
"""
Wakfu Ouginak Class Resource Tracker - Full Screen Overlay System
Tracks Ouginak resources in real-time from chat logs
"""

import sys
import threading
import time
import re
import math
import json
from pathlib import Path
import platform

# Ajouter le dossier parent au path pour importer log_deduplicator
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from log_deduplicator import LogDeduplicator
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QFrame, QMenu, QGraphicsOpacityEffect, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QPoint, QRect
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QLinearGradient, QBrush, QPixmap, QPen, QAction, QPainterPath, QImage

# Windows-specific imports for window detection
try:
    import win32gui
    import win32process
    WINDOWS_DETECTION_AVAILABLE = True
except ImportError:
    WINDOWS_DETECTION_AVAILABLE = False
    print("DEBUG: win32gui not available, window detection disabled")

class LogMonitorThread(QThread):
    """Thread for monitoring log file with deduplication"""
    log_updated = pyqtSignal(str)
    
    def __init__(self, log_file_path, enable_deduplication=True):
        super().__init__()
        self.log_file = Path(log_file_path)
        self.monitoring = True
        self.last_position = 0
        
        # Système de déduplication
        self.enable_deduplication = enable_deduplication
        if enable_deduplication:
            self.deduplicator = LogDeduplicator(duplicate_window_ms=100)
            self.deduplicator.set_debug_mode(True)
            print("DEBUG: Déduplication activée pour le tracker Ouginak avec debug")
        else:
            self.deduplicator = None
            print("DEBUG: Déduplication désactivée pour le tracker Ouginak")
        
        # Initialize position to end of file to ignore existing content
        self.initialize_position_to_end()
    
    def initialize_position_to_end(self):
        """Set the file position to the end to ignore existing content"""
        try:
            if self.log_file.exists():
                with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(0, 2)  # Seek to end of file
                    self.last_position = f.tell()
                print(f"DEBUG: Log monitor initialized at position {self.last_position} (end of file)")
            else:
                print("DEBUG: Log file doesn't exist yet, will start from beginning when created")
        except Exception as e:
            print(f"DEBUG: Error initializing log position: {e}")
            self.last_position = 0
        
    def run(self):
        """Monitor log file for changes"""
        consecutive_errors = 0
        max_errors = 5
        
        while self.monitoring:
            try:
                if self.log_file.exists():
                    with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(self.last_position)
                        new_lines = f.readlines()
                        self.last_position = f.tell()
                        
                        if new_lines:
                            for line in new_lines:
                                line = line.strip()
                                if line:
                                    # Vérifier la déduplication si activée
                                    if self.enable_deduplication and self.deduplicator:
                                        if not self.deduplicator.should_process_line(line):
                                            continue  # Ignorer les doublons
                                    
                                    # Traiter la ligne normalement
                                    self.log_updated.emit(line)
                            
                            consecutive_errors = 0
                        else:
                            time.sleep(0.1)
                else:
                    time.sleep(1)
                    consecutive_errors = 0
                
            except Exception as e:
                consecutive_errors += 1
                print(f"Error monitoring log file: {e}")
                
                if consecutive_errors >= max_errors:
                    print(f"Too many consecutive errors, stopping monitoring")
                    break
                
                sleep_time = min(1 * (2 ** consecutive_errors), 10)
                time.sleep(sleep_time)
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False

class DraggableIcon(QWidget):
    """Draggable icon widget that can be moved anywhere on screen"""
    
    def __init__(self, icon_path, icon_name, parent=None, icon_size=68):
        # If no parent, make it a top-level window like Cra's precis_icon
        if parent is None:
            super().__init__()
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        else:
            super().__init__(parent)
        
        self.icon_path = icon_path
        self.icon_name = icon_name
        self.drag_position = QPoint()
        self.is_dragging = False
        self.is_locked = False
        self.parent_overlay = None  # Will be set later
        self.icon_size = icon_size
        
        # Setup UI
        self.setup_ui()
        
        # Initially hidden
        self.hide()
    
    def setup_ui(self):
        """Setup the draggable icon"""
        self.setFixedSize(self.icon_size, self.icon_size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Load icon (15% smaller: 64 * 0.85 = ~54)
        if self.icon_path.exists():
            self.icon_label = QLabel()
            pixmap = QPixmap(str(self.icon_path))
            self.icon_label.setPixmap(pixmap.scaled(54, 54, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.icon_label.setFixedSize(54, 54)
            self.icon_label.setStyleSheet("background-color: transparent;")
        else:
            emoji = "🐺"
            self.icon_label = QLabel(emoji)
            self.icon_label.setFixedSize(54, 54)
            self.icon_label.setStyleSheet("""
                QLabel {
                    color: #8B4513;
                    font-size: 40px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)
        self.setStyleSheet("background-color: transparent;")
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.MouseButton.LeftButton and not self.is_locked:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.is_dragging = True
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if self.is_dragging and event.buttons() == Qt.MouseButton.LeftButton and not self.is_locked:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            # Auto-save position when dragging
            if self.parent_overlay and hasattr(self.parent_overlay, 'auto_save_positions'):
                self.parent_overlay.auto_save_positions()
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            event.accept()
    
    def show_context_menu(self, position):
        """Show context menu for lock/unlock"""
        menu = QMenu(self)
        
        lock_action = QAction("🔒 Lock Position" if not self.is_locked else "🔓 Unlock Position", self)
        lock_action.triggered.connect(self.toggle_lock)
        menu.addAction(lock_action)
        
        menu.exec(position)
    
    def toggle_lock(self):
        """Toggle lock state"""
        self.is_locked = not self.is_locked

class OutlinedLabel(QLabel):
    """QLabel with outlined text (white text with black border)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_to_draw = ""
    
    def setText(self, text):
        """Override setText to store text and trigger repaint"""
        self.text_to_draw = text
        super().setText(text)
        self.update()
    
    def get_resource_color(self, text):
        """Get color based on resource type"""
        if "RG" in text:
            return QColor(255, 50, 50)  # Brighter red for Rage (RG) - more visible
        elif "PA" in text:
            return QColor(0, 150, 255)  # Bright blue for PA
        elif "PM" in text:
            return QColor(0, 128, 0)   # Green for PM
        elif "PW" in text:
            return QColor(0, 206, 209) # Turquoise for PW
        else:
            return QColor(255, 255, 255)  # Default white
    
    def paintEvent(self, event):
        """Custom paint event to draw outlined text"""
        if not self.text_to_draw:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Parse text to separate number from resource type
        text = self.text_to_draw
        number_part = ""
        resource_part = ""
        
        # Extract number and resource type (e.g., "1PA" -> "1" and "PA")
        for i, char in enumerate(text):
            if char.isdigit():
                number_part += char
            else:
                resource_part = text[i:]
                break
        
        # Font sizes - make them closer in size for better alignment
        font_size_large = 9  # Larger font for numbers
        font_size_small = 8  # Smaller font for resource types
        font_large = QFont('Segoe UI', font_size_large, QFont.Weight.Bold)
        font_small = QFont('Segoe UI', font_size_small, QFont.Weight.Bold)
        
        # Calculate metrics for both fonts
        painter.setFont(font_large)
        metrics_large = painter.fontMetrics()
        painter.setFont(font_small)
        metrics_small = painter.fontMetrics()
        
        # Calculate total width of the entire text
        number_width = metrics_large.boundingRect(number_part).width() if number_part else 0
        resource_width = metrics_small.boundingRect(resource_part).width() if resource_part else 0
        total_width = number_width + resource_width
        
        # Center the entire text block
        start_x = (self.width() - total_width) // 2
        y = (self.height() + metrics_large.height()) // 2
        
        # Draw number part (larger font)
        if number_part:
            painter.setFont(font_large)
            current_x = start_x
            
            # Draw black outline for number
            painter.setPen(QPen(QColor(0, 0, 0, 255), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx != 0 or dy != 0:
                        painter.drawText(current_x + dx, y + dy, number_part)
            
            # Draw number in white
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(current_x, y, number_part)
        
        # Draw resource part (smaller font) - positioned right after the number with small gap
        if resource_part:
            painter.setFont(font_small)
            # Position resource part right after the number with a small gap for clarity
            resource_x = start_x + number_width + 1  # Add 1 pixel gap
            
            # Draw black outline for resource
            painter.setPen(QPen(QColor(0, 0, 0, 255), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx != 0 or dy != 0:
                        painter.drawText(resource_x + dx, y + dy, resource_part)
            
            # Draw resource part in appropriate color
            resource_color = self.get_resource_color(resource_part)
            painter.setPen(QPen(resource_color, 1))
            painter.drawText(resource_x, y, resource_part)

class OuginakProgressBar(QProgressBar):
    """Custom progress bar for Ouginak resource with animated gradient"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.decimal_value = 0
        self.target_value = 0
        self.smooth_value = 0
        self.smooth_transitions = True
        self.animation_frame = 0
        
        # Separate high-frequency timer for progress bar only
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_animation)
        self.progress_timer.start(16)  # ~60 FPS
        
        # Animation variables for gradient progression
        self.gradient_animation_speed = 0.02
        self.gradient_phase = 0
        
        # Track Ougigarou mode
        self.ougiagou_active = False
        
        # Load animated GIF background (rageeffect.gif)
        self.icon_path = parent.icon_path if parent else Path(__file__).parent / "img"
        self.gif_path = self.icon_path / "rageeffect.gif"
        self.movie = None
        self.load_gif_frames()
        
        self.setFixedHeight(24)
        self.setFixedWidth(250)
        self.setRange(0, 30)  # Rage stacks from 0 to 30
        self.setValue(0)
        
        # Hide default text
        self.setTextVisible(False)
        
        # Styling
        self.setStyleSheet(self.get_minimal_style())
    
    def set_ougiagou_mode(self, active):
        """Enable or disable Ougigarou mode"""
        self.ougiagou_active = active
        if active and self.movie:
            self.movie.start()
        elif not active and self.movie:
            self.movie.stop()
        
    def load_gif_frames(self):
        """Load GIF frames - simplified version using QMovie"""
        try:
            if self.gif_path.exists():
                from PyQt6.QtGui import QMovie
                self.movie = QMovie(str(self.gif_path))
                self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
                self.movie.start()
                print("DEBUG: Loaded GIF successfully")
            else:
                self.movie = None
                print("DEBUG: GIF file not found")
        except Exception as e:
            print(f"DEBUG: Error loading GIF: {e}")
            self.movie = None
    
    def setValue(self, value):
        """Override setValue to handle decimal values"""
        self.target_value = float(value)
        self.is_transitioning = True
        super().setValue(int(self.target_value))
    
    def update_animation(self):
        """Update gradient animation and smooth value transitions"""
        self.animation_frame += 1
        self.gradient_phase += self.gradient_animation_speed
        
        # The QMovie will handle animation automatically
        
        # Smooth value transition
        if self.smooth_transitions:
            self.smooth_value = self.smooth_value + (self.target_value - self.smooth_value) * 0.15
            # If we're very close to target, just snap to it (avoid floating point issues)
            if abs(self.smooth_value - self.target_value) < 0.1:
                self.smooth_value = self.target_value
            self.decimal_value = self.smooth_value
        else:
            self.decimal_value = self.target_value
        
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event with modern animated gradient and text"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate progress percentage (Rage 0-30)
        progress = self.decimal_value / 30.0
        bar_width = int(self.width() * progress)
        radius = 12
        
        # Draw background with rounded corners
        bg_path = QPainterPath()
        bg_path.addRoundedRect(0, 0, self.width(), self.height(), radius, radius)
        
        # Draw GIF background if in Ougigarou mode
        if self.ougiagou_active and self.movie and bar_width > 0:
            current_pixmap = self.movie.currentPixmap()
            if not current_pixmap.isNull():
                # Draw GIF scaled to bar width
                scaled_gif = current_pixmap.scaled(bar_width, self.height(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                gif_path = QPainterPath()
                gif_path.addRoundedRect(0, 0, bar_width, self.height(), radius, radius)
                painter.setClipPath(gif_path)
                painter.drawPixmap(0, 0, scaled_gif)
                painter.setClipping(False)
            else:
                # Default background if GIF not loaded yet
                painter.fillPath(bg_path, QColor(0, 0, 0, 77))
        else:
            # Default dark background
            painter.fillPath(bg_path, QColor(0, 0, 0, 77))
        
        # Draw progress bar with rounded corners
        if bar_width > 0:
            progress_path = QPainterPath()
            progress_path.addRoundedRect(0, 0, bar_width, self.height(), radius, radius)
            
            # Apply gradient overlay on top of GIF (for visibility)
            # Make it more red when in Ougigarou mode
            if self.ougiagou_active:
                gradient_final = QLinearGradient(0, 0, bar_width, 0)
                gradient_final.setColorAt(0, QColor(180, 0, 0, 120))  # Reduced opacity for brighter GIF
                gradient_final.setColorAt(0.5, QColor(255, 60, 60, 120))  # Reduced opacity
                gradient_final.setColorAt(1, QColor(255, 100, 100, 120))  # Reduced opacity
            else:
                gradient_final = QLinearGradient(0, 0, bar_width, 0)
                gradient_final.setColorAt(0, QColor(139, 69, 19, 100))  # Reduced opacity
                gradient_final.setColorAt(0.5, QColor(205, 92, 92, 100))  # Reduced opacity
                gradient_final.setColorAt(1, QColor(255, 140, 0, 100))  # Reduced opacity
            
            painter.fillPath(progress_path, gradient_final)
        
        # Draw text - Rage counter
        font = QFont('Segoe UI', 16, QFont.Weight.Bold)
        painter.setFont(font)
        text = f"{int(self.decimal_value)}/30"
        
        metrics = painter.fontMetrics()
        text_rect = metrics.boundingRect(text)
        x = (self.width() - text_rect.width()) // 2
        y = (self.height() + text_rect.height()) // 2 - metrics.descent()
        
        # Draw black outline
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    painter.drawText(x + dx, y + dy, text)
        
        # Draw white text
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(x, y, text)
        
        painter.end()
    
    def get_minimal_style(self):
        """Get transparent style since we're using custom painting"""
        return """
            QProgressBar {
                border: none;
                background-color: transparent;
                text-align: center;
            }
        """

class WakfuOuginakResourceTracker(QMainWindow):
    """Main window for Ouginak resource tracker"""
    
    def __init__(self, hidden_mode=False):
        super().__init__()
        
        # Store hidden mode
        self.hidden_mode = hidden_mode
        
        # Resource tracking
        self.resource = 0
        self.current_resource = 0
        self.ougiagou_active = False  # Track if Ougigarou mode is active
        
        # Timeline system
        self.timeline_max_slots = 5
        self.timeline_entries = []  # List of { 'spell': str, 'icon': QPixmap, 'cost': str }
        self.timeline_icon_labels = []
        self.timeline_cost_labels = []
        
        # Spell to icon filename mapping
        self.spell_icon_map = {
            "Emeute": "Emeute.png",
            "Émeute": "Emeute.png",
            "Fléau": "Fléau.png",
            "Fleau": "Fléau.png",
            "Rupture": "Rupture.png",
            "Plombage": "Plombage.png",
            "Balafre": "Balafre.png",
            "Croc-en-jambe": "Croc-en-jambe.png",
            "Bastonnade": "Bastonnade.png",
            "Molosse": "Molosse.png",
            "Hachure": "Hachure.png",
            "Saccade": "Saccade.png",
            "Balayage": "Balayage.png",
            "Contusion": "Contusion.png",
            "Cador": "Cador.png",
            "Brise'Os": "Brise'Os.png",
            "Brise'O": "Brise'Os.png",
            "Baroud": "Baroud.png",
            "Chasseur": "Chasseur.png",
            "Elan": "Elan.png",
            "Élan": "Elan.png",
            "Canine": "Canine.png",
            "Apaisement": "Apaisement.png",
            "Poursuite": "Poursuite.png",
            "Meute": "Meute.png",
            "Proie": "Proie.png",
            "Chienchien": "Chienchien.png",
            "Ougigarou": "Ougigarou.png",
        }
        
        # Spell cost mapping (PA, PM, PW separately for rage calculation)
        self.spell_cost_map = {
            "Emeute": "3 PA", "Émeute": "3 PA",
            "Fléau": "4 PA", "Fleau": "4 PA",  # Show only first cost
            "Rupture": "2 PA",
            "Plombage": "3 PA",
            "Balafre": "5 PA",
            "Croc-en-jambe": "2 PA",
            "Bastonnade": "3 PA",  # Show only first cost
            "Molosse": "4 PA",
            "Hachure": "3 PA",
            "Saccade": "4 PA",
            "Balayage": "4 PA",
            "Contusion": "3 PA",
            "Cador": "3 PA",  # 3 PA + 1 PW total
            "Brise'Os": "2 PA", "Brise'O": "2 PA",
            "Baroud": "6 PA",  # 6 PA + 1 PW total
            "Chasseur": "2 PA",
            "Elan": "1 PA", "Élan": "1 PA",
            "Canine": "3 PA",
            "Apaisement": "2 PA",
            "Poursuite": "3 PA",
            "Meute": "1 PW",
            "Proie": "1 PW",
            "Chienchien": "3 PA",
            "Ougigarou": "2 PA 2 PW"  # Ougigarou cast cost
        }
        
        # Total resource cost for rage calculation (PA + PM + PW)
        self.spell_rage_cost_map = {
            "Emeute": 3, "Émeute": 3,
            "Fléau": 5, "Fleau": 5,  # 4 PA + 1 PW
            "Rupture": 2,
            "Plombage": 3,
            "Balafre": 5,
            "Croc-en-jambe": 2,
            "Bastonnade": 4,  # 3 PA + 1 PW
            "Molosse": 4,
            "Hachure": 3,
            "Saccade": 4,
            "Balayage": 4,
            "Contusion": 3,
            "Cador": 4,  # 3 PA + 1 PW
            "Brise'Os": 2, "Brise'O": 2,
            "Baroud": 7,  # 6 PA + 1 PW
            # Note: Chasseur, Elan, Élan, Canine, Apaisement, Poursuite, Meute, Proie, Chienchien do NOT consume rage
        }
        
        # Turn-based visibility system
        self.tracked_player_name = None
        self.is_ouginak_turn = False
        self.overlay_visible = False
        self.in_combat = False
        self.last_spell_caster = None
        
        # Ouginak spells list
        self.ouginak_spells = [
            "Emeute", "Émeute", "Fleau", "Fléau", "Rupture", "Plombage", 
            "Balafre", "Croc-en-jambe", "Bastonnade", "Molosse", "Hachure", 
            "Saccade", "Balayage", "Contusion", "Cador", "Brise'Os", "Brise'O",
            "Baroud", "Chasseur", "Elan", "Élan", "Canine", "Apaisement", 
            "Poursuite", "Meute", "Proie", "Ougigarou", "Chienchien"
        ]
        
        # Position saving
        self.positions_locked = False
        if getattr(sys, 'frozen', False):
            app_data_dir = Path.home() / "AppData" / "Roaming" / "Waksense"
            app_data_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = app_data_dir / "ouginak_positions.json"
            self.lock_state_file = app_data_dir / "lock_states.json"
        else:
            base_dir = Path(__file__).parent
            self.config_file = base_dir / "positions_config.json"
            self.lock_state_file = base_dir.parent / "lock_states.json"
        
        # Default to unlocked on startup; lock state may be checked dynamically later
        self.is_locked = False
        
        # Log file path
        user_profile = Path.home()
        self.log_file_path = user_profile / "AppData" / "Roaming" / "zaap" / "gamesLogs" / "wakfu" / "logs" / "wakfu_chat.log"
        
        # Icon paths
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys._MEIPASS) / "Ouginak"
        else:
            base_dir = Path(__file__).parent
        self.icon_path = base_dir / "img"
        
        self.setup_ui()
        self.setup_log_monitoring()
        self.setup_animations()
        
        # Load saved positions
        QTimer.singleShot(100, self.load_positions)
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Wakfu Ouginak Resource Tracker")
        
        # Set window flags
        if self.hidden_mode:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | 
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool |
                Qt.WindowType.X11BypassWindowManagerHint
            )
        else:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | 
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool
            )
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Make window full screen
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setGeometry(screen_geometry)
        
        # Main widget
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: transparent;")
        
        # Resource bar container
        self.resource_container = QWidget(main_widget)
        self.resource_container.setFixedSize(320, 70)
        self.resource_container.setStyleSheet("background-color: transparent;")
        
        # Resource bar layout
        resource_layout = QVBoxLayout(self.resource_container)
        resource_layout.setSpacing(10)
        resource_layout.setContentsMargins(0, 0, 0, 0)
        
        # Resource progress bar
        self.resource_bar = OuginakProgressBar()
        
        resource_layout.addWidget(self.resource_bar)
        
        # Position resource container
        self.resource_container.setParent(main_widget)
        # Will be positioned by load_positions() - default is (509, 892)
        
        # Create timeline UI elements (icons and cost overlays)
        for _ in range(self.timeline_max_slots):
            # Icon label
            icon_label = QLabel()
            icon_label.setParent(main_widget)
            icon_label.setFixedSize(32, 32)
            icon_label.setScaledContents(True)
            icon_label.setStyleSheet("background-color: transparent;")
            icon_label.hide()
            self.timeline_icon_labels.append(icon_label)
            
            # Cost label below the icon using outlined white text
            cost_label = OutlinedLabel()
            cost_label.setParent(main_widget)
            cost_label.setFixedSize(32, 16)
            cost_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cost_label.setStyleSheet("background-color: transparent;")
            cost_label.hide()
            self.timeline_cost_labels.append(cost_label)
        
        # Initially hide overlay
        self.resource_container.hide()
        
        self.setCentralWidget(main_widget)
    
    def setup_log_monitoring(self):
        """Setup log file monitoring"""
        self.log_monitor = LogMonitorThread(str(self.log_file_path))
        self.log_monitor.log_updated.connect(self.parse_log_line)
        self.log_monitor.start()
    
    def setup_animations(self):
        """Setup animation timer"""
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animations)
        self.animation_timer.start(16)  # ~60 FPS
    
    def update_animations(self):
        """Update animations and visual effects"""
        # Show/hide overlay based on turn-based visibility and combat status
        if self.overlay_visible and self.in_combat:
            if not self.resource_container.isVisible():
                self.resource_container.show()
            # Show timeline slots that have entries
            self.update_timeline_display()
            
            # Update progress bar Ougigarou mode
            self.resource_bar.set_ougiagou_mode(self.ougiagou_active)
            
            # Update timeline entry animations (fade in/slide for newest)
            for entry in reversed(self.timeline_entries):
                if entry.get('alpha', 1.0) < 1.0:
                    entry['alpha'] = min(1.0, entry['alpha'] + 0.15)
                if entry.get('slide', 0) < 0:
                    entry['slide'] = min(0, entry['slide'] + 3)
        else:
            self.resource_container.hide()
            # Hide timeline when not visible
            for i in range(self.timeline_max_slots):
                self.timeline_icon_labels[i].hide()
                self.timeline_cost_labels[i].hide()
            return
        
        # Smooth transitions for values
        self.resource_bar.setValue(self.resource)
    
    def position_timeline_elements(self):
        """Position timeline elements relative to resource bar"""
        # Get the absolute position of the resource bar
        # Calculate bar position within container, then add container position
        bar_local_pos = self.resource_bar.pos()
        base_x = self.resource_container.x() + bar_local_pos.x()
        base_y = self.resource_container.y() + bar_local_pos.y()
        
        # Position timeline slots relative to resource bar (same as Iop concentration bar)
        timeline_icon_y = base_y + 30  # Below the resource bar
        slot_spacing = 32  # No gap between icons (same as icon width)
        icon_w, icon_h = 32, 32
        
        for i in range(self.timeline_max_slots):
            icon_x = base_x + (i * slot_spacing)
            # Icon position
            self.timeline_icon_labels[i].move(icon_x, timeline_icon_y)
            # Cost label below icon, centered horizontally
            cost_x = icon_x + (icon_w - 32) // 2  # Center the 32px wide cost label under the 32px icon
            cost_y = timeline_icon_y + icon_h - 2
            self.timeline_cost_labels[i].move(cost_x, cost_y)
    
    def update_timeline_display(self):
        """Refresh timeline labels to reflect current entries"""
        # Ensure positions are up-to-date
        self.position_timeline_elements()
        
        # Fill newest-to-oldest left-to-right (latest cast on the far left)
        for i in range(self.timeline_max_slots):
            entry_index = len(self.timeline_entries) - 1 - i
            if 0 <= entry_index < len(self.timeline_entries):
                entry = self.timeline_entries[entry_index]
                # Set cost text
                self.timeline_cost_labels[i].setText(entry['cost'])
                self.timeline_cost_labels[i].show()
                # Set icon
                if entry['pixmap']:
                    self.timeline_icon_labels[i].setPixmap(entry['pixmap'].scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                else:
                    self.timeline_icon_labels[i].setText("?")
                self.timeline_icon_labels[i].show()
                # Ensure cost overlay stays on top of the icon
                self.timeline_icon_labels[i].raise_()
                self.timeline_cost_labels[i].raise_()
                # Apply opacity and slide based on entry animation state
                icon_label = self.timeline_icon_labels[i]
                cost_label = self.timeline_cost_labels[i]
                # Set opacity
                if not hasattr(icon_label, '_opacity'):
                    icon_label._opacity = QGraphicsOpacityEffect()
                    icon_label.setGraphicsEffect(icon_label._opacity)
                if not hasattr(cost_label, '_opacity'):
                    cost_label._opacity = QGraphicsOpacityEffect()
                    cost_label.setGraphicsEffect(cost_label._opacity)
                # Determine target alpha
                is_newest = (i == 0)
                icon_label._opacity.setOpacity(min(1.0, max(0.0, entry.get('alpha', 1.0) if is_newest else 1.0)))
                cost_label._opacity.setOpacity(min(1.0, max(0.0, entry.get('alpha', 1.0) if is_newest else 1.0)))
                # Apply slide offset for newest (both icon and cost move together)
                slide_offset = entry.get('slide', 0) if is_newest else 0
                # Reposition with slide offset - calculate absolute position like above
                bar_local_pos = self.resource_bar.pos()
                base_x = self.resource_container.x() + bar_local_pos.x()
                base_y = self.resource_container.y() + bar_local_pos.y()
                timeline_icon_y = base_y + 30
                icon_x = base_x + (i * 32) + slide_offset
                icon_label.move(icon_x, timeline_icon_y)
                # Cost below icon, centered
                cost_x = icon_x + (32 - 32) // 2
                cost_y = timeline_icon_y + 32 - 2
                cost_label.move(cost_x, cost_y)
            else:
                # Hide empty slots
                self.timeline_icon_labels[i].hide()
                self.timeline_cost_labels[i].hide()
    
    def parse_log_line(self, line):
        """Parse a log line and extract resource information"""
        
        # Check if it's a combat line
        if "[Information (combat)]" not in line:
            return
        
        # Check for Rage gain/loss
        rage_match = re.search(r'(\d+)\s+Rage\s*\(Traqueur\)', line)
        if rage_match:
            rage_gained = int(rage_match.group(1))
            # Add to current rage (it shows how much we gained, not current total)
            self.resource = min(30, self.resource + rage_gained)
            print(f"DEBUG: Rage gained {rage_gained}, current total: {self.resource}")
            return
        
        # Check for combat start
        if "lance le sort" in line:
            self.in_combat = True
            
            # Extract player and spell info
            spell_match = re.search(r'\[Information \(combat\)\] ([^:]+)[:\s]+lance le sort ([^(]+)', line)
            if spell_match:
                caster_name = spell_match.group(1).strip()
                spell_name = spell_match.group(2).strip()
                
                # Track last spell caster
                self.last_spell_caster = caster_name
                
                # Check if this is an Ouginak spell
                is_ouginak_spell = any(ouginak_spell in spell_name for ouginak_spell in self.ouginak_spells)
                
                if is_ouginak_spell:
                    # Set tracked player on first Ouginak spell cast
                    if self.tracked_player_name is None:
                        self.tracked_player_name = caster_name
                        print(f"DEBUG: Ouginak player tracked: {caster_name}")
                    
                    # Show overlay if the tracked Ouginak casts a spell
                    if caster_name == self.tracked_player_name:
                        self.is_ouginak_turn = True
                        self.overlay_visible = True
                        print(f"DEBUG: Ouginak turn started - overlay shown for '{spell_name}'")
                        
                        # Add to timeline
                        self.add_spell_to_timeline(spell_name)
                        
                        # Check if Ougigarou mode consumption should happen
                        if self.ougiagou_active and caster_name == self.tracked_player_name:
                            rage_cost = self.spell_rage_cost_map.get(spell_name, 0)
                            if rage_cost > 0:
                                self.resource = max(0, self.resource - rage_cost)
                                print(f"DEBUG: Spell '{spell_name}' consumed {rage_cost} rage, current: {self.resource}")
                                
                                # Check if rage reached 0 (exit Ougigarou mode)
                                if self.resource <= 0:
                                    self.ougiagou_active = False
                                    print("DEBUG: Rage depleted, exiting Ougigarou mode")
        
        # Check for Ougigarou activation (check for player name separately)
        if "Ougigarou (Niv." in line:
            # Extract player name and check if it's our tracked player
            ougi_match = re.search(r'\[Information \(combat\)\] ([^:]+): Ougigarou', line)
            if ougi_match and ougi_match.group(1).strip() == self.tracked_player_name:
                self.ougiagou_active = True
                print("DEBUG: Ougigarou mode activated")
        
        # Check for Ougigarou deactivation
        if "n'est plus sous l'emprise de 'Ougigarou' (Rage consommée)" in line:
            self.ougiagou_active = False
            print("DEBUG: Ougigarou mode deactivated")
        
        # Turn end detection
        if "secondes reportées pour le tour suivant" in line:
            # Reload lock state to check current state
            self.is_locked = self.load_lock_state()
            
            turn_owner = self.last_spell_caster
            
            if turn_owner and self.tracked_player_name and turn_owner == self.tracked_player_name:
                self.is_ouginak_turn = False
                # Only hide overlay if not locked (locked overlays stay visible)
                if not self.is_locked:
                    self.overlay_visible = False
                print(f"DEBUG: Ouginak turn ended - overlay {'hidden' if not self.overlay_visible else 'still visible (locked)'}")
        
        # Combat end detection
        if "Combat terminé, cliquez ici pour rouvrir l'écran de fin de combat." in line:
            self.in_combat = False
            self.is_ouginak_turn = False
            self.overlay_visible = False
            self.tracked_player_name = None
            self.resource = 0
            self.ougiagou_active = False
            self.timeline_entries.clear()  # Clear timeline on combat end
            print("DEBUG: Combat ended, resources reset")
    
    def add_spell_to_timeline(self, spell_name):
        """Add a spell to the timeline"""
        # Get icon filename
        icon_filename = self.spell_icon_map.get(spell_name, None)
        pixmap = None
        
        if icon_filename:
            icon_path = self.icon_path / icon_filename
            if icon_path.exists():
                pixmap = QPixmap(str(icon_path))
        
        # Determine what to show: Rage cost if Ougigarou active and spell consumes rage, otherwise spell cost
        if self.ougiagou_active and spell_name in self.spell_rage_cost_map:
            rage_cost = self.spell_rage_cost_map.get(spell_name, 0)
            display_cost = f"{rage_cost}RG" if rage_cost > 0 else ""
        else:
            # Show spell cost normally - only the first cost
            cost = self.spell_cost_map.get(spell_name, "? PA")
            # Extract only the first cost (e.g., "2 PA 2 PW" -> "2PA")
            first_cost = cost.split()[0:2] if len(cost.split()) >= 2 else cost.split()
            display_cost = "".join(first_cost)  # e.g., "2 PA" -> "2PA"
        
        # Build entry with animation state
        entry = { 'spell': spell_name, 'cost': display_cost, 'pixmap': pixmap, 'alpha': 0.0, 'slide': -16 }
        
        # Append and clamp to last N; mark the oldest for fade-out/slide-right if overflow
        overflow_entry = None
        if len(self.timeline_entries) >= self.timeline_max_slots:
            overflow_entry = self.timeline_entries[0]
        self.timeline_entries.append(entry)
        if len(self.timeline_entries) > self.timeline_max_slots:
            # Keep one extra temporarily for animating out the oldest
            self.timeline_entries = self.timeline_entries[-(self.timeline_max_slots + 1):]
    
    def load_positions(self):
        """Load positions from config file"""
        # Default initial position (same as Iop)
        default_x = 509
        default_y = 892
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    positions = json.load(f)
                
                if 'resource_container' in positions:
                    x, y = positions['resource_container']['x'], positions['resource_container']['y']
                    self.resource_container.move(x, y)
                else:
                    self.resource_container.move(default_x, default_y)
                
            else:
                self.resource_container.move(default_x, default_y)
        except Exception as e:
            print(f"DEBUG: Error loading positions: {e}")
            self.resource_container.move(default_x, default_y)
    
    def save_positions(self):
        """Save current positions to config file"""
        try:
            positions = {
                'resource_container': {
                    'x': self.resource_container.x(),
                    'y': self.resource_container.y()
                },
                'positions_locked': self.positions_locked
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(positions, f, indent=2)
        except Exception as e:
            print(f"DEBUG: Error saving positions: {e}")
    
    def load_lock_state(self):
        """Load lock state from file"""
        try:
            if self.lock_state_file.exists():
                with open(self.lock_state_file, 'r', encoding='utf-8') as f:
                    lock_states = json.load(f)
                    # Check for Ouginak lock state
                    return lock_states.get('Ouginak', False)
            return False
        except Exception as e:
            print(f"DEBUG: Error loading lock state: {e}")
            return False
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.MouseButton.LeftButton and not self.positions_locked:
            self.drag_position = event.globalPosition().toPoint() - self.resource_container.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if event.buttons() == Qt.MouseButton.LeftButton and not self.positions_locked:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.resource_container.move(new_pos)
            self.save_positions()
            event.accept()
    
    def auto_save_positions(self):
        """Auto-save positions (called by DraggableIcon when dragged)"""
        self.save_positions()
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.save_positions()
        if hasattr(self, 'log_monitor'):
            self.log_monitor.stop_monitoring()
            self.log_monitor.wait()
        if hasattr(self, 'resource_bar'):
            self.resource_bar.progress_timer.stop()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # Check if running in hidden mode
    hidden_mode = "--hidden" in sys.argv
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show window
    window = WakfuOuginakResourceTracker(hidden_mode=hidden_mode)
    
    if not hidden_mode:
        window.show()
    else:
        window.show()
        window.showMinimized()
    
    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

